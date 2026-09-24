#!/usr/bin/env python3
"""Prepare rights-reviewed candidates on a hosted runner; never approve or deploy music."""
import argparse
import hashlib
import html
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from itch_audio import acquire as acquire_itch, validate_row as validate_itch_row, validate_native_probe

RESERVE = 1024 ** 3
SOURCE_LIMIT = 64 * 1024 ** 2
TOTAL_LIMIT = 650 * 1024 ** 2
SCRATCH_LIMIT = 256 * 1024 ** 2
DERIVATIVE_LIMIT = 24 * 1024 ** 2  # more than 12 minutes at 256 kbps
VOLUME_LIMIT = 64 * 1024 ** 2
VOLUME_METADATA_RESERVATION = 512 * 1024
ROW_RESERVATION = 96 * 1024 ** 2  # bounded source, 12-minute MP3, page and receipts
INSPECTOR_REVISION = '71a0ffeaeb5079ac6e87a7d80327c6b34948aaa3'
LICENSES = {'CC0 1.0 Universal': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'CC BY 4.0 International': 'https://creativecommons.org/licenses/by/4.0/'}
CREATOR_SOURCE = 'https://creatorchords.com/music/carol-of-the-bells-metal-version/'
CREATOR_DOWNLOAD = 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/Carol_of_the_Bells_Metal_Version.mp3'
CREATOR_LICENSING = 'https://creatorchords.com/licensing-info/'
CREATOR_FAQ = 'https://creatorchords.com/faq/'
CREATOR_URLS = frozenset((CREATOR_SOURCE, CREATOR_DOWNLOAD, CREATOR_LICENSING, CREATOR_FAQ))
CREATOR_SOURCE_LIMIT = 11 * 1024 ** 2
CREATOR_IDENTITY = {
    'id': 'alexander-nakarada.carol-of-the-bells-metal-version',
    'title': 'Carol of the Bells (Metal Version)',
    'artist': 'Alexander Nakarada',
    'artistURL': 'https://creatorchords.com',
    'source': CREATOR_SOURCE,
    'download': CREATOR_DOWNLOAD,
    'license': 'CC BY 4.0 International',
    'licenseURL': LICENSES['CC BY 4.0 International'],
    'licensingInfo': CREATOR_LICENSING,
    'creatorFAQ': CREATOR_FAQ,
    'contentId': True,
    'recordingModeEligible': False,
    'culturalDescriptor': 'Ukrainian-melody metal adaptation',
    'culturalReview': 'pending',
    'instrumentalReview': 'pending',
}


# Exact creator page/download pairs. Acquisition never grants musical approval.
CREATOR_IDENTITIES = {CREATOR_SOURCE: CREATOR_IDENTITY}
for slug, title, download in (
    ('the-dobermann', 'The Dobermann', 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/The_Dobermann.mp3'),
    ('folklore', 'Folklore', 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/Folklore.mp3'),
    ('anemo', 'Anemo', 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/Anemo.mp3'),
    ('trial-of-thorns', 'Trial of Thorns', 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/Trial_of_Thorns.mp3'),
    ('riffs-two', 'Riffs Two', 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/Riffs_Two.mp3'),
    ('apocalypse', 'Apocalypse', 'https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/Apocalypse.mp3'),
):
    source = 'https://creatorchords.com/music/' + slug + '/'
    CREATOR_IDENTITIES[source] = {
        'id': 'alexander-nakarada.' + slug, 'title': title,
        'artist': 'Alexander Nakarada', 'artistURL': 'https://creatorchords.com',
        'source': source, 'download': download,
        'license': 'CC BY 4.0 International', 'licenseURL': LICENSES['CC BY 4.0 International'],
        'licensingInfo': CREATOR_LICENSING, 'creatorFAQ': CREATOR_FAQ,
        'contentId': True, 'recordingModeEligible': False, 'family': 'metal',
    }
CREATOR_URLS = frozenset((CREATOR_LICENSING, CREATOR_FAQ,
    *(r['source'] for r in CREATOR_IDENTITIES.values()),
    *(r['download'] for r in CREATOR_IDENTITIES.values())))
CREATOR_SOURCE_LIMITS = {source: CREATOR_SOURCE_LIMIT if source == CREATOR_SOURCE else 16 * 1024 ** 2
                         for source in CREATOR_IDENTITIES}

# These new pages expose their authoritative recording in one mainTrack element.
# Related recommendations must not establish a page/recording identity binding.
CREATOR_MAIN_TRACK_SOURCES = frozenset(
    'https://creatorchords.com/music/' + slug + '/'
    for slug in ('anemo', 'trial-of-thorns', 'riffs-two', 'apocalypse')
)
for source in CREATOR_MAIN_TRACK_SOURCES:
    CREATOR_IDENTITIES[source].update({
        'instrumentalReview': 'pending', 'fullTrackListening': False,
        'gameplayReview': 'pending',
    })


def digest(body):
    return hashlib.sha256(body).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def allowed_url(value):
    if value in CREATOR_URLS:
        return True
    try:
        url = urlparse(value)
        return (url.scheme == 'https' and url.hostname == 'opengameart.org'
                and url.port in (None, 443) and not url.username and not url.password
                and not url.fragment and not any(ord(char) < 33 for char in value))
    except (TypeError, ValueError):
        return False


def allowed_redirect(origin, destination):
    if origin in CREATOR_URLS:
        return destination == origin
    return allowed_url(destination) and urlparse(destination).hostname == 'opengameart.org'


class IntakeRedirectHandler(HTTPRedirectHandler):
    def __init__(self, origin):
        super().__init__()
        self.origin = origin

    def redirect_request(self, request, fp, code, message, headers, newurl):
        # Validate before urllib sends anything to the redirect destination.
        if not allowed_redirect(self.origin, newurl):
            raise ValueError('Unexpected redirect destination')
        return super().redirect_request(request, fp, code, message, headers, newurl)


def validate_manifest(value):
    if value.get('format') != 'revealline-core-intake.v1' or not 1 <= len(value.get('tracks', [])) <= 20:
        raise ValueError('Unsupported or excessive intake')
    ids = set()
    for row in value['tracks']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,79}', row['id']) or row['id'] in ids:
            raise ValueError('Invalid or duplicate identity')
        ids.add(row['id'])
        if row.get('licenseURL') != LICENSES.get(row.get('license')):
            raise ValueError('Unsupported exact source licence')
        if row.get('acquisition') == 'itch-public-free-download':
            validate_itch_row(row)
            continue
        if not allowed_url(row['source']) or not allowed_url(row['download']):
            raise ValueError('Unapproved source host')
        if row['source'] in CREATOR_IDENTITIES:
            identity = CREATOR_IDENTITIES[row['source']]
            if any(row.get(key) != expected or type(row.get(key)) is not type(expected)
                   for key, expected in identity.items()):
                raise ValueError('Creator recording differs from the reviewed identity and licence evidence')
        elif (urlparse(row['source']).hostname != 'opengameart.org'
              or urlparse(row['download']).hostname != 'opengameart.org'
              or not urlparse(row['download']).path.startswith('/sites/default/files/')):
            raise ValueError('Not an author-provided source/download pair')
        if row.get('status') != 'rights-reviewed-listening-pending':
            raise ValueError('Intake cannot grant listening approval')
    return value


def fetch(url, limit):
    if not allowed_url(url):
        raise ValueError('Unapproved source host')
    request = Request(url, headers={'User-Agent': 'RevealLine soundtrack archival intake/1.0'})
    opener = build_opener(IntakeRedirectHandler(url))
    for attempt in range(3):
        try:
            with opener.open(request, timeout=60) as response:
                if not allowed_redirect(url, response.url):
                    raise ValueError('Unexpected redirect destination')
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError('Source exceeds bounded intake size')
                return body, response.url
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


class SourceLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.main_tracks = []

    def handle_starttag(self, tag, attrs):
        self.links.extend(value for key, value in attrs
                          if key in ('href', 'src', 'data-src') and value)
        if any(key == 'id' and value == 'mainTrack' for key, value in attrs):
            # Duplicate identity attributes have ambiguous browser/parser semantics.
            keys = [key for key, _ in attrs]
            if any(keys.count(key) != 1 for key in ('id', 'data-title', 'data-src')):
                self.main_tracks.append(None)
            else:
                self.main_tracks.append(dict(attrs))


def validate_source_page(row, body):
    source = body.decode('utf8')
    parser = SourceLinks()
    parser.feed(source)
    if row['source'] in CREATOR_MAIN_TRACK_SOURCES:
        expected = CREATOR_IDENTITIES[row['source']]
        if (len(parser.main_tracks) != 1 or parser.main_tracks[0] is None
                or parser.main_tracks[0].get('data-title') != expected['title']
                or parser.main_tracks[0].get('data-src') != expected['download']):
            raise ValueError('Primary creator player differs from the reviewed recording')
    linked = {unquote(urljoin(row['source'], link)) for link in parser.links}
    if unquote(row['download']) not in linked:
        raise ValueError('Exact download is not linked by the reviewed creator page')
    normalized = unquote(html.unescape(source))
    if row['licenseURL'].removeprefix('https://') not in normalized:
        raise ValueError('Expected licence link is absent from creator snapshot')


def snapshot(url, output, pages):
    if url not in pages:
        body, final = fetch(url, 2 * 1024 ** 2)
        sha = digest(body)
        (output / 'evidence' / (sha + '.html')).write_bytes(body)
        pages[url] = (body, {'path': 'evidence/' + sha + '.html', 'sha256': sha, 'url': final})
    return pages[url]


def collect_evidence(row, output, pages, partial):
    body, partial['sourceSnapshot'] = snapshot(row['source'], output, pages)
    validate_source_page(row, body)
    if row['source'] in CREATOR_IDENTITIES:
        licensing, partial['licensingInfoSnapshot'] = snapshot(CREATOR_LICENSING, output, pages)
        _, partial['creatorFAQSnapshot'] = snapshot(CREATOR_FAQ, output, pages)
        text = html.unescape(licensing.decode('utf8'))
        if row['licenseURL'] not in text or 'Smart Content ID' not in text:
            raise ValueError('Creator licence or Content ID evidence has changed; review it before acquisition')
    return {key: value for key, value in partial.items() if key.endswith('Snapshot')}


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:])
    return result


def loudness(file, target=-16, peak=-1.5):
    result = command(['ffmpeg', '-hide_banner', '-nostdin', '-i', str(file), '-vn',
                      '-af', f'loudnorm=I={target}:TP={peak}:LRA=11:print_format=json',
                      '-f', 'null', '-'])
    match = re.search(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    if not match:
        raise ValueError('No complete loudness measurement')
    facts = json.loads(match.group())
    if not all(math.isfinite(float(facts[k])) for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')):
        raise ValueError('Silent or unmeasurable recording')
    return facts


def reserve(root, requested=ROW_RESERVATION):
    if shutil.disk_usage(root).free < RESERVE + requested:
        raise ValueError('Intake must leave at least 1 GiB free')


def reserve_row(root):
    used = sum(file.stat().st_size for file in root.rglob('*') if file.is_file())
    if used + ROW_RESERVATION > TOTAL_LIMIT:
        raise ValueError('Next recording would exceed the 650 MiB production reservation')
    scratch = sum(file.stat().st_size for file in root.glob('candidate-*.mp3') if file.is_file())
    if scratch + DERIVATIVE_LIMIT > SCRATCH_LIMIT:
        raise ValueError('Next recording would exceed the 256 MiB scratch reservation')
    reserve(root)


def verify_storage(root):
    files = [file for file in root.rglob('*') if file.is_file()]
    if sum(file.stat().st_size for file in files) > TOTAL_LIMIT:
        raise ValueError('Active production storage exceeds 650 MiB')
    if sum(file.stat().st_size for file in root.glob('candidate-*.mp3') if file.is_file()) > SCRATCH_LIMIT:
        raise ValueError('Active scratch exceeds 256 MiB')
    reserve(root, requested=0)


def delivery_volumes(tracks):
    """Partition actual MP3 bytes; no oversized collection is labelled a 64 MiB album."""
    volumes = []
    families = sorted({track.get('family', 'unassigned') for track in tracks})
    for family in families:
        volume = None
        for track in (row for row in tracks if row.get('family', 'unassigned') == family):
            size = track['delivery']['bytes']
            if type(size) is not int or not 0 < size <= VOLUME_LIMIT - VOLUME_METADATA_RESERVATION:
                raise ValueError('Delivery recording exceeds the optional volume budget')
            if volume is None or volume['audioBytes'] + size + VOLUME_METADATA_RESERVATION > VOLUME_LIMIT:
                volume = {'family': family, 'number': len(volumes) + 1, 'audioBytes': 0,
                          'metadataReservationBytes': VOLUME_METADATA_RESERVATION,
                          'maximumBytes': VOLUME_LIMIT, 'tracks': [],
                          'status': 'size-checked-plan-listening-pending'}
                volumes.append(volume)
            volume['audioBytes'] += size
            volume['tracks'].append(track['id'])
    return volumes


def itch_evidence(row, output, partial):
    body, receipt = acquire_itch(row)
    # Resolution receipt contains only pinned identities and a CDN path, never
    # authorization/session material. Preserve a semantic, hashed source snapshot.
    encoded = (json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf8')
    sha = digest(encoded)
    path = 'evidence/' + sha + '.json'
    (output / path).write_bytes(encoded)
    partial['sourceSnapshot'] = {'path': path, 'sha256': sha, 'url': row['source'],
                                 'snapshotKind': 'itch-public-license-and-native-acquisition'}
    return body, receipt['native'], {'sourceSnapshot': partial['sourceSnapshot']}


def inspect_mp3(file, game_root):
    module = (game_root / 'game/mp3.mjs').resolve().as_uri()
    code = ("import{readFile}from'node:fs/promises';"
            f"import{{inspectMP3}}from{json.dumps(module)};"
            "console.log(JSON.stringify(await inspectMP3(new Blob([await readFile(process.argv[1])],{type:'audio/mpeg'}))));")
    return json.loads(command(['node', '--input-type=module', '-e', code, str(file)]).stdout)


def verify_inspector(game_root):
    revision = command(['git', '-C', str(game_root), 'rev-parse', 'HEAD']).stdout.strip()
    if revision != INSPECTOR_REVISION:
        raise ValueError('Game inspector checkout differs from the reviewed revision')
    pins = []
    for name in ('mp3.mjs', 'data-json.mjs', 'soundtrack.mjs', 'soundtrack-rights.mjs', 'ui/music.mjs', 'content/soundtrack-catalogue.mjs'):
        relative = 'game/' + name
        expected = subprocess.run(['git', '-C', str(game_root), 'show', 'HEAD:' + relative], capture_output=True, check=True).stdout
        actual = (game_root / relative).read_bytes()
        if expected != actual:
            raise ValueError('Game inspector files differ from the reviewed source')
        pins.append({'path': relative, 'sha256': digest(actual)})
    return {'revision': revision, 'files': pins}


def prepare(manifest, output, game_root):
    manifest_bytes = manifest.read_bytes()
    rows = validate_manifest(json.loads(manifest_bytes))['tracks']
    inspector = verify_inspector(game_root)
    if output.exists():
        raise ValueError('Choose a fresh output directory; never overwrite evidence')
    reserve(output.parent)
    output.mkdir()
    for name in ('objects', 'originals', 'evidence'):
        (output / name).mkdir()
    receipt = {'format': 'revealline-core-intake-receipt.v1', 'sourceManifestSha256': digest(manifest_bytes),
               'checkedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'runnerRevision': os.environ.get('GITHUB_SHA'), 'runnerRun': os.environ.get('GITHUB_RUN_ID'),
               'ffmpeg': command(['ffmpeg', '-version']).stdout.splitlines()[0],
               'gameInspector': inspector,
               'listeningApproval': False, 'tracks': [], 'failures': []}
    known = json.loads(Path('preview-catalogue.json').read_text())['tracks']
    known_hashes = {track['sha256'] for track in known}
    known_titles = {re.sub(r'[^a-z0-9]', '', track['title'].lower()) for track in known}
    pages = {}
    source_hashes = set()
    for row in rows:
        partial = {'id': row['id'], 'source': row['source'], 'loudnessAttempts': []}
        if 'download' in row:
            partial['download'] = row['download']
        try:
            reserve_row(output)
            is_itch = row.get('acquisition') == 'itch-public-free-download'
            if is_itch:
                body, native, evidence = itch_evidence(row, output, partial)
                suffix = native['suffix']
                source_details = {'source': row['source'], 'uploadId': row['uploadId'],
                                  'fileName': native['fileName'], 'contentType': native['contentType']}
            else:
                evidence = collect_evidence(row, output, pages, partial)
                body, final = fetch(row['download'], CREATOR_SOURCE_LIMITS.get(row['source'], SOURCE_LIMIT))
                suffix = Path(urlparse(final).path).suffix
                source_details = {'url': final}
            source_sha = digest(body)
            if source_sha in known_hashes or source_sha in source_hashes or re.sub(r'[^a-z0-9]', '', row['title'].lower()) in known_titles:
                raise ValueError('Recording already exists in the admitted collection')
            source_hashes.add(source_sha)
            original = output / 'originals' / (source_sha + suffix)
            original.write_bytes(body)
            partial['original'] = {'path': str(original.relative_to(output)), 'sha256': source_sha, 'bytes': len(body), **source_details}
            del body
            probe = json.loads(command(['ffprobe', '-v', 'error',
                                        '-show_entries', 'format=duration,format_name:stream=codec_type,codec_name,sample_rate,channels:stream_disposition=attached_pic',
                                        '-of', 'json', str(original)]).stdout)
            if is_itch:
                validate_native_probe(suffix, probe)
            verify_storage(output)
            duration = float(probe['format']['duration'])
            if not 60 <= duration <= 720:
                raise ValueError('Recording is outside the 1–12 minute candidate envelope')
            command(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(original), '-map', '0:a:0', '-f', 'null', '-'])
            measured = loudness(original)
            partial['sourceLoudness'] = measured
            normalized_path = output / ('candidate-' + row['id'] + '.mp3')
            measured_output = None
            for peak in (-1.5, -2.0, -2.5):
                filter_value = (f'loudnorm=I=-16:TP={peak}:LRA=11:measured_I={measured["input_i"]}'
                                f':measured_TP={measured["input_tp"]}:measured_LRA={measured["input_lra"]}'
                                f':measured_thresh={measured["input_thresh"]}:offset={measured["target_offset"]}'
                                ':linear=true:print_format=json')
                command(['ffmpeg', '-v', 'error', '-y', '-nostdin', '-i', str(original), '-map', '0:a:0',
                         '-map_metadata', '-1', '-vn', '-af', filter_value, '-ar', '44100', '-ac', '2',
                         '-c:a', 'libmp3lame', '-b:a', '256k', '-id3v2_version', '3',
                         '-fs', str(DERIVATIVE_LIMIT), str(normalized_path)])
                if normalized_path.stat().st_size >= DERIVATIVE_LIMIT:
                    raise ValueError('Derivative reached the scratch file limit')
                verify_storage(output)
                command(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(normalized_path), '-f', 'null', '-'])
                measured_output = loudness(normalized_path)
                partial['loudnessAttempts'].append({'targetPeak': peak, 'measurement': measured_output})
                if -17 <= float(measured_output['input_i']) <= -15 and float(measured_output['input_tp']) <= -1:
                    break
            else:
                raise ValueError('Encoded loudness or true peak misses target')
            data = normalized_path.read_bytes()
            audio_hash = digest(data)
            if audio_hash in known_hashes:
                raise ValueError('Duplicate encoded recording')
            known_hashes.add(audio_hash)
            facts = inspect_mp3(normalized_path, game_root)
            destination = output / 'objects' / (audio_hash + '.mp3')
            normalized_path.rename(destination)
            receipt['tracks'].append({**row, **evidence,
                'original': {'path': str(original.relative_to(output)), 'sha256': source_sha, 'bytes': original.stat().st_size, **source_details},
                'delivery': {'path': str(destination.relative_to(output)), 'sha256': audio_hash, 'bytes': len(data)},
                'asset': facts, 'durationSeconds': duration, 'sourceLoudness': measured, 'encodedLoudness': measured_output,
                'completeDecode': True, 'listeningApproval': False,
                'changes': 'Converted to 256 kbps stereo MP3 at 44.1 kHz with two-pass loudness normalization; native source retained unchanged.'})
            receipt['deliveryVolumes'] = delivery_volumes(receipt['tracks'])
            print(f'Prepared {row["id"]}: {duration:.1f}s, {measured_output["input_i"]} LUFS, {measured_output["input_tp"]} dBTP', flush=True)
        except Exception as error:
            attempted = output / ('candidate-' + row['id'] + '.mp3')
            if attempted.is_file():
                partial['failedDerivative'] = {'path': attempted.name, 'bytes': attempted.stat().st_size, 'sha256': digest(attempted.read_bytes())}
            receipt['failures'].append({**partial, 'error': str(error)})
            print(f'FAILED {row["id"]}: {error}', flush=True)
        write_json(output / 'receipt.json', receipt)
        verify_storage(output)
    write_json(output / 'review.json', {'status': 'pending', 'tracks': [{'id': r['id'], 'sha256': r['delivery']['sha256'], 'fullTrackListening': False, 'transitions': False, 'warningAudibility': False} for r in receipt['tracks']]})
    verify_storage(output)
    if receipt['failures']:
        raise SystemExit('Partial intake retained; review receipt failures')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--game-root', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.manifest, args.output, args.game_root)
