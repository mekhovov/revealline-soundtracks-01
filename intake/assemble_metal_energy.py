"""Publish the exact reviewed metal-energy artifact without regenerating audio."""

import assemble_approved_directions as assembler
from prepare_metal_energy import MANIFEST_SHA256, checked_manifest


CONFIG = {
    'BRANCH': 'codex/metal-energy-publication-20260926',
    'RUN': 36216590495,
    'ARTIFACT': 10898061610,
    'ZIP_BYTES': 126708651,
    'ZIP_SHA': '6a30ea883646a016354cc7a5bb532ebab15260a1c34fc32fa72e64e224ef8d61',
    'SOURCE_HEAD': '00266689d4ceca7758733bfd4bd79ce4918910f7',
    'RUNNER': '58ca17ed65a78247c72cd26cdf08388cf477d549',
    'TREE_PROOF': '58ca17ed65a78247c72cd26cdf08388cf477d549',
    'SOURCE_TREE': 'c4659963a1bb7a929e6ed172ee72b2c0797b8dd5',
    'SOURCE_BASE': 'cc7777bb62981ea9739a8efbc67f658f16f49a3f',
    'MERGED_SOURCE': 'ab9b5f36e3e5f0c3ec140edae20ed0a0d7e32f8f',
    'ARCHIVE': 'intake/archive/metal-energy-audition-20260926',
    'BATCH_IDS': {
        'metal': 'metal-energy-audition-20260926',
        'synth90s': 'synth-action-audition-20260926',
    },
    'TITLES': {
        'metal': 'High-energy metal auditions',
        'synth90s': 'Action synth and electro auditions',
    },
    'TEMPLATE': 'batches/metal-purgatory3-audition-20260925',
    'RELATED_BATCH': None,
    'TESTS_FILE': 'metal-energy-tests.txt',
    'EXPECTED_TEST_COUNT': 23,
    'ARTIFACT_NAME': 'metal-energy-candidates-20260926',
    'WORKFLOW_PATH': '.github/workflows/metal-energy-intake.yml',
    'BINDING_FORMAT': 'revealline-metal-energy-intake-binding.v1',
    'SOURCE_FILES': (
        'intake/approved_directions_pins.py',
        'intake/second_directions_pins.py',
        'intake/purgatory3_pins.py',
        'intake/reckless2_pins.py',
        'intake/itch_source.py',
        'intake/itch_audio.py',
        'intake/prepare.py',
        'intake/metal-energy-20260926.json',
        'intake/metal-energy-20260926.md',
        'intake/test_prepare.py',
        'intake/test_metal_energy.py',
        'intake/prepare_metal_energy.py',
        '.github/workflows/metal-energy-intake.yml',
    ),
    'BASE_RECORDINGS': 140,
    'PUBLIC_RECORDINGS': 148,
    'EXPECTED_FAMILY_COUNTS': {'metal': 5, 'synth90s': 3},
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
