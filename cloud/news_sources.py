"""Bounded official-source discovery. Publisher announcements are not benchmarks.

No queries, model calls, account sessions, scripts, browser automation or keys.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from html.parser import HTMLParser
import re
import time
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree as ET

from cloud.web_reader import PublicPageReader, public_url

MAX_BYTES = 1048576
MAX_ITEMS = 60


@dataclass(frozen=True)
class Source:
    key: str
    label: str
    url: str
    parser: str
    hosts: tuple


SOURCES = (
    Source('openai', 'OpenAI News', 'https://openai.com/news/rss.xml', 'feed', ('openai.com',)),
    Source('gemini', 'Gemini release notes', 'https://gemini.google/release-notes/', 'gemini', ('gemini.google',)),
    Source('anthropic', 'Anthropic News', 'https://www.anthropic.com/news', 'anthropic', ('www.anthropic.com', 'anthropic.com')),
)


def clean(value, limit=600):
    value = ''.join(c if ord(c) >= 32 or c in '\n\t' else ' ' for c in value)
    return ' '.join(value.split())[:limit]


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []; self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self.hidden.append(tag)

    def handle_endtag(self, tag):
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()

    def handle_data(self, value):
        if not self.hidden:
            self.parts.append(value)


def plain(value, limit=600):
    parser = PlainText(); parser.feed(value)
    return clean(' '.join(parser.parts), limit)


def source_url(source, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError('Missing official announcement link.')
    url = public_url(urljoin(source.url, value))
    if urlsplit(url).hostname not in source.hosts:
        raise ValueError('Announcement link leaves the official publisher.')
    if source.parser == 'anthropic' and not urlsplit(url).path.startswith('/news/'):
        raise ValueError('Not an official news article.')
    return url


def timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.strip().replace('Z', '+00:00'))
    except ValueError:
        stamp = parsedate_to_datetime(value)
    if stamp.tzinfo is None:
        raise ValueError('Publisher time has no timezone.')
    return stamp.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def announcement(source, title, url, published, summary='', precision='time'):
    title = clean(title, 1000)
    if not title or not 5 <= len(title) <= 240:
        raise ValueError('Missing announcement title.')
    url = source_url(source, url)
    stamp = timestamp(published)
    identity = source.key + '\n' + url
    if source.parser == 'gemini':
        identity += '\n' + stamp[:10] + '\n' + title.casefold()
    return {'id': hashlib.sha256(identity.encode()).hexdigest(), 'source': source.key,
            'publisher': source.label, 'source_url': source.url, 'url': url,
            'title': title, 'published_at': stamp, 'precision': precision,
            'preview': plain(summary, 600)}


def parse_feed(raw, source, check=lambda: None):
    # Decode before the declaration check: UTF-16 must not evade the DTD guard.
    text = raw.decode('utf-8-sig')
    if '<!DOCTYPE' in text.upper() or '<!ENTITY' in text.upper():
        raise ValueError('DTD/entity declarations are not accepted.')
    parser = ET.XMLPullParser(events=('start', 'end'))
    depth = count = 0
    for start in range(0, len(text), 8192):
        check(); parser.feed(text[start:start+8192])
        for event, node in parser.read_events():
            if event == 'start':
                depth += 1; count += 1
                if depth > 32 or count > 12000:
                    raise ValueError('News XML structure exceeds its budget.')
            else:
                depth -= 1
    parser.close()
    root = ET.fromstring(text)
    local = lambda tag: tag.rsplit('}', 1)[-1]
    if local(root.tag) not in ('rss', 'feed', 'RDF'):
        raise ValueError('Unrecognized official feed format.')
    items, rejected = [], 0
    for node in root.iter():
        if local(node.tag) not in ('item', 'entry'):
            continue
        check()
        fields = {}; link = ''
        for child in node:
            key = local(child.tag)
            value = ''.join(child.itertext()).strip()
            fields.setdefault(key, value)
            if key == 'link':
                if child.attrib.get('rel', 'alternate') == 'alternate':
                    link = child.attrib.get('href') or value
        try:
            # An update date alone does not establish when a launch was announced.
            date = fields.get('pubDate') or fields.get('published') or fields.get('date')
            if not date: raise ValueError('Missing publisher announcement date.')
            items.append(announcement(source, fields.get('title', ''), link, date,
                fields.get('description') or fields.get('summary') or fields.get('encoded', '')))
        except (ValueError, TypeError, OverflowError):
            rejected += 1
        if len(items) >= MAX_ITEMS:
            break
    return items, rejected


class GeminiNotes(HTMLParser):
    """Dated H2 sections with H3 update titles, as on official release notes."""
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source; self.capture = None; self.parts = []
        self.date = None; self.current = None; self.items = []; self.hidden = []
        self.rejected = 0

    def finish(self):
        if self.current and self.date and len(self.items) < MAX_ITEMS:
            try:
                self.items.append(announcement(self.source, self.current[0], self.source.url,
                    self.date+'T00:00:00Z', ' '.join(self.current[1]), 'day'))
            except ValueError:
                self.rejected += 1
        self.current = None

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'nav', 'footer', 'header'):
            self.hidden.append(tag)
        if not self.hidden and tag in ('h2', 'h3'):
            self.finish(); self.capture = tag; self.parts = []

    def handle_endtag(self, tag):
        if self.hidden:
            if self.hidden[-1] == tag: self.hidden.pop()
            return
        if tag == self.capture:
            value = clean(' '.join(self.parts), 240)
            if tag == 'h2':
                self.date = None
                if re.fullmatch(r'\d{4}\.\d{2}\.\d{2}', value):
                    try: self.date = datetime.strptime(value, '%Y.%m.%d').date().isoformat()
                    except ValueError: self.rejected += 1
            elif self.date:
                self.current = (value, [])
            self.capture = None

    def handle_data(self, value):
        if not self.hidden:
            if self.capture: self.parts.append(value)
            elif self.current and sum(map(len, self.current[1])) < 1600:
                self.current[1].append(value)


class AnthropicListing(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=True)
        self.source = source; self.href = None; self.parts = []
        self.items = []; self.rejected = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.href = dict(attrs).get('href'); self.parts = []

    def handle_data(self, value):
        if self.href: self.parts.append(value)

    def handle_endtag(self, tag):
        if tag != 'a' or not self.href:
            return
        value, href = clean(' '.join(self.parts), 2000), self.href
        self.href = None
        if '/news/' not in href or len(self.items) >= MAX_ITEMS:
            return
        match = re.search(r'\b([A-Z][a-z]{2} \d{1,2}, \d{4})\b', value)
        if not match:
            self.rejected += 1; return
        try:
            date = datetime.strptime(match.group(1), '%b %d, %Y').date().isoformat()
            title = (value[:match.start()] + ' ' + value[match.end():]).strip()
            title = re.sub(r'^(?:Announcements|Features|Policy|Research|Science)\s*', '', title)
            self.items.append(announcement(self.source, title, href, date+'T00:00:00Z', '', 'day'))
        except ValueError:
            self.rejected += 1


def parse_source(raw, source, check=lambda: None):
    if type(raw) is not bytes or len(raw) > MAX_BYTES:
        raise ValueError('News source exceeds its byte budget.')
    check()
    if source.parser == 'feed':
        items, rejected = parse_feed(raw, source, check)
    else:
        parser = GeminiNotes(source) if source.parser == 'gemini' else AnthropicListing(source)
        text = raw.decode('utf-8-sig')
        for start in range(0, len(text), 8192):
            check(); parser.feed(text[start:start+8192])
        if isinstance(parser, GeminiNotes): parser.finish()
        items, rejected = parser.items, parser.rejected
    if not items:
        raise ValueError('No dated official announcements could be parsed; format may have changed.')
    return list({row['id']: row for row in items}.values()), rejected


class OfficialNewsFetcher:
    def __init__(self, reader=None):
        self.reader = reader or PublicPageReader()

    def __call__(self, source, *, deadline, check, reserve):
        parts = urlsplit(source.url)
        robots_url = 'https://' + parts.netloc + '/robots.txt'
        _, status, _, raw = self.reader._get(robots_url, deadline, check, reserve,
                                            max_bytes=32768, redirects=0)
        if status == 200:
            policy = RobotFileParser(); policy.parse(raw.decode('utf-8', 'replace').splitlines())
            if not policy.can_fetch('LYAResearch/1.0', source.url):
                raise ValueError('Publisher robots policy disallows this check.')
        elif status not in (404, 410):
            raise ValueError('Publisher robots policy is unavailable.')
        _, status, mime, raw = self.reader._get(source.url, deadline, check, reserve,
            max_bytes=MAX_BYTES, redirects=0,
            accepted_mimes=('application/rss+xml','application/atom+xml','application/xml',
                            'text/xml','text/html','application/xhtml+xml','text/plain'))
        if status != 200:
            raise ValueError('Official source is unavailable.')
        return parse_source(raw, source, check)
