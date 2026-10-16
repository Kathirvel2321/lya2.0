"""Bounded HTTPS text reader. No cookies, browser session, JavaScript or downloads.

DNS answers must all be global addresses; the TLS socket is pinned to a validated
address while retaining hostname certificate checks. The public reader refuses
redirects because redirected destinations need their own robots-policy check.
This is a text reader, not a sandbox for executing untrusted site code.
"""
from html.parser import HTMLParser
import http.client
import ipaddress
import re
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

USER_AGENT = 'LYAResearch/1.0'
MAX_PAGE_BYTES = 196608


def public_url(url):
    if type(url) is not str or not 1 <= len(url) <= 2048 or any(ord(c) < 33 for c in url):
        raise ValueError('Invalid public URL.')
    parsed = urlsplit(url)
    if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
            or parsed.port not in (None, 443) or '%' in parsed.hostname or '\\' in url):
        raise ValueError('Only ordinary public HTTPS URLs are supported.')
    host = parsed.hostname.rstrip('.').encode('idna').decode('ascii').lower()
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.onion')):
        raise ValueError('Local destinations are not public research.')
    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[a-z0-9.-]+', host) or '.' not in host:
            raise ValueError('Invalid public hostname.')
    else:
        if not literal.is_global or literal.is_multicast:
            raise ValueError('Non-public addresses are blocked.')
    authority = '[' + host + ']' if ':' in host else host
    return urlunsplit(('https', authority, parsed.path or '/', parsed.query, ''))


def public_addresses(host, resolve=socket.getaddrinfo):
    entries = resolve(host, 443, type=socket.SOCK_STREAM)
    addresses = list(dict.fromkeys(entry[4][0] for entry in entries))
    if not addresses:
        raise ValueError('No public address was resolved.')
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global or address.is_multicast:
            raise ValueError('Mixed or non-public DNS destinations are blocked.')
    return addresses


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host, address, timeout):
        super().__init__(host, timeout=timeout, context=ssl.create_default_context())
        self.address = address

    def connect(self):
        raw = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except BaseException:
            raw.close()
            raise


class TextBlocks(HTMLParser):
    SKIP = {'script', 'style', 'nav', 'footer', 'header', 'form', 'noscript', 'svg', 'template'}
    BREAK = {'p', 'div', 'li', 'br', 'tr', 'h1', 'h2', 'h3', 'h4', 'section', 'article'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.parts, self.blocks = [], []

    def flush(self):
        value = ' '.join(' '.join(self.parts).split())
        if value:
            self.blocks.append(value)
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.hidden.append(tag)
        if not self.hidden and tag in self.BREAK:
            self.flush()

    def handle_endtag(self, tag):
        if self.hidden:
            if tag == self.hidden[-1]:
                self.hidden.pop()
            return
        if tag in self.BREAK:
            self.flush()

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def relevant_excerpt(blocks, question, limit=900):
    words = {w.casefold() for w in re.findall(r'[^\W_]{3,}', question)}
    candidates = [value for value in blocks if 20 <= len(value) <= limit]
    if not candidates:
        raise ValueError('No bounded readable passage; search snippet remains unconfirmed.')
    # Select complete blocks. Do not clip away a trailing condition to fit a quote.
    ranked = sorted(enumerate(candidates), key=lambda pair: (
        -len(words.intersection(w.casefold() for w in re.findall(r'[^\W_]{3,}', pair[1]))), pair[0]))
    selected, size = [], 0
    for index, value in ranked[:3]:
        if size + len(value) + 1 <= limit:
            selected.append((index, value))
            size += len(value) + 1
    return '\n'.join(value for _, value in sorted(selected))


class PublicPageReader:
    def __init__(self, *, resolve=socket.getaddrinfo, connect=_PinnedHTTPS, monotonic=time.monotonic):
        self.resolve, self.connect, self.monotonic = resolve, connect, monotonic

    def _get(self, url, deadline, check, reserve, max_bytes=MAX_PAGE_BYTES, redirects=3):
        for hop in range(redirects + 1):
            check()
            url = public_url(url)
            parsed = urlsplit(url)
            addresses = public_addresses(parsed.hostname, self.resolve)
            check()
            remaining = deadline - self.monotonic()
            if remaining <= 0:
                raise TimeoutError('Page-reading budget expired.')
            reserve()
            connection = self.connect(parsed.hostname, addresses[0], min(4, remaining))
            try:
                target = urlunsplit(('', '', parsed.path or '/', parsed.query, ''))
                connection.request('GET', target, headers={'User-Agent': USER_AGENT,
                    'Accept': 'text/html,text/plain;q=0.9', 'Accept-Encoding': 'identity',
                    'Connection': 'close'})
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    if hop == redirects or not response.getheader('Location'):
                        raise ValueError('Page redirect limit exceeded.')
                    url = urljoin(url, response.getheader('Location'))
                    continue
                if response.status != 200:
                    return url, response.status, '', b''
                mime = (response.getheader('Content-Type') or '').split(';')[0].strip().lower()
                encoding = (response.getheader('Content-Encoding') or 'identity').lower()
                if mime not in ('text/html', 'text/plain', 'application/xhtml+xml') or encoding != 'identity':
                    raise ValueError('Only uncompressed public text pages are supported.')
                length = response.getheader('Content-Length')
                if length and (not length.isdigit() or int(length) > max_bytes):
                    raise ValueError('Public text page exceeds the byte budget.')
                raw = bytearray()
                while True:
                    check()
                    remaining = deadline - self.monotonic()
                    if remaining <= 0:
                        raise TimeoutError('Page-reading budget expired.')
                    if connection.sock is not None:
                        connection.sock.settimeout(min(4, remaining))
                    chunk = response.read(min(8192, max_bytes + 1 - len(raw)))
                    if not chunk:
                        break
                    raw.extend(chunk)
                    if len(raw) > max_bytes:
                        raise ValueError('Public text page exceeds the byte budget.')
                return url, response.status, mime, bytes(raw)
            except http.client.HTTPException as exc:
                raise ValueError('Public page transfer was incomplete or invalid.') from exc
            finally:
                connection.close()
        raise ValueError('Public page unavailable.')

    def __call__(self, url, question, *, deadline, check, reserve):
        url = public_url(url)
        parsed = urlsplit(url)
        robots_url = urlunsplit(('https', parsed.netloc, '/robots.txt', '', ''))
        final, status, _, raw = self._get(robots_url, deadline, check, reserve, max_bytes=32768, redirects=0)
        if status == 200:
            rules = RobotFileParser(); rules.parse(raw.decode('utf-8', 'replace').splitlines())
            if not rules.can_fetch(USER_AGENT, url):
                raise ValueError('Page reading is disallowed by robots rules.')
        elif status not in (404, 410):
            raise ValueError('Robots policy could not be established.')
        final, status, mime, raw = self._get(url, deadline, check, reserve, redirects=0)
        # Page redirects are deliberately unsupported until target-origin robots are checked.
        if status != 200:
            raise ValueError('Page content is unavailable; snippet is not a page read.')
        text = raw.decode('utf-8', 'replace')
        if mime == 'text/plain':
            blocks = text.splitlines()
        else:
            parser = TextBlocks(); parser.feed(text); parser.flush(); blocks = parser.blocks
        return {'url': final, 'excerpt': relevant_excerpt(blocks, question)}
