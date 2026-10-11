"""Explicit public-only archive transport; never installed or enabled at import."""
import ipaddress
import json
from pathlib import Path
from storage.public_archive import encoded, record, slug, revision, validate_request, MAX_WIRE

ROOT = Path(__file__).resolve().parents[1]


class ArchiveUnavailable(RuntimeError):
    pass


def acknowledged(result, expected):
    if (type(result) is not dict or set(result) != {'revision', 'acknowledged'}
            or result['acknowledged'] is not True or type(result['revision']) is not int
            or result['revision'] != expected):
        raise ArchiveUnavailable('Invalid archive acknowledgement.')
    return result


class OraclePublicArchive:
    def __init__(self, config, *, cache=None, exchange=None):
        self.config, self.cache, self.exchange = config, cache, exchange

    def request(self, packet, *, cancelled=None):
        validate_request(packet)
        # Verified deployment is separate from the accepted inference configuration.
        gates = self.config.get('public_archive', {})
        if not isinstance(gates, dict) or any(gates.get(key) is not True for key in
                ('enabled', 'free_allowance_verified', 'isolated_access_verified', 'recovery_verified')):
            raise ArchiveUnavailable('Public archive is disabled pending deployment and readiness checks.')
        body = encoded(packet).decode()
        try:
            host = str(ipaddress.ip_address(self.config['host']))
            key = (ROOT / gates['key_file']).resolve()
            key.relative_to(ROOT)
            pins = ROOT / 'oracle_known_hosts.local'
            if not key.is_file() or not pins.is_file():
                raise ValueError()
            command = ['ssh', '-T', '-o', 'BatchMode=yes', '-o', 'IdentitiesOnly=yes',
                       '-o', 'ConnectTimeout=7', '-o', 'StrictHostKeyChecking=yes',
                       '-o', 'UpdateHostKeys=no', '-o', 'ForwardAgent=no',
                       '-o', 'ClearAllForwardings=yes', '-o', 'ControlMaster=no',
                       '-o', 'ControlPath=none', '-o', 'UserKnownHostsFile=' + str(pins),
                       '-i', str(key), 'lya-archive@' + host,
                       '/usr/bin/python3 /opt/lya-public/public_archive.py']
            exchange = self.exchange
            if exchange is None:
                from cloud.ssh_session import exchange
            run = exchange(command, body, cancelled, timeout=12, close_stdin=True)
            if run.returncode or len(run.stdout.encode()) > MAX_WIRE:
                raise ValueError()
            response = json.loads(run.stdout)
            if type(response) is not dict or 'error' in response:
                raise ValueError()
            return response
        except InterruptedError:
            raise
        except Exception:
            raise ArchiveUnavailable('Archive unavailable; completion was not confirmed. Retry the same revision.') from None

    def put(self, item, *, expected_revision, reviewed_public=False, cancelled=None):
        record(item)
        revision(expected_revision, zero=True)
        if reviewed_public is not True:
            raise PermissionError('Public transfer review required.')
        if item['revision'] != expected_revision + 1:
            raise ValueError('Revision conflict.')
        # Invalidate before sending: an interrupted correction may have committed.
        if self.cache:
            self.cache.invalidate(item['owner'], item['project'], item['id'])
        result = self.request({'op': 'put', 'owner': item['owner'], 'project': item['project'],
                               'record': item, 'expected_revision': expected_revision,
                               'reviewed_public': reviewed_public}, cancelled=cancelled)
        return acknowledged(result, item['revision'])

    def get(self, owner, project, doc_id, version, *, cancelled=None):
        slug(doc_id)
        revision(version)
        result = self.request({'op': 'get', 'owner': owner, 'project': project,
                               'id': doc_id, 'revision': version}, cancelled=cancelled)
        if set(result) != {'record'}:
            raise ArchiveUnavailable('Invalid archive response.')
        item = result['record']
        if item is not None:
            record(item)
            if (item['owner'], item['project'], item['id'], item['revision']) != (owner, project, doc_id, version):
                raise ArchiveUnavailable('Archive scope mismatch.')
            if self.cache:
                try:
                    self.cache.put(item)
                except OSError:
                    pass  # A confirmed public read does not depend on an evictable cache.
        elif self.cache:
            self.cache.invalidate(owner, project, doc_id)
        return result

    def search(self, owner, project, query, *, cancelled=None):
        if type(query) is not str or not 1 <= len(query) <= 400:
            raise ValueError('Invalid query.')
        result = self.request({'op': 'search', 'owner': owner, 'project': project,
                               'query': query}, cancelled=cancelled)
        hits = result.get('records')
        if set(result) != {'records'} or type(hits) is not list or len(hits) > 6:
            raise ArchiveUnavailable('Invalid archive response.')
        for hit in hits:
            record(hit)
            if (hit['owner'], hit['project']) != (owner, project):
                raise ArchiveUnavailable('Archive scope mismatch.')
        return result

    def delete(self, owner, project, doc_id, *, expected_revision, cancelled=None):
        slug(owner), slug(project), slug(doc_id), revision(expected_revision)
        if self.cache:
            self.cache.invalidate(owner, project, doc_id)
        result = self.request({'op': 'delete', 'owner': owner, 'project': project,
                               'id': doc_id, 'expected_revision': expected_revision}, cancelled=cancelled)
        return acknowledged(result, expected_revision + 1)


def configured_archive():
    """Load existing settings only on an explicit archive command; no new key store."""
    from brain.oracle import CONFIG
    from storage.public_archive import PublicCache
    import os
    try:
        config = json.loads(CONFIG.read_text())
        if type(config) is not dict:
            raise ValueError()
    except (OSError, ValueError):
        raise ArchiveUnavailable('Public archive is not configured.') from None
    # Distinct evictable directory; protected identity/memory never enters this cache.
    root = os.environ.get('LYA_DATA_DIR') or os.environ.get('LOCALAPPDATA')
    if not root:
        raise ArchiveUnavailable('Public cache directory is unavailable.')
    cache = PublicCache(Path(root) / 'LYA/public-archive-cache')
    return OraclePublicArchive(config, cache=cache)
