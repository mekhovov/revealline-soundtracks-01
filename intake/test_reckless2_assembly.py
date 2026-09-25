import copy
import json
import unittest
from unittest.mock import patch

import assemble_approved_directions as assembler
import assemble_reckless2 as subject
from prepare_reckless2 import MANIFEST


class Reckless2AssemblyConfigurationTests(unittest.TestCase):
    def test_exact_artifact_source_runner_and_tree_proof(self):
        self.assertEqual(subject.CONFIG['RUN'], 36193952191)
        self.assertEqual(subject.CONFIG['ARTIFACT'], 10889860079)
        self.assertEqual(subject.CONFIG['ZIP_BYTES'], 20781317)
        self.assertEqual(
            subject.CONFIG['ZIP_SHA'],
            '00211751f1701748948ca922c589120ad15db47b512b7bab15ca691a082bbc72',
        )
        self.assertEqual(subject.CONFIG['SOURCE_HEAD'],
                         'fec06dd45eacea56d00acbd470a43999b2f22710')
        self.assertEqual(subject.CONFIG['RUNNER'],
                         '2d2bbda086833d2b142dddbfa5668639683ddc1f')
        self.assertEqual(subject.CONFIG['TREE_PROOF'], subject.CONFIG['RUNNER'])
        self.assertEqual(subject.CONFIG['SOURCE_TREE'],
                         '704ac13c13b3c408bf5bc7ecc87df6d9827aa878')
        self.assertEqual(subject.CONFIG['SOURCE_BASE'],
                         '824e34e4957ab29b7ef841115f631a579f741fc4')
        self.assertEqual(subject.CONFIG['MERGED_SOURCE'],
                         '4f9ac1c1179d768bb851b63dd8cee6a604897fc5')

    def test_publication_configuration_is_distinct_and_pending(self):
        self.assertEqual(subject.CONFIG['BASE_RECORDINGS'], 136)
        self.assertEqual(subject.CONFIG['PUBLIC_RECORDINGS'], 140)
        self.assertEqual(subject.CONFIG['EXPECTED_TEST_COUNT'], 146)
        self.assertEqual(subject.CONFIG['EXPECTED_FAMILY_COUNTS'], {'metal': 4})
        self.assertEqual(subject.CONFIG['ARTIFACT_NAME'],
                         'reckless2-audition-candidates')
        self.assertEqual(subject.CONFIG['WORKFLOW_PATH'],
                         '.github/workflows/metal-reckless2-intake.yml')
        self.assertEqual(subject.CONFIG['BINDING_FORMAT'],
                         'revealline-reckless2-intake-binding.v1')
        self.assertEqual(subject.CONFIG['ARCHIVE'],
                         'intake/archive/metal-reckless2-audition-20260925')
        self.assertEqual(subject.CONFIG['BATCH_IDS'], {
            'metal': 'metal-reckless2-audition-20260925'
        })

    def test_original_runner_merge_proves_the_exact_source_tree(self):
        saved = {name: getattr(assembler, name) for name in subject.CONFIG}
        try:
            subject.configure()
            metadata = {
                'id': assembler.ARTIFACT,
                'size_in_bytes': assembler.ZIP_BYTES,
                'digest': 'sha256:' + assembler.ZIP_SHA,
                'expired': False,
                'name': assembler.ARTIFACT_NAME,
                'workflow_run': {'head_sha': assembler.SOURCE_HEAD, 'id': assembler.RUN},
            }
            run = {
                'id': assembler.RUN,
                'head_sha': assembler.SOURCE_HEAD,
                'conclusion': 'success',
                'event': 'pull_request',
                'path': assembler.WORKFLOW_PATH,
            }
            source = {'sha': assembler.SOURCE_HEAD,
                      'tree': {'sha': assembler.SOURCE_TREE}}
            tree_proof = {
                'sha': assembler.TREE_PROOF,
                'tree': {'sha': assembler.SOURCE_TREE},
                'parents': [{'sha': assembler.SOURCE_BASE},
                            {'sha': assembler.SOURCE_HEAD}],
            }
            assembler.validate_remote(metadata, run, source, tree_proof)
            changed = copy.deepcopy(tree_proof)
            changed['parents'].reverse()
            with self.assertRaisesRegex(ValueError, 'runner tree binding'):
                assembler.validate_remote(metadata, run, source, changed)
        finally:
            for name, value in saved.items():
                setattr(assembler, name, value)

    def test_exact_manifest_rows_project_to_non_sharealike_rights(self):
        rows = json.loads(MANIFEST.read_bytes())['tracks']
        self.assertEqual(len(rows), 4)
        for row in rows:
            row['sourceSnapshot'] = {'url': row['source']}
            row['changes'] = (
                'Converted from the exact native OGG Vorbis recording to 256 kbps '
                'stereo MP3 at 44.1 kHz with two-pass loudness normalization; '
                'native OGG retained unchanged.'
            )
            rights = assembler.structured_rights(row)
            self.assertEqual(rights, {
                'licenseId': 'CC-BY',
                'licenseVersion': '4.0',
                'licenseURL': row['licenseURL'],
                'rightsEvidenceURL': row['source'],
                'attribution': row['credit'],
                'derivativeChangeNotice': row['changes'],
                'shareAlike': {
                    'required': False,
                    'deliveryLicenseId': None,
                    'deliveryLicenseVersion': None,
                    'deliveryLicenseURL': None,
                },
            })

    def test_main_applies_configuration_before_guarded_assembly(self):
        saved = {name: getattr(assembler, name) for name in subject.CONFIG}
        saved.update({
            'MANIFEST_SHA256': assembler.MANIFEST_SHA256,
            'checked_manifest': assembler.checked_manifest,
            'UPLOAD_PINS': assembler.UPLOAD_PINS,
            'DESCRIPTION_HASHES': assembler.DESCRIPTION_HASHES,
        })
        try:
            with patch.object(assembler, 'main') as run:
                subject.main()
                run.assert_called_once_with()
                for name, value in subject.CONFIG.items():
                    self.assertEqual(getattr(assembler, name), value)
        finally:
            for name, value in saved.items():
                setattr(assembler, name, value)


if __name__ == '__main__':
    unittest.main()
