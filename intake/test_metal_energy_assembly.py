import copy
import json
import unittest
from unittest.mock import patch

import assemble_approved_directions as assembler
import assemble_metal_energy as subject
from prepare_metal_energy import MANIFEST


class MetalEnergyAssemblyTests(unittest.TestCase):
    def test_exact_artifact_source_runner_and_tree_proof(self):
        self.assertEqual(subject.CONFIG['RUN'], 36216590495)
        self.assertEqual(subject.CONFIG['ARTIFACT'], 10898061610)
        self.assertEqual(subject.CONFIG['ZIP_BYTES'], 126708651)
        self.assertEqual(
            subject.CONFIG['ZIP_SHA'],
            '6a30ea883646a016354cc7a5bb532ebab15260a1c34fc32fa72e64e224ef8d61',
        )
        self.assertEqual(subject.CONFIG['SOURCE_HEAD'],
                         '00266689d4ceca7758733bfd4bd79ce4918910f7')
        self.assertEqual(subject.CONFIG['RUNNER'],
                         '58ca17ed65a78247c72cd26cdf08388cf477d549')
        self.assertEqual(subject.CONFIG['TREE_PROOF'], subject.CONFIG['RUNNER'])
        self.assertEqual(subject.CONFIG['SOURCE_TREE'],
                         'c4659963a1bb7a929e6ed172ee72b2c0797b8dd5')

    def test_publication_configuration_keeps_all_admissions_pending(self):
        self.assertEqual(subject.CONFIG['BASE_RECORDINGS'], 140)
        self.assertEqual(subject.CONFIG['PUBLIC_RECORDINGS'], 148)
        self.assertEqual(subject.CONFIG['EXPECTED_TEST_COUNT'], 23)
        self.assertEqual(subject.CONFIG['EXPECTED_FAMILY_COUNTS'],
                         {'metal': 5, 'synth90s': 3})
        self.assertEqual(subject.CONFIG['BINDING_FORMAT'],
                         'revealline-metal-energy-intake-binding.v1')

    def test_original_runner_merge_proves_the_exact_source_tree(self):
        saved = {name: getattr(assembler, name) for name in subject.CONFIG}
        saved.update({
            'MANIFEST_SHA256': assembler.MANIFEST_SHA256,
            'checked_manifest': assembler.checked_manifest,
            'UPLOAD_PINS': assembler.UPLOAD_PINS,
            'DESCRIPTION_HASHES': assembler.DESCRIPTION_HASHES,
        })
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

    def test_exact_rows_project_to_structured_rights(self):
        rows = json.loads(MANIFEST.read_bytes())['tracks']
        self.assertEqual(len(rows), 8)
        for row in rows:
            row['sourceSnapshot'] = {'url': row['source']}
            rights = assembler.structured_rights(row)
            self.assertEqual(rights['rightsEvidenceURL'], row['source'])
            self.assertEqual(rights['attribution'], row['credit'])
            self.assertEqual(rights['derivativeChangeNotice'], row['changes'])
            self.assertFalse(rights['shareAlike']['required'])

    def test_page_falls_back_to_creator_source_and_reports_registered_content_id(self):
        row = json.loads(MANIFEST.read_bytes())['tracks'][1]
        track = {**row, 'durationSeconds': 145, 'originalFilename': 'nox.wav',
                 'sha256': 'a' * 64, 'path': 'objects/' + 'a' * 64 + '.mp3'}
        track.pop('artistURL')
        body = assembler.page('Fixture', [track], 'other-batch').decode()
        self.assertIn(f'href="{row["source"]}"', body)
        self.assertIn('registered Content ID', body)
        self.assertIn('No game admission or default selection.', body)

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
