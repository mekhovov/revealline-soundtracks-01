"""Publish the exact reviewed second-direction artifact without regenerating audio."""

import assemble_approved_directions as assembler
from prepare_second_directions import MANIFEST_SHA256, checked_manifest
from second_directions_pins import DESCRIPTION_HASHES, UPLOAD_PINS


CONFIG = {
    'BRANCH': 'codex/second-directions-publication',
    'RUN': 36072262687,
    'ARTIFACT': 10838153770,
    'ZIP_BYTES': 140918961,
    'ZIP_SHA': '8f2dccf2de56f3ade27038def3e5395777cd3cee37c6580ce68439ac2eb7cc25',
    'SOURCE_HEAD': '39b09d5269f0fa9a32786fdb705eb8e69a5cf33f',
    'RUNNER': 'b3b435fa6ac788494d80b9af81d862fbb1ddd0f1',
    'TREE_PROOF': 'b3b435fa6ac788494d80b9af81d862fbb1ddd0f1',
    'SOURCE_TREE': 'fae86c78144ca2bd1f959deee312b045be5672fb',
    'SOURCE_BASE': '5c3f3d798c64ddaa3677bd0ecafec4ee7a4a7221',
    'MERGED_SOURCE': '6a1a3c42761b25c3f87121a70a6b17959088e9f4',
    'ARCHIVE': 'intake/archive/second-directions-audition-20260925',
    'BATCH_IDS': {
        'synth90s': 'synth-second-directions-audition-20260925',
        'metal': 'metal-second-directions-audition-20260925',
    },
    'TITLES': {
        'synth90s': 'Electric Pulse synthwave auditions',
        'metal': 'Interstellar and Purgatory metal auditions',
    },
    'TEMPLATE': 'batches/synth-approved-directions-audition-20260925',
    'TESTS_FILE': 'second-directions-tests.txt',
    'EXPECTED_TEST_COUNT': 104,
    'ARTIFACT_NAME': 'second-directions-audition-candidates',
    'WORKFLOW_PATH': '.github/workflows/second-directions-intake.yml',
    'BINDING_FORMAT': 'revealline-second-directions-intake-binding.v1',
    'SOURCE_FILES': (
        'intake/second_directions_pins.py',
        'intake/approved_directions_pins.py',
        'intake/itch_source.py',
        'intake/itch_audio.py',
        'intake/prepare.py',
        'intake/prepare_second_directions.py',
        '.github/workflows/second-directions-intake.yml',
    ),
    'BASE_RECORDINGS': 116,
    'PUBLIC_RECORDINGS': 128,
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
