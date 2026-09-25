"""Publish the exact reviewed third synth-direction artifact without regenerating audio."""

import assemble_approved_directions as assembler
from prepare_synth_third_directions import MANIFEST_SHA256, checked_manifest


CONFIG = {
    'BRANCH': 'codex/third-directions-publication-20260925',
    'RUN': 36082136561,
    'ARTIFACT': 10843185196,
    'ZIP_BYTES': 62234070,
    'ZIP_SHA': 'fdcf01c091d53b7349d873569cb4fe4ba1e365432f52fd51f98938feb6d96ecc',
    'SOURCE_HEAD': '400367c644cafeae6e8ce94011cbb790561455f6',
    'RUNNER': 'e774748eace8567fbeda3d8c8e31245a29dfbb9b',
    'TREE_PROOF': 'd674bd24db64dd20925148945158b265e8526f07',
    'SOURCE_TREE': '97bebf63ab89a3718ec172614ad5d3561e18d1d0',
    'SOURCE_BASE': '275525e791d7f135e581f56c22100eb1bca16804',
    'MERGED_SOURCE': 'd674bd24db64dd20925148945158b265e8526f07',
    'ARCHIVE': 'intake/archive/synth-third-directions-audition-20260925',
    'BATCH_IDS': {'synth90s': 'synth-third-directions-audition-20260925'},
    'TITLES': {'synth90s': '90s racer and neon synth auditions'},
    'TEMPLATE': 'batches/synth-second-directions-audition-20260925',
    'RELATED_BATCH': 'synth-second-directions-audition-20260925',
    'TESTS_FILE': 'synth-third-directions-tests.txt',
    'EXPECTED_TEST_COUNT': 116,
    'ARTIFACT_NAME': 'synth-third-directions-audition-candidates',
    'WORKFLOW_PATH': '.github/workflows/synth-third-directions-intake.yml',
    'BINDING_FORMAT': 'revealline-synth-third-directions-intake-binding.v1',
    'SOURCE_FILES': (
        'intake/prepare.py',
        'intake/prepare_synth_third_directions.py',
        'intake/synth-third-directions-audition-20260925.json',
        'intake/synth-third-directions-audition-20260925.md',
        'intake/test_synth_third_directions.py',
        '.github/workflows/synth-third-directions-intake.yml',
    ),
    'BASE_RECORDINGS': 128,
    'PUBLIC_RECORDINGS': 132,
    'EXPECTED_FAMILY_COUNTS': {'synth90s': 4},
}


def configure():
    for name, value in CONFIG.items():
        setattr(assembler, name, value)
    assembler.MANIFEST_SHA256 = MANIFEST_SHA256
    assembler.checked_manifest = checked_manifest
    assembler.UPLOAD_PINS = {}
    assembler.DESCRIPTION_HASHES = {}


def main():
    configure()
    assembler.main()


if __name__ == '__main__':
    main()
