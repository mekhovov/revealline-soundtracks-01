"""Hosted-only entry point for the immutable eight-recording energy audition."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from itch_audio import acquisition_source_files
from prepare import prepare, validate_manifest


MANIFEST = Path(__file__).with_name('metal-energy-20260926.json')
MANIFEST_SHA256 = 'f326621bafffa17f24a5f331749539da0331d1937b709c5cb5109793d619021e'
WORKFLOW = '.github/workflows/metal-energy-intake.yml'
SOURCE_FILES = acquisition_source_files(
    'intake/prepare_metal_energy.py',
    WORKFLOW,
    'intake/metal-energy-20260926.json',
    'intake/metal-energy-20260926.md',
    'intake/test_prepare.py',
    'intake/test_metal_energy.py',
)


def checked_manifest(data):
    if len(data) > 128 * 1024 or hashlib.sha256(data).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Immutable metal-energy source manifest changed; review a new batch')
    return validate_manifest(json.loads(data))


def run(output, game_root):
    source = MANIFEST.read_bytes()
    checked_manifest(source)
    if (
        os.environ.get('GITHUB_ACTIONS') != 'true'
        or os.environ.get('GITHUB_REPOSITORY') != 'mekhovov/revealline-soundtracks-01'
        or not re.fullmatch(r'[0-9a-f]{40}', os.environ.get('GITHUB_SHA', ''))
        or not re.fullmatch(r'[0-9a-f]{40}', os.environ.get('EVENT_HEAD_SHA', ''))
        or not os.environ.get('GITHUB_WORKFLOW_REF', '').startswith(
            'mekhovov/revealline-soundtracks-01/' + WORKFLOW + '@'
        )
    ):
        raise ValueError('Audio acquisition requires the distinct hosted metal-energy workflow')
    if output.exists():
        raise ValueError('Choose a fresh output directory; never overwrite evidence')
    try:
        prepare(MANIFEST, output, game_root)
    finally:
        if output.is_dir():
            (output / 'source-manifest.json').write_bytes(source)
            binding = {
                'format': 'revealline-metal-energy-intake-binding.v1',
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
                'listeningApproval': False,
            }
            (output / 'intake-binding.json').write_text(json.dumps(binding, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true', help='Validate source only; no network or audio')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--game-root', type=Path)
    args = parser.parse_args()
    if args.check:
        checked_manifest(MANIFEST.read_bytes())
        print('Exact eight-recording metal-energy source manifest verified; audio not acquired')
    elif args.output is None or args.game_root is None:
        parser.error('--output and --game-root are required for hosted acquisition')
    else:
        run(args.output, args.game_root)
