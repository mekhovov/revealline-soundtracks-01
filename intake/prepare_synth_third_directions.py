"""Hosted-only entry point for the immutable four-recording third synth slate."""
import argparse
import hashlib
import html
import json
import os
from pathlib import Path
import re
from urllib.parse import unquote

from itch_audio import acquisition_source_files
from prepare import SOURCE_LIMIT, prepare, validate_manifest


MANIFEST = Path(__file__).with_name('synth-third-directions-audition-20260925.json')
MANIFEST_SHA256 = '07ac02efefcaece89ffef39d0e6afb3b22bfde476a6b8cf651c318e429c074aa'
WORKFLOW = '.github/workflows/synth-third-directions-intake.yml'
SOURCE_FILES = acquisition_source_files(
    'intake/prepare_synth_third_directions.py',
    WORKFLOW,
    'intake/synth-third-directions-audition-20260925.json',
    'intake/synth-third-directions-audition-20260925.md',
    'intake/test_synth_third_directions.py',
)


def validate_third_manifest(value):
    value = validate_manifest(value)
    if any(value.get(key) is not False
           for key in ('publicationApproval', 'gameCatalogueAdmission',
                       'defaultPlaylistAdmission', 'recordingModeAdmission',
                       'listeningApproval')):
        raise ValueError('Third synth-direction intake cannot grant any admission or approval')
    for row in value['tracks']:
        if (not re.fullmatch(r'[0-9a-f]{64}', row.get('expectedSourceSha256', ''))
                or type(row.get('expectedSourceBytes')) is not int
                or not 0 < row['expectedSourceBytes'] <= SOURCE_LIMIT
                or row.get('expectedSourceSuffix') not in ('.flac', '.mp3', '.ogg')):
            raise ValueError('Exact source identity pins are incomplete or invalid')
        terms = row.get('requiredSourceTerms')
        if (not isinstance(terms, list) or not 1 <= len(terms) <= 8
                or any(not isinstance(term, str) or not 1 <= len(term) <= 240
                       for term in terms)):
            raise ValueError('Required source evidence terms are invalid')
    return value


def checked_manifest(data):
    if len(data) > 64 * 1024 or hashlib.sha256(data).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Immutable third synth-direction source manifest changed; review a new batch')
    return validate_third_manifest(json.loads(data))


def validate_prepared_intake(manifest, output):
    """Bind the bytes actually decoded to the reviewed source and evidence pins."""
    try:
        receipt = json.loads((output / 'receipt.json').read_text())
        tracks = receipt['tracks']
        failures = receipt['failures']
    except (KeyError, OSError, TypeError, json.JSONDecodeError):
        raise ValueError('Prepared receipt is incomplete') from None
    rows = {row['id']: row for row in manifest['tracks']}
    if failures or [track.get('id') for track in tracks] != list(rows):
        raise ValueError('Prepared receipt does not contain exactly four successful source rows')
    for track in tracks:
        row = rows[track['id']]
        original = track.get('original', {})
        expected_original = ('originals/' + row['expectedSourceSha256']
                             + row['expectedSourceSuffix'])
        if (original.get('path') != expected_original
                or original.get('sha256') != row['expectedSourceSha256']
                or original.get('bytes') != row['expectedSourceBytes']
                or original.get('url') != row['download']
                or track.get('completeDecode') is not True):
            raise ValueError('Prepared recording differs from the reviewed exact source identity')
        original_path = output / expected_original
        try:
            original_bytes = original_path.read_bytes()
        except OSError:
            raise ValueError('Prepared native source is missing') from None
        if (len(original_bytes) != row['expectedSourceBytes']
                or hashlib.sha256(original_bytes).hexdigest() != row['expectedSourceSha256']):
            raise ValueError('Preserved native source bytes differ from the reviewed identity')

        snapshot = track.get('sourceSnapshot', {})
        snapshot_sha = snapshot.get('sha256', '')
        if (not re.fullmatch(r'[0-9a-f]{64}', snapshot_sha)
                or snapshot.get('path') != 'evidence/' + snapshot_sha + '.html'
                or snapshot.get('url') != row['source']):
            raise ValueError('Prepared rights snapshot identity is invalid')
        try:
            evidence = (output / snapshot['path']).read_bytes()
        except OSError:
            raise ValueError('Prepared rights snapshot is missing') from None
        if hashlib.sha256(evidence).hexdigest() != snapshot_sha:
            raise ValueError('Prepared rights snapshot bytes differ from its identity')
        normalized = unquote(html.unescape(evidence.decode('utf8')))
        if (row['licenseURL'].removeprefix('https://') not in normalized
                or any(term not in normalized for term in row['requiredSourceTerms'])):
            raise ValueError('Required attribution or rights evidence changed on creator page')

        delivery = track.get('delivery', {})
        delivery_sha = delivery.get('sha256', '')
        if (not re.fullmatch(r'[0-9a-f]{64}', delivery_sha)
                or delivery.get('path') != 'objects/' + delivery_sha + '.mp3'):
            raise ValueError('Prepared derivative identity is invalid')
        try:
            derivative = (output / delivery['path']).read_bytes()
        except OSError:
            raise ValueError('Prepared derivative is missing') from None
        if (len(derivative) != delivery.get('bytes')
                or hashlib.sha256(derivative).hexdigest() != delivery_sha):
            raise ValueError('Prepared derivative bytes differ from the receipt')


def run(output, game_root):
    source = MANIFEST.read_bytes()
    checked_manifest(source)
    if (os.environ.get('GITHUB_ACTIONS') != 'true'
            or os.environ.get('GITHUB_REPOSITORY') != 'mekhovov/revealline-soundtracks-01'
            or not re.fullmatch(r'[0-9a-f]{40}', os.environ.get('GITHUB_SHA', ''))
            or not re.fullmatch(r'[0-9a-f]{40}', os.environ.get('EVENT_HEAD_SHA', ''))
            or not os.environ.get('GITHUB_WORKFLOW_REF', '').startswith(
                'mekhovov/revealline-soundtracks-01/' + WORKFLOW + '@')):
        raise ValueError('Audio acquisition requires the distinct hosted third synth-direction workflow')
    if output.exists():
        raise ValueError('Choose a fresh output directory; never overwrite evidence')
    exact_sources_verified = False
    try:
        prepare(MANIFEST, output, game_root)
        validate_prepared_intake(checked_manifest(source), output)
        exact_sources_verified = True
    finally:
        if output.is_dir():
            (output / 'source-manifest.json').write_bytes(source)
            binding = {
                'format': 'revealline-synth-third-directions-intake-binding.v1',
                'sourceManifestSha256': MANIFEST_SHA256,
                'runnerRevision': os.environ['GITHUB_SHA'],
                'eventHeadRevision': os.environ['EVENT_HEAD_SHA'],
                'runnerRun': os.environ.get('GITHUB_RUN_ID'),
                'workflowRef': os.environ['GITHUB_WORKFLOW_REF'],
                'sourceFiles': {
                    name: hashlib.sha256(Path(name).read_bytes()).hexdigest()
                    for name in SOURCE_FILES
                },
                'publicationApproval': False,
                'gameCatalogueAdmission': False,
                'defaultPlaylistAdmission': False,
                'recordingModeAdmission': False,
                'listeningApproval': False,
                'exactSourcesVerified': exact_sources_verified,
            }
            (output / 'intake-binding.json').write_text(
                json.dumps(binding, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate source only; no network or audio')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--game-root', type=Path)
    args = parser.parse_args()
    if args.check:
        checked_manifest(MANIFEST.read_bytes())
        print('Exact third synth-direction source manifest verified; audio not acquired')
    elif args.output is None or args.game_root is None:
        parser.error('--output and --game-root are required for hosted acquisition')
    else:
        run(args.output, args.game_root)
