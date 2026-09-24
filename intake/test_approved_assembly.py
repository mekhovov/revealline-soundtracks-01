import copy
import io
import json
import unittest
import zipfile
from unittest.mock import patch

import assemble_approved_directions as subject
from prepare_approved_directions import MANIFEST
from approved_directions_pins import UPLOAD_PINS, DESCRIPTION_HASHES


def fixture():
    """Synthetic metadata and tiny stub bytes only; never acquire real audio."""
    manifest = json.loads(MANIFEST.read_bytes())
    source_files = {'fixture.py': 'a' * 64}
    files = {
        subject.PREFIX + 'source-manifest.json': MANIFEST.read_bytes(),
        'approved-directions-tests.txt': b'Ran 81 tests in 0.134s\n\nOK\n',
        subject.PREFIX + 'intake-binding.json': subject.encoded({
            'format': 'revealline-approved-directions-intake-binding.v1',
            'sourceManifestSha256': subject.MANIFEST_SHA256, 'runnerRevision': subject.RUNNER,
            'eventHeadRevision': subject.SOURCE_HEAD, 'runnerRun': str(subject.RUN),
            'sourceFiles': source_files, 'publicationApproval': False,
            'gameCatalogueAdmission': False, 'listeningApproval': False}),
    }
    rows = []
    for source in manifest['tracks']:
        row = copy.deepcopy(source)
        for name, directory in (('original', 'originals'), ('delivery', 'objects')):
            body = (name + ':' + row['id']).encode()
            suffix = 'ogg' if name == 'original' and source.get('uploadId') else 'mp3'
            relative = directory + '/' + subject.digest(body) + '.' + suffix
            files[subject.PREFIX + relative] = body
            row[name] = subject.pin(relative, body)
        if source.get('uploadId'):
            observed = {k: source[k] for k in
                        ('id', 'title', 'source', 'gameId', 'uploadId', 'uploadName', 'license', 'licenseURL')}
            observed.update({'audioAcquired': True, 'listeningApproval': False, 'admitted': False,
                             'native': row['original'], 'licenseObservation': {
                                 'reviewedDescriptionSha256': DESCRIPTION_HASHES[UPLOAD_PINS[source['id']][0]],
                                 'observedDirectLicenseLink': source['licenseURL']}})
            evidence = subject.encoded(observed)
            suffix = '.json'
        else:
            evidence = (f'<a href="{source["download"]}">Source</a>'
                        f'<a href="{source["licenseURL"]}">License</a>').encode()
            suffix = '.html'
        relative = 'evidence/' + subject.digest(evidence) + suffix
        files[subject.PREFIX + relative] = evidence
        row['sourceSnapshot'] = {'path': relative, 'sha256': subject.digest(evidence), 'url': source['source']}
        row.update({'durationSeconds': 200, 'completeDecode': True, 'listeningApproval': False,
                    'encodedLoudness': {'input_i': '-16', 'input_tp': '-2'},
                    'changes': 'Synthetic fixture conversion; not real audio.'})
        rows.append(row)
    receipt = {'format': 'revealline-core-intake-receipt.v1',
               'sourceManifestSha256': subject.MANIFEST_SHA256, 'runnerRevision': subject.RUNNER,
               'runnerRun': str(subject.RUN), 'failures': [], 'listeningApproval': False,
               'gameInspector': {'revision': subject.INSPECTOR_REVISION, 'files': [
                   {'path': p, 'sha256': sha} for p, sha in subject.INSPECTOR_PINS.items()]},
               'tracks': rows, 'deliveryVolumes': subject.delivery_volumes(rows)}
    files[subject.PREFIX + 'receipt.json'] = subject.encoded(receipt)
    files[subject.PREFIX + 'review.json'] = subject.encoded({'status': 'pending', 'tracks': [
        {'id': r['id'], 'sha256': r['delivery']['sha256'], 'fullTrackListening': False,
         'transitions': False, 'warningAudibility': False} for r in rows]})
    return files, receipt, source_files


def zipped(files):
    output = io.BytesIO()
    with zipfile.ZipFile(output, 'w') as archive:
        for name, body in files.items():
            archive.writestr(name, body)
    return output.getvalue()


class ApprovedAssemblyTests(unittest.TestCase):
    def test_original_remote_artifact_run_and_runner_tree_are_all_exact(self):
        metadata = {'id': subject.ARTIFACT, 'size_in_bytes': subject.ZIP_BYTES,
                    'digest': 'sha256:' + subject.ZIP_SHA, 'expired': False,
                    'name': 'approved-directions-audition-candidates',
                    'workflow_run': {'head_sha': subject.SOURCE_HEAD, 'id': subject.RUN}}
        run = {'id': subject.RUN, 'head_sha': subject.SOURCE_HEAD, 'conclusion': 'success',
               'event': 'pull_request', 'path': '.github/workflows/approved-directions-intake.yml'}
        source = {'sha': subject.SOURCE_HEAD, 'tree': {'sha': subject.SOURCE_TREE}}
        runner = {'sha': subject.RUNNER, 'tree': {'sha': subject.SOURCE_TREE},
                  'parents': [{'sha': subject.SOURCE_BASE}, {'sha': subject.SOURCE_HEAD}]}
        subject.validate_remote(metadata, run, source, runner)
        for index, key, value in ((0, 'id', 1), (0, 'size_in_bytes', 1), (0, 'digest', 'other'),
                                  (0, 'expired', True), (0, 'workflow_run', {'id': 1}),
                                  (1, 'head_sha', 'f' * 40), (1, 'conclusion', 'failure'),
                                  (1, 'path', 'other.yml'), (2, 'tree', {'sha': 'f' * 40}),
                                  (3, 'parents', [{'sha': subject.SOURCE_HEAD}])):
            args = copy.deepcopy([metadata, run, source, runner])
            args[index][key] = value
            with self.subTest(index=index, key=key), self.assertRaises(ValueError):
                subject.validate_remote(*args)

    def test_full_fixture_validates_every_original_derivative_and_pending_row(self):
        files, receipt, source_files = fixture()
        self.assertEqual(subject.checked_receipt(files, source_files), receipt)
        data = zipped(files)
        with patch.multiple(subject, ZIP_BYTES=len(data), ZIP_SHA=subject.digest(data)):
            self.assertEqual(subject.checked_members(data), files)

    def test_original_artifact_digest_length_and_unsafe_members_fail_closed(self):
        files, _, _ = fixture()
        data = zipped(files)
        with self.assertRaisesRegex(ValueError, 'ZIP digest'):
            subject.checked_members(data)
        for name in ('../escape.mp3', '/absolute', 'candidate-output/objects/fake.mp3',
                     'candidate-output/extra.json'):
            broken = zipped({**files, name: b'Unexpected'})
            with patch.multiple(subject, ZIP_BYTES=len(broken), ZIP_SHA=subject.digest(broken)):
                with self.assertRaisesRegex(ValueError, 'artifact member'):
                    subject.checked_members(broken)

    def test_zip_duplicates_and_symlinks_are_rejected(self):
        files, _, _ = fixture()
        for symlink in (True, False):
            output = io.BytesIO()
            with zipfile.ZipFile(output, 'w') as archive:
                name, body = next(iter(files.items()))
                info = zipfile.ZipInfo(name)
                if symlink:
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                archive.writestr(info, body)
                if not symlink:
                    with self.assertWarns(UserWarning):
                        archive.writestr(name, body)
            data = output.getvalue()
            with patch.multiple(subject, ZIP_BYTES=len(data), ZIP_SHA=subject.digest(data)):
                with self.assertRaisesRegex(ValueError, 'artifact member'):
                    subject.checked_members(data)

    def test_missing_modified_and_unreferenced_bytes_do_not_assemble(self):
        files, receipt, source_files = fixture()
        native = subject.PREFIX + receipt['tracks'][0]['original']['path']
        for changed in (dict(files, **{native: b'modified'}),
                        {k: v for k, v in files.items() if k != native},
                        dict(files, **{'unreferenced.json': b'{}'})):
            with self.assertRaises((ValueError, KeyError)):
                subject.checked_receipt(changed, source_files)

    def test_status_identity_and_technical_claims_cannot_be_promoted(self):
        files, receipt, source_files = fixture()
        for key, value in [('title', 'Another recording'), ('recordingModeEligible', True),
                           ('contentId', False), ('fullTrackListening', True), ('completeDecode', False),
                           ('listeningApproval', True), ('durationSeconds', 10),
                           ('encodedLoudness', {'input_i': '-10', 'input_tp': '0'})]:
            changed = copy.deepcopy(receipt)
            changed['tracks'][0][key] = value
            altered = dict(files, **{subject.PREFIX + 'receipt.json': subject.encoded(changed)})
            with self.subTest(key=key), self.assertRaises(ValueError):
                subject.checked_receipt(altered, source_files)

    def test_source_hashes_runner_inspector_test_failure_and_review_remain_bound(self):
        files, receipt, source_files = fixture()
        for key, value in [('runnerRevision', 'f' * 40), ('failures', [{'error': 'failed'}]),
                           ('gameInspector', {'revision': 'other', 'files': []})]:
            changed = copy.deepcopy(receipt)
            changed[key] = value
            with self.assertRaises(ValueError):
                subject.checked_receipt(dict(files, **{subject.PREFIX + 'receipt.json': subject.encoded(changed)}), source_files)
        with self.assertRaises(ValueError):
            subject.checked_receipt(files, {'changed.py': 'b' * 64})
        with self.assertRaises(ValueError):
            subject.checked_receipt(dict(files, **{'approved-directions-tests.txt': b'Ran 81 tests\nFAILED\n'}), source_files)
        with self.assertRaises(ValueError):
            subject.checked_receipt(dict(files, **{subject.PREFIX + 'review.json': b'{"status":"approved"}'}), source_files)

    def test_batch_generation_is_reproducible_and_preserves_exact_delivery_bytes(self):
        files, receipt, _ = fixture()
        templates = {'player.mjs': b'// fixture player', 'style.css': b'/* fixture style */'}
        for family in subject.BATCH_IDS:
            rows = [r for r in receipt['tracks'] if r['family'] == family]
            first = subject.build_batch(family, rows, files, templates)
            self.assertEqual(first, subject.build_batch(family, rows, files, templates))
            for row in rows:
                self.assertEqual(first[row['delivery']['path']], files[subject.PREFIX + row['delivery']['path']])
            catalogue = json.loads(first['preview-catalogue.json'])
            self.assertFalse(catalogue['gameCatalogueAdmission'])
            self.assertEqual(catalogue['listeningApproval'], 'not-reviewed')
            self.assertEqual(len(catalogue['tracks']), 6)
            for row in catalogue['tracks']:
                self.assertFalse(row['default'])
                self.assertFalse(row['gameCatalogueAdmission'])
                self.assertFalse(row['recordingModeEligible'])
            self.assertEqual(first['player.mjs'], templates['player.mjs'])
            self.assertIn(b'id="search"', first['index.html'])
            self.assertIn(b'id="next"', first['index.html'])
            self.assertIn(b'aria-live="polite"', first['index.html'])
            self.assertLess(sum(map(len, first.values())), subject.MAX_VOLUME)

    def test_full_batch_size_includes_metadata_and_html_is_escaped(self):
        files, receipt, _ = fixture()
        rows = [r for r in receipt['tracks'] if r['family'] == 'metal']
        rows[0]['title'] = '<script>alert("x")</script>'
        page = subject.build_batch('metal', rows, files, {'player.mjs': b'x', 'style.css': b'y'})
        self.assertNotIn(b'<script>alert', page['index.html'])
        self.assertIn(b'&lt;script&gt;', page['index.html'])
        with patch.object(subject, 'MAX_VOLUME', 100):
            with self.assertRaisesRegex(ValueError, '64 MiB'):
                subject.build_batch('metal', rows, files, {'player.mjs': b'x', 'style.css': b'y'})

    def test_local_or_main_assembly_is_refused_before_any_io(self):
        with patch.dict('os.environ', {}, clear=True), patch.object(subject, 'api') as api:
            with self.assertRaisesRegex(ValueError, 'hosted publication branch'):
                subject.main()
            api.assert_not_called()


if __name__ == '__main__':
    unittest.main()
