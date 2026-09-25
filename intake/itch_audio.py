"""Bounded hosted acquisition for exact free itch uploads; never publish or approve.

Anonymous session pages and temporary media authorization live only in memory.
Persist semantic licence evidence and hash-addressed native sources, never the
raw session-bearing HTML, cookies, CSRF state or signed media URL.
"""
from email.message import Message
from email.utils import collapse_rfc2231_value
import hashlib
import re
import unicodedata
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse
from urllib.request import Request, build_opener
from itch_source import (MetadataClient, NoRedirects, SOURCE_PINS, UPLOAD_PINS,
                         LICENSE_URL, SourceChanged, checked_cdn, require, resolve)
from approved_directions_pins import (SOURCE_PINS as NEW_SOURCES,
                                      UPLOAD_PINS as NEW_UPLOADS,
                                      DESCRIPTION_HASHES as NEW_DESCRIPTION_HASHES,
                                      details as audition_details)
from second_directions_pins import (SOURCE_PINS as SECOND_SOURCES,
                                    UPLOAD_PINS as SECOND_UPLOADS,
                                    DESCRIPTION_HASHES as SECOND_DESCRIPTION_HASHES,
                                    details as second_audition_details)
from purgatory3_pins import (SOURCE_PINS as PURGATORY3_SOURCES,
                             UPLOAD_PINS as PURGATORY3_UPLOADS,
                             DESCRIPTION_HASHES as PURGATORY3_DESCRIPTION_HASHES,
                             details as purgatory3_audition_details)
from reckless2_pins import (SOURCE_PINS as RECKLESS2_SOURCES,
                            UPLOAD_PINS as RECKLESS2_UPLOADS,
                            DESCRIPTION_HASHES as RECKLESS2_DESCRIPTION_HASHES,
                            details as reckless2_audition_details)

SOURCE_LIMIT = 64 * 1024 ** 2
ARTISTS = {'dos88': 'DOS-88', 'escp': 'escp', 'davidkbd': 'David KBD'}
ARTISTS.update({source: 'David KBD' for source in NEW_SOURCES})
ARTISTS.update({source: 'David KBD' for source in SECOND_SOURCES})
ARTISTS.update({source: 'David KBD' for source in PURGATORY3_SOURCES})
ARTISTS.update({source: 'David KBD' for source in RECKLESS2_SOURCES})
DESCRIPTION_HASHES = {
    **NEW_DESCRIPTION_HASHES,
    **SECOND_DESCRIPTION_HASHES,
    **PURGATORY3_DESCRIPTION_HASHES,
    **RECKLESS2_DESCRIPTION_HASHES,
}
PIN_FILES = (
    'intake/approved_directions_pins.py',
    'intake/second_directions_pins.py',
    'intake/purgatory3_pins.py',
    'intake/reckless2_pins.py',
)
SHARED_ACQUISITION_FILES = (
    *PIN_FILES,
    'intake/itch_source.py',
    'intake/itch_audio.py',
    'intake/prepare.py',
)
FORMATS = {
    '.mp3': ({'audio/mpeg', 'audio/mp3'}, {'mp3'}, {'mp3'}),
    '.ogg': ({'audio/ogg', 'application/ogg'}, {'ogg'}, {'vorbis', 'opus'}),
    '.wav': ({'audio/wav', 'audio/x-wav', 'audio/wave'}, {'wav'}, None),
    '.flac': ({'audio/flac', 'audio/x-flac'}, {'flac'}, {'flac'}),
}


def acquisition_source_files(entry_point, workflow, *batch_files):
    """Return a complete, deterministic source binding for one hosted entry point."""
    files = (*SHARED_ACQUISITION_FILES, *batch_files, entry_point, workflow)
    if len(files) != len(set(files)):
        raise ValueError('Acquisition source binding contains duplicate paths')
    if any(not isinstance(name, str) or not name or not Path(name).is_file() for name in files):
        raise ValueError('Acquisition source binding contains a missing path')
    return files


def identity(track_id):
    require(track_id in UPLOAD_PINS, 'Unregistered itch recording')
    creator, upload_id, upload_name, title = UPLOAD_PINS[track_id]
    source, game_id, _ = SOURCE_PINS[creator]
    result = {
        'id': track_id, 'title': title, 'artist': ARTISTS[creator],
        'artistURL': source.split('/')[0] + '//' + urlparse(source).netloc,
        'source': source, 'acquisition': 'itch-public-free-download',
        'gameId': game_id, 'uploadId': upload_id, 'uploadName': upload_name,
        'license': 'CC BY 4.0 International', 'licenseURL': LICENSE_URL,
        'family': 'metal' if creator == 'davidkbd' else 'synth90s',
        'contentId': 'unknown', 'recordingModeEligible': False,
        'status': 'rights-reviewed-listening-pending', 'instrumentalReview': 'pending',
    }
    if track_id in NEW_UPLOADS:
        result.update(audition_details(track_id))
    elif track_id in SECOND_UPLOADS:
        result.update(second_audition_details(track_id))
    elif track_id in PURGATORY3_UPLOADS:
        result.update(purgatory3_audition_details(track_id))
    elif track_id in RECKLESS2_UPLOADS:
        result.update(reckless2_audition_details(track_id))
    return result


def validate_row(row):
    expected = identity(row.get('id'))
    require(all(type(row.get(key)) is type(value) and row.get(key) == value
                for key, value in expected.items()), 'Itch intake identity or pending status changed')
    require(set(row) == set(expected) | {'credit'}
            and row['credit'] == credit(expected), 'Itch intake contains unreviewed fields or credits')
    return row


def credit(row):
    return (f'Music: {row["title"]} by {row["artist"]} ({row["source"]}). '
            f'Licensed under Creative Commons Attribution 4.0 International (CC BY 4.0): {LICENSE_URL}')


class EvidenceClient:
    def __init__(self, source):
        self.client = MetadataClient(source)
        self.source = source
        self.observation = None

    def read(self, url, data=None):
        body = self.client.read(url, data)
        if url == self.source:
            creator = next(key for key, item in SOURCE_PINS.items() if item[0] == self.source)
            self.observation = {
                'format': 'revealline-itch-public-license-observation.v1',
                'source': self.source, 'creator': ARTISTS[creator],
                'pageSha256': hashlib.sha256(body.encode('utf8')).hexdigest(),
                'observedLicenseLink': SOURCE_PINS[creator][2],
                'license': 'CC BY 4.0 International', 'licenseURL': LICENSE_URL,
                'snapshotKind': 'Verified public licence facts; raw session-bearing HTML is not retained',
                'listeningApproval': False, 'admitted': False,
            }
            if creator in DESCRIPTION_HASHES:
                self.observation.update({
                    'reviewedDescriptionSha256': DESCRIPTION_HASHES[creator],
                    'observedDirectLicenseLink': LICENSE_URL,
                })
        return body


def native_filename(headers, upload_name):
    values = headers.get_all('Content-Disposition', [])
    require(len(values) == 1 and len(values[0]) <= 2048
            and not any(ord(c) < 32 or ord(c) == 127 for c in values[0]),
            'Missing or ambiguous native Content-Disposition')
    # A comma is valid inside a quoted filename (for example
    # ``filename="Keep My Rhythm, If You Can.ogg"``), but an unquoted comma
    # can join multiple field values into one string.  Message.get_params()
    # otherwise accepts that combined form, so reject it before parsing while
    # retaining quoted-string escaping semantics.
    quoted = escaped = False
    for character in values[0]:
        if escaped:
            escaped = False
        elif quoted and character == '\\':
            escaped = True
        elif character == '"':
            quoted = not quoted
        elif character == ',' and not quoted:
            require(False, 'Missing or ambiguous native Content-Disposition')
    require(not quoted and not escaped, 'Missing or ambiguous native Content-Disposition')
    message = Message()
    message['Content-Disposition'] = values[0]
    params = message.get_params(header='content-disposition', unquote=True)
    require(params and params[0][0].lower() == 'attachment', 'Native response is not an attachment')
    names = [value for key, value in params[1:] if key.lower() == 'filename']
    require(len(names) == 1, 'Missing or ambiguous native filename')
    filename = collapse_rfc2231_value(names[0], errors='strict')
    require(isinstance(filename, str) and 1 <= len(filename) <= 255
            and filename == filename.strip() and filename not in {'.', '..'}
            and not re.search(r'[\\/\x00-\x1f\x7f]', filename)
            and not re.search(r'%[0-9a-fA-F]{2}|[\u2044\u2215\uff0f\uff3c]', filename)
            and not any(unicodedata.category(c).startswith('C') for c in filename),
            'Unsafe native filename')
    suffix = PurePosixPath(filename).suffix.lower()
    require(suffix in FORMATS, 'Native file is not an individually supported audio format')
    if PurePosixPath(upload_name).suffix:
        require(filename == upload_name, 'Native filename differs from the exact upload title')
    media_types = headers.get_all('Content-Type', [])
    require(len(media_types) == 1, 'Missing or ambiguous native media type')
    media_type = media_types[0].split(';', 1)[0].strip().lower()
    require(media_type in FORMATS[suffix][0] | {'application/octet-stream'},
            'Native filename and response media type differ')
    return filename, suffix, media_type


def fetch_media(resolution, opener=None):
    """No redirect, credentials, response headers or temporary URL leave this function."""
    pin = identity(resolution.track_id)
    require((resolution.source, resolution.game_id, resolution.upload_id, resolution.upload_name)
            == (pin['source'], pin['gameId'], pin['uploadId'], pin['uploadName']),
            'Resolved media identity differs from the reviewed recording')
    checked_cdn(resolution.download_url, resolution.game_id, resolution.upload_id)
    try:
        opener = opener or build_opener(NoRedirects())
        request = Request(resolution.download_url, headers={
            'User-Agent': 'RevealLine soundtrack archival intake/1.0',
            'Accept-Encoding': 'identity',
        })
        with opener.open(request, timeout=60) as response:
            require(response.url == resolution.download_url and response.status == 200,
                    'Unexpected media response or redirect')
            encodings = response.headers.get_all('Content-Encoding', [])
            require(not encodings or len(encodings) == 1 and encodings[0].lower() == 'identity',
                    'Encoded native response requires review')
            filename, suffix, media_type = native_filename(response.headers, resolution.upload_name)
            lengths = response.headers.get_all('Content-Length', [])
            require(len(lengths) <= 1 and (not lengths or
                    re.fullmatch(r'[0-9]+', lengths[0]) and 0 < int(lengths[0]) <= SOURCE_LIMIT),
                    'Native audio exceeds its bounded size')
            body = response.read(SOURCE_LIMIT + 1)
            require(0 < len(body) <= SOURCE_LIMIT
                    and (not lengths or len(body) == int(lengths[0])),
                    'Native audio is empty, truncated or exceeds its bounded size')
            return body, {
                'fileName': filename, 'suffix': suffix, 'contentType': media_type,
                'bytes': len(body), 'sha256': hashlib.sha256(body).hexdigest(),
            }
    except SourceChanged:
        raise
    except Exception:
        # urllib errors may include the entire signed request URL.
        raise SourceChanged('Native audio acquisition failed; temporary authorization omitted') from None


def acquire(row, client=None, opener=None):
    validate_row(row)
    client = client or EvidenceClient(row['source'])
    resolution = resolve(row['id'], client)
    observation = client.observation
    require(isinstance(observation, dict) and observation.get('source') == row['source'],
            'Public licence observation is missing')
    body, media = fetch_media(resolution, opener)
    safe = resolution.receipt()
    safe['audioAcquired'] = True
    return body, {**safe, 'native': media, 'licenseObservation': observation}


def validate_native_probe(suffix, probe):
    """Header extension must agree with the decoder, not just a server MIME claim."""
    formats = set(probe.get('format', {}).get('format_name', '').split(','))
    streams = probe.get('streams', [])
    audio = [stream for stream in streams if stream.get('codec_type') == 'audio']
    pictures = [stream for stream in streams if stream.get('codec_type') != 'audio']
    expected = FORMATS.get(suffix)
    require(expected and formats & expected[1] and len(audio) == 1
            and all(stream.get('codec_type') == 'video'
                    and stream.get('disposition', {}).get('attached_pic') == 1
                    for stream in pictures),
            'Native audio container or stream layout differs from its verified filename')
    codec = audio[0].get('codec_name', '')
    require((suffix == '.wav' and codec.startswith('pcm_'))
            or (expected[2] is not None and codec in expected[2]),
            'Native audio codec differs from its verified filename')
