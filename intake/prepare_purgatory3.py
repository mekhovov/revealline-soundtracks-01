"""Hosted-only entry point for the immutable four-recording Purgatory 3 audition."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re

from itch_audio import acquisition_source_files
from prepare import prepare, validate_manifest


MANIFEST = Path(__file__).with_name('purgatory3-audition-20260925.json')
MANIFEST_SHA256 = '35dd9fb823d926d6ac4489037e99fcc0ebb4de1802d9fdf8096c929d5289ef5e'
WORKFLOW = '.github/workflows/metal-purgatory3-intake.yml'
SOURCE_FILES = acquisition_source_files(
    'intake/prepare_purgatory3.py', WORKFLOW)


def checked_manifest(data):
    if len(data) > 64 * 1024 or hashlib.sha256(data).hexdigest() != MANIFEST_SHA256:
        raise ValueError('Immutable Purgatory 3 source manifest changed; review a new batch')
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
        raise ValueError('Audio acquisition requires the distinct hosted Purgatory 3 workflow')
    if output.exists():
        raise ValueError('Choose a fresh output directory; never overwrite evidence')
    try:
        prepare(MANIFEST, output, game_root)
    finally:
        if output.is_dir():
            (output / 'source-manifest.json').write_bytes(source)
            binding = {
                'format': 'revealline-purgatory3-intake-binding.v1',
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
        print('Exact four-recording Purgatory 3 source manifest verified; audio not acquired')
    elif args.output is None or args.game_root is None:
        parser.error('--output and --game-root are required for hosted acquisition')
    else:
        run(args.output, args.game_root)
