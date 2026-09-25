"""Publish the exact reviewed Reckless 2 artifact without regenerating audio."""

import assemble_approved_directions as assembler
from prepare_reckless2 import MANIFEST_SHA256, checked_manifest
from reckless2_pins import DESCRIPTION_HASHES, UPLOAD_PINS


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
