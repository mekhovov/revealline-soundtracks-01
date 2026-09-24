"""Assemble exact prior hosted candidates; never regenerate audio or publish main."""
import base64
import hashlib
import html
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import zipfile

from prepare_approved_directions import checked_manifest, MANIFEST_SHA256
from prepare import delivery_volumes, INSPECTOR_REVISION, validate_source_page
from approved_directions_pins import UPLOAD_PINS, DESCRIPTION_HASHES

REPOSITORY = 'mekhovov/revealline-soundtracks-01'
BRANCH = 'codex/approved-directions-publication'
RUN = 36067987427
ARTIFACT = 10836959665
ZIP_BYTES = 128698822
ZIP_SHA = 'b632cb216cbb64db5bb08287a0e63eaebfdbf347d173f1cfe5c796c79670885c'
SOURCE_HEAD = 'ce8ec098b9d400f8a4b2fdba77f8dc548e09375e'
RUNNER = '4c58001367033ede0f2566a572e4813426d61267'
SOURCE_TREE = 'c19d3cb93ddfd3d0a947a2cb94adb86ef1f91d4f'
SOURCE_BASE = 'ea40d9fc5583a643e8bb2d6cdc69d885960f354f'
MERGED_SOURCE = '0df64cecbe82c6d000780562e3ca0718981e64d0'
ARCHIVE = 'intake/archive/approved-directions-audition-20260925'
SITE = 'https://mekhovov.github.io/revealline-soundtracks-01/'
PREFIX = 'candidate-output/'
BATCH_IDS = {'synth90s': 'synth-approved-directions-audition-20260925',
             'metal': 'metal-approved-directions-audition-20260925'}
TITLES = {'synth90s': 'Synth and electro auditions', 'metal': 'EDM, techno and extreme metal auditions'}
TEMPLATE = 'batches/synth-audition-20260924'
TESTS_FILE = 'approved-directions-tests.txt'
EXPECTED_TEST_COUNT = 81
ARTIFACT_NAME = 'approved-directions-audition-candidates'
WORKFLOW_PATH = '.github/workflows/approved-directions-intake.yml'
BINDING_FORMAT = 'revealline-approved-directions-intake-binding.v1'
SOURCE_FILES = (
    'intake/approved_directions_pins.py',
    'intake/itch_source.py',
    'intake/itch_audio.py',
    'intake/prepare.py',
    'intake/prepare_approved_directions.py',
    '.github/workflows/approved-directions-intake.yml',
)
BASE_RECORDINGS = 104
PUBLIC_RECORDINGS = 116
MAX_PRODUCTION = 650 * 1024 ** 2
MAX_SCRATCH = 256 * 1024 ** 2
MAX_VOLUME = 64 * 1024 ** 2
INSPECTOR_PINS = {
    'game/mp3.mjs': 'd4f36f5f7760fc8d6482c716f944ff2e4df931a74e8c3f6f1684b90b7410d92a',
    'game/data-json.mjs': 'bcf8c3cb859473a39973cc93cee347085d3146164b0b92a02e81df57f6ffc823',
    'game/soundtrack.mjs': 'ec03303d295b4f7997f4b8c3c3573cf2bdddcd81f92700d98710d38933f89843',
    'game/soundtrack-rights.mjs': '8c1c10927cf5c1f7360374ca1a4d64a7dec3c312b197ace89201c37d75793f04',
    'game/ui/music.mjs': 'a1ecafd319417d075ec584d8b2f54008a8b877e49848e364bd91603896c44fda',
    'game/content/soundtrack-catalogue.mjs': '0618993ff8ff9508d1ab4295920c07d0b5a8f6f34df683538029754b438dc44f',
}


def demand(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def pin(name, data):
    return {'path': name, 'bytes': len(data), 'sha256': digest(data)}


def api(endpoint):
    # Metadata only. Audio bytes use the separate fixed-size stream below.
    result = subprocess.run(['gh', 'api', endpoint], capture_output=True, check=True)
    demand(len(result.stdout) <= 8 * 1024 ** 2, 'GitHub metadata exceeds limit')
    return json.loads(result.stdout)


def validate_remote(metadata, run, source, runner):
    demand(metadata.get('id') == ARTIFACT and metadata.get('size_in_bytes') == ZIP_BYTES
           and metadata.get('digest') == 'sha256:' + ZIP_SHA and metadata.get('expired') is False
           and metadata.get('name') == ARTIFACT_NAME
           and metadata.get('workflow_run', {}).get('head_sha') == SOURCE_HEAD
           and metadata['workflow_run'].get('id') == RUN, 'Original artifact metadata changed')
    demand(run.get('id') == RUN and run.get('head_sha') == SOURCE_HEAD
           and run.get('conclusion') == 'success' and run.get('event') == 'pull_request'
           and run.get('path') == WORKFLOW_PATH,
           'Original workflow identity or result changed')
    demand(source.get('sha') == SOURCE_HEAD and runner.get('sha') == RUNNER
           and source.get('tree', {}).get('sha') == SOURCE_TREE
           and runner.get('tree', {}).get('sha') == SOURCE_TREE
           and [p['sha'] for p in runner.get('parents', [])] == [SOURCE_BASE, SOURCE_HEAD],
           'Original source and runner tree binding differs')


def download_original():
    endpoint = f'repos/{REPOSITORY}/actions/artifacts/{ARTIFACT}/zip'
    process = subprocess.Popen(['gh', 'api', endpoint], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    data = bytearray()
    try:
        while True:
            block = process.stdout.read(min(1024 * 1024, ZIP_BYTES + 1 - len(data)))
            if not block:
                break
            data.extend(block)
            demand(len(data) <= ZIP_BYTES, 'Artifact stream exceeded its exact size')
        demand(process.wait(timeout=60) == 0, 'Original artifact download failed')
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    demand(len(data) == ZIP_BYTES and digest(data) == ZIP_SHA, 'Original ZIP digest or length differs')
    return data


def checked_members(data):
    demand(len(data) == ZIP_BYTES and digest(data) == ZIP_SHA, 'Original ZIP digest or length differs')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        demand(1 <= len(infos) <= 64, 'Unexpected artifact member count')
        names = set()
        total = 0
        for info in infos:
            name = info.filename
            allowed = (name == TESTS_FILE
                       or re.fullmatch(r'candidate-output/(?:receipt|review|intake-binding|source-manifest)\.json', name)
                       or re.fullmatch(r'candidate-output/(?:objects|originals|evidence)/[0-9a-f]{64}\.(?:mp3|ogg|json|html)', name))
            demand(allowed and name not in names and not info.is_dir()
                   and not stat.S_ISLNK(info.external_attr >> 16)
                   and not (info.flag_bits & 1) and 0 < info.file_size <= 64 * 1024 ** 2,
                   'Unexpected, duplicate, unsafe or excessive artifact member')
            names.add(name)
            total += info.file_size
        demand(total < MAX_SCRATCH and len(data) < MAX_SCRATCH,
               'Artifact archive or extracted member set exceeds 256 MiB')
        # ZipFile.read verifies each member CRC. All members are preserved exactly.
        return {info.filename: archive.read(info) for info in infos}


def checked_receipt(files, expected_source_files):
    source_bytes = files[PREFIX + 'source-manifest.json']
    manifest = checked_manifest(source_bytes)
    receipt = json.loads(files[PREFIX + 'receipt.json'])
    binding = json.loads(files[PREFIX + 'intake-binding.json'])
    demand(receipt.get('format') == 'revealline-core-intake-receipt.v1'
           and receipt.get('sourceManifestSha256') == MANIFEST_SHA256
           and receipt.get('runnerRevision') == RUNNER and str(receipt.get('runnerRun')) == str(RUN)
           and receipt.get('failures') == [] and receipt.get('listeningApproval') is False,
           'Intake receipt is incomplete or bound to another run')
    demand(binding.get('format') == BINDING_FORMAT
           and binding.get('sourceManifestSha256') == MANIFEST_SHA256
           and binding.get('runnerRevision') == RUNNER and binding.get('eventHeadRevision') == SOURCE_HEAD
           and str(binding.get('runnerRun')) == str(RUN)
           and binding.get('sourceFiles') == expected_source_files
           and all(binding.get(flag) is False for flag in
                   ('publicationApproval', 'gameCatalogueAdmission', 'listeningApproval')),
           'Hosted intake source binding changed')
    inspector = receipt.get('gameInspector', {})
    demand(inspector.get('revision') == INSPECTOR_REVISION
           and inspector.get('files') == [{'path': p, 'sha256': h} for p, h in INSPECTOR_PINS.items()],
           'Pinned game inspector differs')
    tests = files[TESTS_FILE].decode()
    demand(re.search(rf'Ran {EXPECTED_TEST_COUNT} tests in [0-9.]+s', tests) and '\nOK\n' in tests
           and 'FAILED' not in tests, 'Original hosted source tests did not pass')
    rows = receipt.get('tracks', [])
    demand([r.get('id') for r in rows] == [r['id'] for r in manifest['tracks']], 'Slate identities or order differ')
    used = {PREFIX + n for n in ('source-manifest.json', 'intake-binding.json', 'receipt.json', 'review.json')}
    used.add(TESTS_FILE)
    hashes = set()
    for row, source in zip(rows, manifest['tracks']):
        demand(all(type(row.get(k)) is type(v) and row.get(k) == v for k, v in source.items()),
               'Recording identity, rights or pending metadata changed')
        demand(row.get('completeDecode') is True and row.get('listeningApproval') is False
               and 60 <= row.get('durationSeconds', 0) <= 720,
               'Recording lacks complete decoding or duration evidence')
        measured = row.get('encodedLoudness', {})
        demand(-17 <= float(measured.get('input_i', 'nan')) <= -15
               and float(measured.get('input_tp', 'nan')) <= -1,
               'Encoded loudness or true peak misses target')
        for key, directory in (('original', 'originals'), ('delivery', 'objects')):
            member = row[key]
            expected = directory + '/' + member['sha256']
            demand(member['path'].startswith(expected + '.')
                   and (key != 'delivery' or member['path'] == expected + '.mp3'),
                   'Recording path differs from hash')
            full = PREFIX + member['path']
            body = files[full]
            demand(len(body) == member['bytes'] and digest(body) == member['sha256'], 'Recording bytes differ')
            demand(member['sha256'] not in hashes, 'Duplicate native or delivery recording')
            hashes.add(member['sha256'])
            used.add(full)
        evidence = row['sourceSnapshot']
        full = PREFIX + evidence['path']
        demand(evidence['url'] == source['source'] and digest(files[full]) == evidence['sha256'],
               'Source/licence evidence differs')
        if source.get('acquisition') == 'itch-public-free-download':
            observed = json.loads(files[full])
            creator = UPLOAD_PINS[source['id']][0]
            demand(all(observed.get(k) == source[k] for k in
                       ('id', 'title', 'source', 'gameId', 'uploadId', 'uploadName', 'license', 'licenseURL'))
                   and observed.get('audioAcquired') is True
                   and observed.get('listeningApproval') is False and observed.get('admitted') is False
                   and observed.get('native', {}).get('sha256') == row['original']['sha256']
                   and observed.get('native', {}).get('bytes') == row['original']['bytes']
                   and observed.get('licenseObservation', {}).get('reviewedDescriptionSha256') == DESCRIPTION_HASHES[creator]
                   and observed['licenseObservation'].get('observedDirectLicenseLink') == source['licenseURL'],
                   'Exact itch acquisition or licence observation changed')
        else:
            validate_source_page(source, files[full])
        used.add(full)
    demand(used == set(files), 'Artifact contains unreferenced or missing evidence')
    review = json.loads(files[PREFIX + 'review.json'])
    demand(review == {'status': 'pending', 'tracks': [
        {'id': r['id'], 'sha256': r['delivery']['sha256'], 'fullTrackListening': False,
         'transitions': False, 'warningAudibility': False} for r in rows]}, 'Review flags changed')
    demand(receipt.get('deliveryVolumes') == delivery_volumes(rows), 'Delivery volume plan differs')
    return receipt


def page(title, tracks, other):
    esc = html.escape
    cards = []
    for t in tracks:
        duration = f'{int(t["durationSeconds"]) // 60}:{int(t["durationSeconds"]) % 60:02}'
        vocal = 'Creator-described vocals; lyrics and explicit-content suitability remain pending.' if t['vocalContent'] == 'creator-described-vocals' else 'Vocal and instrumental review remain pending.'
        cards.append(f'<article class="track" data-genres="{t["family"]}" data-search="{esc((t["title"] + " " + t["artist"]).lower(), quote=True)}"><button class="play-track" type="button" aria-label="Play {esc(t["title"], quote=True)}">▶</button><div class="track-main"><h2>{esc(t["title"])}</h2><p class="artist"><a href="{esc(t["artistURL"])}" rel="noopener noreferrer">{esc(t["artist"])}</a></p><p class="tags">{duration} · Audition · Listening pending</p><details><summary>Credits and recording details</summary><p>{esc(t["credit"])}</p><p>{esc(t["changes"])}</p><p>{vocal}</p><p>Content ID is unknown; Recording mode eligibility remains off. No game admission or default selection.</p><p>Source filename: <span class="filename">{esc(t["originalFilename"])}</span></p><p>SHA-256: <code>{t["sha256"]}</code></p></details></div><div class="links"><a href="{t["path"]}" download="{esc(t["title"], quote=True)}.mp3">MP3 ↓</a><a href="{esc(t["source"])}" rel="noopener noreferrer">Creator source ↗</a><a href="{t["licenseURL"]}" rel="license">CC BY 4.0</a></div></article>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="dark"><title>RevealLine · {esc(title)}</title><link rel="stylesheet" href="style.css"><script type="module" src="player.mjs"></script></head>
<body><a class="skip" href="#recordings">Skip to recordings</a><main><header><p class="eyebrow">REVEALLINE / LISTENING AUDITIONS</p><h1>{esc(title)}</h1><p class="intro">Six complete recordings following the requested music direction. Musical fit and full listening remain pending.</p><p class="notice">These are licensed auditions, with no game admission or default selection. Content ID is unknown and gameplay-video eligibility is unverified.</p><nav><a href="../../">All soundtracks</a><a href="../{other}/">Other new auditions</a><a href="preview-catalogue.json">Credits and licence</a><a href="inventory.json">Exact MP3 inventory</a></nav></header>
<section class="player" aria-labelledby="player-heading"><div><p class="eyebrow" id="player-heading">NOW PLAYING</p><p id="now-playing" aria-live="polite">Choose a recording below.</p></div><audio id="audio" controls preload="none"></audio><div class="transport"><button id="pause" type="button" disabled>Pause music</button><button id="next" type="button">Next →</button><label><input id="shuffle" type="checkbox" checked> Shuffle</label><span>Repeat all</span></div><p id="playback-status" role="status"></p></section>
<section class="filters"><label>Search <input id="search" type="search" placeholder="Song or artist"></label><label>Style <select id="genre"><option value="">All styles</option><option value="synth90s">Synth/electro</option><option value="metal">Metal/fusion</option></select></label><p id="count">6 recordings</p></section><section id="recordings">{''.join(cards)}<p id="empty" hidden>No matching recordings.</p></section><footer><p>Native sources, licence evidence and technical receipts are retained unchanged in the repository. Complete listening, transitions, warning audibility, offline and device checks remain pending.</p></footer></main></body></html>
'''.encode()


def build_batch(family, rows, files, templates):
    batch_id = BATCH_IDS[family]
    tracks = []
    payload = {}
    for row in rows:
        t = {k: v for k, v in row.items() if k not in ('delivery', 'asset')}
        t.update(row['delivery'])
        t.update({'genres': [family], 'tags': [family, 'audition', 'listening pending'],
                  'reviewStatus': 'pending', 'default': False, 'gameCatalogueAdmission': False,
                  'originalFilename': row['original'].get('fileName', row['title'] + '.mp3')})
        tracks.append(t)
        payload[t['path']] = files[PREFIX + t['path']]
    inventory = {'format': 'revealline-soundtrack-archive.v1', 'id': batch_id,
                 'files': [pin(t['path'], payload[t['path']]) for t in tracks]}
    payload['inventory.json'] = encoded(inventory)
    catalogue = {'format': 'revealline-licensed-preview-catalogue.v1', 'status': 'licensed-preview',
                 'gameCatalogueAdmission': False, 'listeningApproval': 'not-reviewed',
                 'archive': {'id': batch_id, 'baseURL': SITE + 'batches/' + batch_id + '/',
                             'inventorySha256': digest(payload['inventory.json'])},
                 'source': {'run': RUN, 'artifactId': ARTIFACT, 'artifactSha256': ZIP_SHA,
                            'retainedArchivePath': ARCHIVE + '/'}, 'tracks': tracks}
    payload['preview-catalogue.json'] = encoded(catalogue)
    other = next(value for key, value in BATCH_IDS.items() if key != family)
    payload['index.html'] = page(TITLES[family], tracks, other)
    payload.update(templates)
    payload['.nojekyll'] = b''
    payload['README.md'] = (f'# {TITLES[family]}\n\nSix distinct licensed auditions. Full listening and game admission remain pending. '
                           f'No default changes. Search, play/pause, next, shuffle and repeat-all are available here and in the unified archive.\n\n'
                           f'Original hosted intake: https://github.com/{REPOSITORY}/actions/runs/{RUN}\n'
                           f'Exact native sources and technical evidence: `{ARCHIVE}/`.\n').encode()
    payload['CREDITS.md'] = ('# Credits\n\n' + '\n\n'.join(
        f'## {t["title"]}\n\n{t["credit"]}\n\n{t["changes"]}\n\nSource: {t["source"]}\n\nSHA-256: `{t["sha256"]}`. '
        'Content ID unknown; Recording mode disabled; listening and explicit-content review pending.' for t in tracks) + '\n').encode()
    manifest = {'format': 'revealline-soundtrack-preview-deployment.v1', 'id': batch_id,
                'expected': {'trackCount': len(tracks), 'audioBytes': sum(t['bytes'] for t in tracks)},
                'files': [pin(name, body) for name, body in sorted(payload.items())],
                'provenance': {'sourceRun': RUN, 'artifactId': ARTIFACT, 'artifactSha256': ZIP_SHA,
                               'sourceManifestSha256': MANIFEST_SHA256, 'gameCatalogueAdmission': False,
                               'listeningApproval': False}}
    payload['deployment-manifest.json'] = encoded(manifest)
    demand(sum(len(b) for b in payload.values()) < MAX_VOLUME, 'Complete preview volume exceeds 64 MiB')
    return payload


def main():
    demand(os.environ.get('GITHUB_ACTIONS') == 'true' and os.environ.get('GITHUB_EVENT_NAME') == 'workflow_dispatch'
           and os.environ.get('GITHUB_REPOSITORY') == REPOSITORY
           and os.environ.get('GITHUB_REF_NAME') == BRANCH, 'Assembly is restricted to the hosted publication branch')
    demand(not subprocess.check_output(['git', 'status', '--porcelain']).strip(), 'Source checkout must be clean')
    api_root = f'repos/{REPOSITORY}/'
    metadata = api(api_root + f'actions/artifacts/{ARTIFACT}')
    run = api(api_root + f'actions/runs/{RUN}')
    source = api(api_root + 'git/commits/' + SOURCE_HEAD)
    runner = api(api_root + 'git/commits/' + RUNNER)
    validate_remote(metadata, run, source, runner)
    demand(shutil.disk_usage('.').free >= 1024 ** 3 + MAX_PRODUCTION, 'Assembly must preserve 1 GiB free')
    data = download_original()
    files = checked_members(data)
    del data
    expected_files = {}
    for name in SOURCE_FILES:
        blob = api(api_root + 'contents/' + name + '?ref=' + SOURCE_HEAD)
        demand(blob.get('type') == 'file' and blob.get('encoding') == 'base64', 'Original source file missing')
        expected_files[name] = digest(base64.b64decode(blob['content']))
    receipt = checked_receipt(files, expected_files)
    old_catalogue = json.loads(Path('catalogue.json').read_bytes())
    demand(old_catalogue['counts']['uniqueRecordings'] == BASE_RECORDINGS
           and len(old_catalogue['tracks']) == BASE_RECORDINGS,
           'Refresh against a changed archive baseline before assembly')
    known_ids = {r['id'] for r in old_catalogue['tracks']}
    known_hashes = {r['audio']['sha256'] for r in old_catalogue['tracks']}
    for row in receipt['tracks']:
        demand(row['id'] not in known_ids and row['original']['sha256'] not in known_hashes
               and row['delivery']['sha256'] not in known_hashes, 'Candidate duplicates a public recording')
    templates = {name: Path(TEMPLATE, name).read_bytes() for name in ('player.mjs', 'style.css')}
    batches = {family: build_batch(family, [r for r in receipt['tracks'] if r['family'] == family], files, templates)
               for family in BATCH_IDS}
    demand(all(len([r for r in receipt['tracks'] if r['family'] == f]) == 6 for f in BATCH_IDS), 'Expected six/six split changed')
    production_bytes = sum(map(len, files.values())) + sum(sum(map(len, p.values())) for p in batches.values())
    demand(production_bytes < MAX_PRODUCTION, 'Assembly exceeds the production budget')
    destinations = [Path(ARCHIVE), *(Path('batches', batch) for batch in BATCH_IDS.values())]
    demand(all(not p.exists() and not p.is_symlink() for p in destinations), 'Immutable archive or batch already exists')
    # All identities, rights, bytes and budgets are checked before writing. A
    # failed hosted job retains its workspace evidence but never pushes a commit.
    for name, body in files.items():
        target = Path(ARCHIVE, 'hosted-artifact', name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
    binding = {'format': 'revealline-audition-assembly.v1', 'artifactId': ARTIFACT, 'artifactBytes': ZIP_BYTES,
               'artifactSha256': ZIP_SHA, 'sourceRun': RUN, 'sourceHead': SOURCE_HEAD, 'runnerRevision': RUNNER,
               'sourceTree': SOURCE_TREE, 'mergedSource': MERGED_SOURCE, 'sourceManifestSha256': MANIFEST_SHA256,
               'assemblyRevision': os.environ['GITHUB_SHA'], 'assemblyRun': os.environ['GITHUB_RUN_ID'],
               'originalArtifactInspection': 'Verified by this hosted assembler; independent publication review pending',
               'gameCatalogueAdmission': False, 'listeningApproval': False, 'default': False}
    Path(ARCHIVE, 'artifact-binding.json').write_bytes(encoded(binding))
    Path(ARCHIVE, 'artifact-member-hashes.json').write_bytes(encoded({
        'format': 'revealline-artifact-member-hashes.v1', 'artifactSha256': ZIP_SHA,
        'files': [pin(name, body) for name, body in sorted(files.items())]}))
    index = json.loads(Path('batches.json').read_bytes())
    volumes = []
    for family, payload in batches.items():
        batch_id = BATCH_IDS[family]
        for name, body in payload.items():
            target = Path('batches', batch_id, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
        manifest_pin = pin(f'batches/{batch_id}/deployment-manifest.json', payload['deployment-manifest.json'])
        index['batches'].append({'id': batch_id, 'manifest': manifest_pin})
        volumes.append({'id': batch_id, 'totalBytes': sum(map(len, payload.values())), 'manifest': manifest_pin})
    Path('batches.json').write_bytes(encoded(index))
    subprocess.run(['node', 'intake/build-unified-catalogue.mjs', '--write'], check=True)
    new_catalogue = json.loads(Path('catalogue.json').read_bytes())
    demand(new_catalogue['counts']['uniqueRecordings'] == PUBLIC_RECORDINGS
           and new_catalogue['tracks'][:BASE_RECORDINGS] == old_catalogue['tracks'],
           'Existing public entries changed')
    demand(all(r.get('default') is False and r['gameCatalogueAdmission'] is False
               and r['recordingModeEligible'] is False and r['contentId'] == 'unknown'
               for r in new_catalogue['tracks'][BASE_RECORDINGS:]), 'New catalogue escalated policy')
    subprocess.run(['node', 'intake/update-root-metadata.mjs'], check=True)
    Path(ARCHIVE, 'assembly-review.json').write_bytes(encoded({**binding,
        'status': 'hosted-byte-verification-complete-independent-review-pending',
        'recordings': 12, 'publicRecordings': PUBLIC_RECORDINGS,
        'preservedExistingEntries': BASE_RECORDINGS,
        'memberCount': len(files), 'productionBytes': production_bytes, 'volumes': volumes,
        'remaining': ['Independent original-artifact and publication PR review', 'Public byte and playback verification',
                      'Full listening, musical fit, transitions and warning audibility', 'Game admission and defaults',
                      'Offline and physical-device qualification']}))
    subprocess.run(['node', 'verify.mjs'], check=True)
    print(json.dumps({'assembled': True, 'recordings': 12, 'volumes': volumes, 'binding': binding}, indent=2))


if __name__ == '__main__':
    main()
