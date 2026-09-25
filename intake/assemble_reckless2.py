"""Publish the exact reviewed Reckless 2 artifact without regenerating audio."""

import hashlib
import json
from pathlib import Path
import subprocess

import assemble_approved_directions as assembler
from prepare_reckless2 import MANIFEST_SHA256, checked_manifest
from reckless2_pins import DESCRIPTION_HASHES, UPLOAD_PINS


MERGED_SOURCE_TREE = '704ac13c13b3c408bf5bc7ecc87df6d9827aa878'
MERGED_SOURCE_PARENTS = (
    '824e34e4957ab29b7ef841115f631a579f741fc4',
    'fec06dd45eacea56d00acbd470a43999b2f22710',
)
BASE_CATALOGUE_SHA256 = (
    '946180064d4f3570f6d365e1e005e5e846ea2cc3142d7e4b65bde4b4a3c88199'
)


CONFIG = {
    'BRANCH': 'codex/reckless2-publication-20260926',
    'RUN': 36193952191,
    'ARTIFACT': 10889860079,
    'ZIP_BYTES': 20781317,
    'ZIP_SHA': '00211751f1701748948ca922c589120ad15db47b512b7bab15ca691a082bbc72',
    'SOURCE_HEAD': 'fec06dd45eacea56d00acbd470a43999b2f22710',
    'RUNNER': '2d2bbda086833d2b142dddbfa5668639683ddc1f',
    'TREE_PROOF': '2d2bbda086833d2b142dddbfa5668639683ddc1f',
    'SOURCE_TREE': '704ac13c13b3c408bf5bc7ecc87df6d9827aa878',
    'SOURCE_BASE': '824e34e4957ab29b7ef841115f631a579f741fc4',
    'MERGED_SOURCE': '4f9ac1c1179d768bb851b63dd8cee6a604897fc5',
    'ARCHIVE': 'intake/archive/metal-reckless2-audition-20260925',
    'BATCH_IDS': {'metal': 'metal-reckless2-audition-20260925'},
    'TITLES': {'metal': 'Reckless vol. 2 punk-metal auditions'},
    'TEMPLATE': 'batches/metal-purgatory3-audition-20260925',
    'RELATED_BATCH': 'metal-purgatory3-audition-20260925',
    'TESTS_FILE': 'reckless2-tests.txt',
    'EXPECTED_TEST_COUNT': 146,
    'ARTIFACT_NAME': 'reckless2-audition-candidates',
    'WORKFLOW_PATH': '.github/workflows/metal-reckless2-intake.yml',
    'BINDING_FORMAT': 'revealline-reckless2-intake-binding.v1',
    'SOURCE_FILES': (
        'intake/approved_directions_pins.py',
        'intake/second_directions_pins.py',
        'intake/purgatory3_pins.py',
        'intake/reckless2_pins.py',
        'intake/itch_source.py',
        'intake/itch_audio.py',
        'intake/prepare.py',
        'intake/prepare_reckless2.py',
        '.github/workflows/metal-reckless2-intake.yml',
    ),
    'BASE_RECORDINGS': 136,
    'PUBLIC_RECORDINGS': 140,
    'EXPECTED_FAMILY_COUNTS': {'metal': 4},
}


def validate_merged_identity(commit):
    assembler.demand(
        commit.get('sha') == CONFIG['MERGED_SOURCE']
        and commit.get('tree', {}).get('sha') == MERGED_SOURCE_TREE
        and tuple(parent.get('sha') for parent in commit.get('parents', ()))
        == MERGED_SOURCE_PARENTS,
        'Merged source commit, tree or parents changed',
    )


def validate_publication_ancestry():
    endpoint = f"repos/{assembler.REPOSITORY}/git/commits/{CONFIG['MERGED_SOURCE']}"
    validate_merged_identity(assembler.api(endpoint))
    ancestry = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', CONFIG['MERGED_SOURCE'], 'HEAD'],
        check=False,
        capture_output=True,
    )
    assembler.demand(
        ancestry.returncode == 0,
        'Accepted merged source is not an ancestor of the publication checkout',
    )


def validate_baseline(data=None):
    body = Path('catalogue.json').read_bytes() if data is None else data
    assembler.demand(
        hashlib.sha256(body).hexdigest() == BASE_CATALOGUE_SHA256,
        'Accepted 136-recording catalogue bytes changed',
    )
    catalogue = json.loads(body)
    assembler.demand(
        catalogue.get('counts', {}).get('uniqueRecordings') == CONFIG['BASE_RECORDINGS']
        and len(catalogue.get('tracks', ())) == CONFIG['BASE_RECORDINGS'],
        'Accepted catalogue count changed',
    )


def configure():
    for name, value in CONFIG.items():
        setattr(assembler, name, value)
    assembler.MANIFEST_SHA256 = MANIFEST_SHA256
    assembler.checked_manifest = checked_manifest
    assembler.UPLOAD_PINS = UPLOAD_PINS
    assembler.DESCRIPTION_HASHES = DESCRIPTION_HASHES


def main():
    configure()
    validate_publication_ancestry()
    validate_baseline()
    assembler.main()


if __name__ == '__main__':
    main()
