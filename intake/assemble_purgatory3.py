"""Publish the exact reviewed Purgatory 3 artifact without regenerating audio."""

import assemble_approved_directions as assembler
from prepare_purgatory3 import MANIFEST_SHA256, checked_manifest
from purgatory3_pins import DESCRIPTION_HASHES, UPLOAD_PINS


CONFIG = {
    'BRANCH': 'codex/purgatory3-publication-20260925',
    'RUN': 36083745177,
    'ARTIFACT': 10842748733,
    'ZIP_BYTES': 26388690,
    'ZIP_SHA': 'a77ea696226ebdf7a873c4ca58e77dc00d9eb4802847d4d57bc14d431ded8207',
    'SOURCE_HEAD': '60f1a1d07d8aab6d6ebd4e152174f5326b7b9c37',
    'RUNNER': 'eb3115cc62d0d7c883fb01ebd1c9e141ee294ab3',
    'TREE_PROOF': 'eb3115cc62d0d7c883fb01ebd1c9e141ee294ab3',
    'SOURCE_TREE': 'de8c812ffbc2152a98cd00c49fbd3329ad9ec689',
    'SOURCE_BASE': '275525e791d7f135e581f56c22100eb1bca16804',
    'MERGED_SOURCE': '41ea4448cf9602960ada28cd2c7c9a4cd5cb6b38',
    'ARCHIVE': 'intake/archive/metal-purgatory3-audition-20260925',
    'BATCH_IDS': {'metal': 'metal-purgatory3-audition-20260925'},
    'TITLES': {'metal': 'Purgatory vol. 3 extreme metal auditions'},
    'TEMPLATE': 'batches/metal-second-directions-audition-20260925',
    'RELATED_BATCH': 'metal-second-directions-audition-20260925',
    'TESTS_FILE': 'purgatory3-tests.txt',
    'EXPECTED_TEST_COUNT': 117,
    'ARTIFACT_NAME': 'purgatory3-metal-audition-candidates',
    'WORKFLOW_PATH': '.github/workflows/metal-purgatory3-intake.yml',
    'BINDING_FORMAT': 'revealline-purgatory3-intake-binding.v1',
    'SOURCE_FILES': (
        'intake/purgatory3_pins.py',
        'intake/approved_directions_pins.py',
        'intake/second_directions_pins.py',
        'intake/itch_source.py',
        'intake/itch_audio.py',
        'intake/prepare.py',
        'intake/prepare_purgatory3.py',
        '.github/workflows/metal-purgatory3-intake.yml',
    ),
    'BASE_RECORDINGS': 132,
    'PUBLIC_RECORDINGS': 136,
    'EXPECTED_FAMILY_COUNTS': {'metal': 4},
}


def configure():
    for name, value in CONFIG.items():
        setattr(assembler, name, value)
    assembler.MANIFEST_SHA256 = MANIFEST_SHA256
    assembler.checked_manifest = checked_manifest
    assembler.UPLOAD_PINS = UPLOAD_PINS
    assembler.DESCRIPTION_HASHES = DESCRIPTION_HASHES


def main():
    configure()
    assembler.main()


if __name__ == '__main__':
    main()
