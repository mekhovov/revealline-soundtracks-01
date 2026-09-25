import copy
import json
import unittest
from unittest.mock import patch

import assemble_approved_directions as assembler
import assemble_purgatory3 as subject
from prepare_purgatory3 import MANIFEST


class Purgatory3AssemblyConfigurationTests(unittest.TestCase):
    def test_exact_artifact_source_runner_and_tree_proof(self):
        self.assertEqual(subject.CONFIG['RUN'], 36083745177)
        self.assertEqual(subject.CONFIG['ARTIFACT'], 10842748733)
        self.assertEqual(subject.CONFIG['ZIP_BYTES'], 26388690)
        self.assertEqual(
            subject.CONFIG['ZIP_SHA'],
            'a77ea696226ebdf7a873c4ca58e77dc00d9eb4802847d4d57bc14d431ded8207',
        )
        self.assertEqual(subject.CONFIG['SOURCE_HEAD'],
                         '60f1a1d07d8aab6d6ebd4e152174f5326b7b9c37')
        self.assertEqual(subject.CONFIG['RUNNER'],
                         'eb3115cc62d0d7c883fb01ebd1c9e141ee294ab3')
        self.assertEqual(subject.CONFIG['TREE_PROOF'], subject.CONFIG['RUNNER'])
        self.assertEqual(subject.CONFIG['SOURCE_TREE'],
                         'de8c812ffbc2152a98cd00c49fbd3329ad9ec689')

    def test_publication_configuration_keeps_all_admissions_pending(self):
        self.assertEqual(subject.CONFIG['BASE_RECORDINGS'], 132)
        self.assertEqual(subject.CONFIG['PUBLIC_RECORDINGS'], 136)
        self.assertEqual(subject.CONFIG['EXPECTED_TEST_COUNT'], 117)
        self.assertEqual(subject.CONFIG['EXPECTED_FAMILY_COUNTS'], {'metal': 4})
        self.assertEqual(subject.CONFIG['ARTIFACT_NAME'],
                         'purgatory3-metal-audition-candidates')
        self.assertEqual(subject.CONFIG['WORKFLOW_PATH'],
                         '.github/workflows/metal-purgatory3-intake.yml')
        self.assertEqual(subject.CONFIG['BINDING_FORMAT'],
                         'revealline-purgatory3-intake-binding.v1')

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
