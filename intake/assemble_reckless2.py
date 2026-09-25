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
BASE_AUDIO_BYTES = 777523163
PUBLIC_AUDIO_BYTES = 790408183
DELIVERY_SHA256 = {
    'davidkbd.city-limits-crash':
        '7cc21044e1c8b23b9e71af8bf5a9d143ca8de8b6e8898fe930bc78811493a442',
    'davidkbd.edge-of-the-city':
        'c676190104dae2fc8467957652f2ffe905100ee25451217258e04752e82e9be0',
    'davidkbd.defiant-descent':
        '24ce6e0fb25aa6aabede7a2277fa8eb0add1e46c9c74c725b0192e5f63d01899',
    'davidkbd.airborne-anarchy':
        '4674a3f4b27f7222cd4a0f0bd9aea13c83d5c90fa2b0a168d6ef71bc874a471d',
}


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


def merged_catalogue_bytes():
    return subprocess.check_output([
        'git', 'show', f"{CONFIG['MERGED_SOURCE']}:catalogue.json"
    ])


def checked_baseline(body):
    assembler.demand(
        hashlib.sha256(body).hexdigest() == BASE_CATALOGUE_SHA256,
        'Accepted 136-recording catalogue bytes changed',
    )
    catalogue = json.loads(body)
    assembler.demand(
        catalogue.get('counts') == {
            'declaredTracks': CONFIG['BASE_RECORDINGS'],
            'uniqueRecordings': CONFIG['BASE_RECORDINGS'],
            'duplicateAliases': 0,
            'audioBytes': BASE_AUDIO_BYTES,
        }
        and len(catalogue.get('tracks', ())) == CONFIG['BASE_RECORDINGS'],
        'Accepted catalogue count changed',
    )
    return catalogue


def normalize_title(title):
    return ''.join(character for character in title.lower()
                   if character.isascii() and character.isalnum())


def validate_no_preexisting_candidates(baseline):
    existing = {normalize_title(row.get('title', '')) for row in baseline['tracks']}
    candidates = {normalize_title(values[3]) for values in UPLOAD_PINS.values()}
    assembler.demand(not existing.intersection(candidates),
                     'Reckless title already exists in accepted baseline')


def validate_catalogue_context(body, baseline_body=None):
    baseline_body = merged_catalogue_bytes() if baseline_body is None else baseline_body
    baseline = checked_baseline(baseline_body)
    validate_no_preexisting_candidates(baseline)
    if body == baseline_body:
        return 'base'
    current = json.loads(body)
    counts = current.get('counts', {})
    assembler.demand(
        counts.get('declaredTracks') == CONFIG['PUBLIC_RECORDINGS']
        and counts.get('uniqueRecordings') == CONFIG['PUBLIC_RECORDINGS']
        and counts.get('duplicateAliases') == 0
        and counts.get('audioBytes') == PUBLIC_AUDIO_BYTES
        and len(current.get('tracks', ())) == CONFIG['PUBLIC_RECORDINGS']
        and current['tracks'][:CONFIG['BASE_RECORDINGS']] == baseline['tracks'],
        'Generated catalogue does not preserve the exact accepted baseline',
    )
    added = current['tracks'][CONFIG['BASE_RECORDINGS']:]
    assembler.demand(
        [(row.get('id'), row.get('title'), row.get('audio', {}).get('sha256'))
         for row in added]
        == [(track_id, UPLOAD_PINS[track_id][3], sha256)
            for track_id, sha256 in DELIVERY_SHA256.items()]
        and all(
            row.get('listeningApproval') == 'not-reviewed'
            and row.get('gameCatalogueAdmission') is False
            and row.get('default') is False
            and row.get('recordingModeEligible') is False
            and row.get('contentId') == 'unknown'
            for row in added
        ),
        'Generated catalogue contains another recording or escalated policy',
    )
    return 'generated'


def validate_baseline():
    baseline_body = merged_catalogue_bytes()
    checked_baseline(baseline_body)
    assembler.demand(
        Path('catalogue.json').read_bytes() == baseline_body,
        'Publication checkout does not start from the exact accepted catalogue',
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
