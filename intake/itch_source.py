"""Resolve only the reviewed free itch.io uploads; never download or admit audio.

Download URLs and anonymous CSRF/session state are ephemeral. Persist receipt(),
not the resolved URL. This module is deliberately separate from prepare.py until
the media-intake integration has its own review.
"""
from dataclasses import dataclass, field
from html.parser import HTMLParser
from http.cookiejar import CookieJar
import hashlib
import json
import re
from urllib.parse import parse_qs, unquote, urlencode, urlparse
from urllib.request import HTTPRedirectHandler, HTTPCookieProcessor, Request, build_opener
from approved_directions_pins import (SOURCE_PINS as NEW_SOURCES,
                                      UPLOAD_PINS as NEW_UPLOADS,
                                      DESCRIPTION_HASHES as NEW_DESCRIPTION_HASHES)
from second_directions_pins import (SOURCE_PINS as SECOND_SOURCES,
                                    UPLOAD_PINS as SECOND_UPLOADS,
                                    DESCRIPTION_HASHES as SECOND_DESCRIPTION_HASHES)
from purgatory3_pins import (SOURCE_PINS as PURGATORY3_SOURCES,
                             UPLOAD_PINS as PURGATORY3_UPLOADS,
                             DESCRIPTION_HASHES as PURGATORY3_DESCRIPTION_HASHES)
from reckless2_pins import (SOURCE_PINS as RECKLESS2_SOURCES,
                            UPLOAD_PINS as RECKLESS2_UPLOADS,
                            DESCRIPTION_HASHES as RECKLESS2_DESCRIPTION_HASHES)

PAGE_LIMIT = 2 * 1024 ** 2
CDN_HOST = 'itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com'
LICENSE_URL = 'https://creativecommons.org/licenses/by/4.0/'
SOURCE_PINS = {
    'dos88': ('https://dos88.itch.io/dos-88-music-library', 66639,
              'https://itch.io/soundtracks/assets-cc4-by'),
    'escp': ('https://escpmusic.itch.io/synthasia', 4662919,
             'https://itch.io/game-assets/assets-cc4-by'),
    'davidkbd': ('https://davidkbd.itch.io/eternity-metal-scfi-music-pack', 976471,
                 'https://itch.io/game-assets/assets-cc4-by'),
}
# Public upload titles are exact identity evidence, not inferred local filenames.
# In particular, escp's visible titles have no extension. Verify Content-Disposition
# and actual media format during the later hosted acquisition.
UPLOAD_PINS = {
    'dos88.crash-landing': ('dos88', 206068, 'Crash Landing.mp3', 'Crash Landing'),
    'dos88.race-to-mars': ('dos88', 206071, 'Race to Mars.mp3', 'Race to Mars'),
    'dos88.automata-v2': ('dos88', 206072, 'DOS-88 - Automatav2.mp3', 'Automata v2'),
    'dos88.city-stomper': ('dos88', 206074, 'DOS-88 - City Stomper.mp3', 'City Stomper'),
    'escp.twilight-city': ('escp', 17878087, 'Twilight City', 'Twilight City'),
    'escp.synthasia': ('escp', 17878086, 'Synthasia', 'Synthasia'),
    'davidkbd.desolation': ('davidkbd', 6033123,
        'DavidKBD - Eternity Pack - 01 - The desolation of a civilization - oneshoot.ogg',
        'The Desolation of a Civilization'),
    'davidkbd.agony-space-deep': ('davidkbd', 6033127,
        'DavidKBD - Eternity Pack - 02 - Agony Space-deep - oneshoot.ogg', 'Agony Space-deep'),
    'davidkbd.god-of-darkness': ('davidkbd', 6033130,
        'DavidKBD - Eternity Pack - 06 - God of darkness - oneshoot.ogg', 'God of Darkness'),
    'davidkbd.suffocation': ('davidkbd', 6033135,
        'DavidKBD - Eternity Pack - 07 - Suffocation - oneshoot.ogg', 'Suffocation'),
}
LEGACY_TRACK_IDS = frozenset(UPLOAD_PINS)
SOURCE_PINS.update(NEW_SOURCES)
UPLOAD_PINS.update(NEW_UPLOADS)
SOURCE_PINS.update(SECOND_SOURCES)
UPLOAD_PINS.update(SECOND_UPLOADS)
SOURCE_PINS.update(PURGATORY3_SOURCES)
UPLOAD_PINS.update(PURGATORY3_UPLOADS)
SOURCE_PINS.update(RECKLESS2_SOURCES)
UPLOAD_PINS.update(RECKLESS2_UPLOADS)
DESCRIPTION_HASHES = {
    **NEW_DESCRIPTION_HASHES,
    **SECOND_DESCRIPTION_HASHES,
    **PURGATORY3_DESCRIPTION_HASHES,
    **RECKLESS2_DESCRIPTION_HASHES,
}


class SourceChanged(ValueError):
    """The reviewed free source no longer matches; human review is required."""


def require(condition, message):
    if not condition:
        raise SourceChanged(message)


def valid_download_page(source, value):
    if not isinstance(value, str):
        return False
    parsed, original = urlparse(value), urlparse(source)
    prefix = original.path + '/download/'
    token = parsed.path.removeprefix(prefix)
    return bool(parsed.scheme == 'https' and parsed.netloc == original.netloc
                and parsed.path.startswith(prefix) and not parsed.query and not parsed.fragment
                and re.fullmatch(r'(?:[A-Za-z0-9_-]|%3[dD]|%2[bBeEfF]){1,200}', token)
                and re.fullmatch(r'[A-Za-z0-9_+/-]+={0,2}(?:\.[A-Za-z0-9_+/-]+={0,2})?',
                                 unquote(token)))


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        raise SourceChanged('Unexpected metadata redirect; source review required')


class MetadataClient:
    """Anonymous, bounded metadata requests, restricted to one registered creator."""

    def __init__(self, source):
        require(source in {row[0] for row in SOURCE_PINS.values()}, 'Unregistered creator source')
        self.source = source
        self.opener = build_opener(NoRedirects(), HTTPCookieProcessor(CookieJar()))

    def read(self, url, data=None):
        parsed, source = urlparse(url), urlparse(self.source)
        require(parsed.scheme == 'https' and parsed.netloc == source.netloc
                and not parsed.username and not parsed.password and not parsed.fragment
                and not any(ord(c) < 33 for c in url),
                'Metadata request escaped the registered creator')
        allowed = (url == self.source or url == self.source + '/purchase'
                   or url == self.source + '/download_url'
                   or valid_download_page(self.source, url)
                   or re.fullmatch(re.escape(source.path) + r'/file/[0-9]+', parsed.path)
                   and parsed.query == 'source=game_download')
        require(allowed, 'Unreviewed metadata endpoint')
        require(data is None or (set(data) == {'csrf_token'} and isinstance(data['csrf_token'], str)),
                'Only anonymous free-download CSRF submission is allowed')
        headers = {'User-Agent': 'RevealLine soundtrack source resolver/1.0'}
        payload = None
        if data is not None:
            payload = urlencode(data).encode()
            headers.update({'Content-Type': 'application/x-www-form-urlencoded',
                            'X-Requested-With': 'XMLHttpRequest'})
        try:
            with self.opener.open(Request(url, data=payload, headers=headers), timeout=30) as response:
                require(response.url == url, 'Unexpected metadata response origin')
                body = response.read(PAGE_LIMIT + 1)
                require(len(body) <= PAGE_LIMIT, 'Metadata response exceeds bounded size')
                return body.decode('utf8')
        except SourceChanged:
            raise
        except Exception:
            # Exception strings can contain temporary keys. Never echo them.
            raise SourceChanged('Metadata request failed; no media was fetched') from None


class Page(HTMLParser):
    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.csrf = None
        self.links = set()
        self.free_button = False
        self.uploads = []
        self.depth = 0
        self.row = None
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = attrs.get('class', '').split()
        if tag == 'meta' and attrs.get('name') == 'csrf_token':
            require(self.csrf is None, 'Duplicate CSRF metadata')
            self.csrf = attrs.get('value')
        if tag == 'a':
            self.links.add(attrs.get('href'))
            self.free_button |= 'direct_download_btn' in classes
        if tag == 'div':
            self.depth += 1
            if 'upload' in classes:
                require(self.row is None, 'Ambiguous nested upload row')
                self.row = {'depth': self.depth, 'ids': [], 'names': []}
        if self.row is not None:
            if tag == 'a' and 'download_btn' in classes:
                self.row['ids'].append(attrs.get('data-upload_id'))
            if tag == 'strong' and 'name' in classes:
                self.row['names'].append(attrs.get('title'))

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.row is not None and self.row['depth'] == self.depth:
                self.uploads.append(self.row)
                self.row = None
            self.depth -= 1


class SourceDescription(HTMLParser):
    """Bind the reviewed creator description, without session state or comments.

    Pinning all description text and links makes added standalone restrictions a
    review event even when the site's CC BY category badge remains unchanged.
    """

    def __init__(self, body):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.active = None
        self.count = 0
        self.chunks = []
        self.links = []
        self.feed(body)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'div':
            self.depth += 1
            if 'formatted_description' in attrs.get('class', '').split():
                self.count += 1
                require(self.active is None, 'Ambiguous nested creator description')
                self.active = self.depth
        if self.active is not None and tag == 'a':
            self.links.append(attrs.get('href'))

    def handle_endtag(self, tag):
        if tag == 'div':
            if self.active == self.depth:
                self.active = None
            self.depth -= 1

    def handle_data(self, data):
        if self.active is not None:
            self.chunks.append(data)

    def digest(self):
        require(self.count == 1 and self.active is None and self.chunks,
                'Missing, duplicate or incomplete creator description')
        facts = {'text': ' '.join(' '.join(self.chunks).split()), 'links': self.links}
        return hashlib.sha256(json.dumps(facts, ensure_ascii=False,
                                        sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def verify_source_license(creator, body):
    require(SOURCE_PINS[creator][2] in Page(body).links,
            'Published CC BY 4.0 asset licence changed')
    if creator in DESCRIPTION_HASHES:
        description = SourceDescription(body)
        require(LICENSE_URL in description.links
                and description.digest() == DESCRIPTION_HASHES[creator],
                'Reviewed creator description or licence terms changed')


def checked_json(body):
    try:
        value = json.loads(body)
    except (ValueError, TypeError):
        raise SourceChanged('Metadata was not JSON') from None
    require(isinstance(value, dict), 'Unexpected metadata object')
    return value


def checked_cdn(url, game_id, upload_id):
    require(isinstance(url, str), 'No signed media URL returned')
    parsed = urlparse(url)
    require(parsed.scheme == 'https' and parsed.netloc == CDN_HOST
            and parsed.path == f'/upload2/game/{game_id}/{upload_id}'
            and not parsed.fragment and not parsed.params
            and not any(ord(c) < 33 for c in url), 'Unreviewed media host or upload binding')
    query = parse_qs(parsed.query, keep_blank_values=True)
    expected = {'X-Amz-Algorithm', 'X-Amz-Credential', 'X-Amz-Date',
                'X-Amz-Expires', 'X-Amz-SignedHeaders', 'X-Amz-Signature'}
    require(set(query) == expected and all(len(v) == 1 and v[0] for v in query.values()),
            'Unexpected signed URL fields')
    require(query['X-Amz-Algorithm'] == ['AWS4-HMAC-SHA256']
            and query['X-Amz-SignedHeaders'] == ['host']
            and re.fullmatch(r'[0-9]{8}T[0-9]{6}Z', query['X-Amz-Date'][0])
            and re.fullmatch(r'[0-9a-f]{64}', query['X-Amz-Signature'][0])
            and query['X-Amz-Expires'][0].isdigit()
            and 0 < int(query['X-Amz-Expires'][0]) <= 86400,
            'Unexpected signed URL authorization shape')
    return url


@dataclass(frozen=True)
class Resolution:
    track_id: str
    source: str
    game_id: int
    upload_id: int
    upload_name: str
    title: str
    download_url: str = field(repr=False)

    def receipt(self):
        """Safe to persist: no cookies, CSRF, temporary download keys or signed URLs."""
        return {
            'format': 'revealline-itch-source-resolution.v1',
            'id': self.track_id, 'source': self.source,
            'gameId': self.game_id, 'uploadId': self.upload_id,
            'uploadName': self.upload_name, 'title': self.title,
            'license': 'CC BY 4.0 International', 'licenseURL': LICENSE_URL,
            'mediaHost': CDN_HOST,
            'mediaPath': f'/upload2/game/{self.game_id}/{self.upload_id}',
            'acquisition': 'public-free-download',
            'audioAcquired': False, 'listeningApproval': False, 'admitted': False,
        }


def resolve(track_id, client=None):
    require(track_id in UPLOAD_PINS, 'Recording is not in the reviewed candidate slate')
    creator, upload_id, upload_name, title = UPLOAD_PINS[track_id]
    source, game_id, _ = SOURCE_PINS[creator]
    client = client or MetadataClient(source)
    body = client.read(source)
    verify_source_license(creator, body)
    body = client.read(source + '/purchase')
    purchase = Page(body)
    matches = re.findall(r"init_GamePurchase\('[^']+',\s*(\{[^;]+?\})\);", body)
    require(len(matches) == 1, 'Ambiguous purchase source identity')
    game = checked_json(matches[0])
    require(type(game.get('id')) is int and game['id'] == game_id
            and game.get('slug') == urlparse(source).path[1:]
            and type(game.get('min_price')) is int and game['min_price'] == 0
            and type(game.get('actual_price')) is int and game['actual_price'] == 0
            and purchase.free_button and purchase.csrf,
            'Source identity changed or public free download is unavailable')
    generated = checked_json(client.read(source + '/download_url', {'csrf_token': purchase.csrf}))
    require(set(generated) == {'url'} and isinstance(generated['url'], str),
            'Free download page was not returned')
    require(valid_download_page(source, generated['url']),
            'Free download page escaped the reviewed source')
    page = Page(client.read(generated['url']))
    require(page.csrf, 'Free download page lacks CSRF state')
    rows = [row for row in page.uploads if str(upload_id) in row['ids']]
    require(len(rows) == 1 and rows[0]['ids'] == [str(upload_id)]
            and rows[0]['names'] == [upload_name],
            'Exact upload identity/title binding changed')
    result = checked_json(client.read(source + f'/file/{upload_id}?source=game_download',
                                      {'csrf_token': page.csrf}))
    require(set(result) == {'url', 'external'} and result['external'] is False,
            'External, quarantined or changed download requires review')
    url = checked_cdn(result['url'], game_id, upload_id)
    return Resolution(track_id, source, game_id, upload_id, upload_name, title, url)
