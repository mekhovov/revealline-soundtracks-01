import copy
from email.message import Message
from pathlib import Path
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
import itch_audio as subject
import prepare
from itch_source import LEGACY_TRACK_IDS
from test_itch_source import FixtureClient


def row(track_id='dos88.race-to-mars'):
    result = subject.identity(track_id)
    result['credit'] = subject.credit(result)
    return result


def headers(name='Race to Mars.mp3', media_type='audio/mpeg', size=None):
    result = Message()
    result['Content-Disposition'] = 'attachment; filename="' + name + '"'
    result['Content-Type'] = media_type
    if size is not None:
        result['Content-Length'] = str(size)
    return result


class Response(io.BytesIO):
    def __init__(self, resolution, body=b'native bytes', response_headers=None):
        super().__init__(body)
        self.status = 200
        self.url = resolution.download_url
        self.headers = response_headers or headers(size=len(body))
        self.requested_sizes = []

    def read(self, size=-1):
        self.requested_sizes.append(size)
        return super().read(size)


def media_fixture(track_id='dos88.race-to-mars', body=b'native bytes', response_headers=None):
    resolution = subject.resolve(track_id, FixtureClient(track_id))
    response = Response(resolution, body, response_headers)
    opener = Mock()
    opener.open.return_value = response
    return resolution, response, opener


class ItchAudioTests(unittest.TestCase):
    def test_exact_ten_identities_remain_pending_with_six_synth_and_four_metal(self):
        rows = [row(key) for key in sorted(LEGACY_TRACK_IDS)]
        manifest = {'format': 'revealline-core-intake.v1', 'tracks': rows}
        self.assertIs(prepare.validate_manifest(manifest), manifest)
        self.assertEqual([r['family'] for r in rows].count('synth90s'), 6)
        self.assertEqual([r['family'] for r in rows].count('metal'), 4)
        for item in rows:
            self.assertFalse(item['recordingModeEligible'])
            self.assertEqual(item['contentId'], 'unknown')
            self.assertNotIn('ukrainian', item.values())
            self.assertNotIn('download', item)

    def test_historical_itch_manifest_and_previous_creator_batch_are_preserved_exactly(self):
        root = Path(__file__).parent
        active = (root / 'archive/itch-core-audition-20260924/source-manifest.json').read_bytes()
        named = (root / 'itch-core-audition-20260924.json').read_bytes()
        self.assertEqual(active, named)
        self.assertEqual(subject.hashlib.sha256(active).hexdigest(),
                         '02a28c838d2f68b2a22ef29b6e432deebfe772e5f86bc1614b73839dceaa89f9')
        parsed = prepare.validate_manifest(json.loads(active))
        self.assertFalse(parsed['publicationApproval'])
        self.assertEqual({r['id'] for r in parsed['tracks']}, LEGACY_TRACK_IDS)
        previous = (root / 'archive/metal-nakarada-audition-20260924/source-manifest.json').read_bytes()
        self.assertEqual(subject.hashlib.sha256(previous).hexdigest(),
                         'c26eb3c1357beee40ea6ceac5001fb15651d5fb86d494722da1628e7bd65c1dd')
        self.assertEqual(len(prepare.validate_manifest(json.loads(previous))['tracks']), 2)
        historical = (root / 'archive/core-20260924/source-manifest.json').read_bytes()
        self.assertEqual(subject.hashlib.sha256(historical).hexdigest(),
                         '5b7ae6ea26ba85214959f3c9c63301ad8b30b5e96d2f6ae0ceb1b43c1d0961ca')

    def test_identity_license_approval_and_extra_token_fields_fail_closed(self):
        for field, value in [('title', 'Other song'), ('gameId', True), ('uploadId', 6033120),
                             ('uploadName', 'paid-archive.wav'), ('family', 'ukrainian'),
                             ('contentId', False), ('recordingModeEligible', True),
                             ('status', 'approved'), ('licenseURL', 'https://example.test'),
                             ('credit', 'no credit'), ('download', 'secret temporary URL'),
                             ('csrf_token', 'secret token')]:
            changed = row()
            changed[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                subject.validate_row(changed)

    def test_attachment_filename_exact_and_extended_forms(self):
        actual = subject.native_filename(headers(), 'Race to Mars.mp3')
        self.assertEqual(actual, ('Race to Mars.mp3', '.mp3', 'audio/mpeg'))
        h = headers()
        h.replace_header('Content-Disposition', "attachment; filename*=UTF-8''Race%20to%20Mars.mp3")
        self.assertEqual(subject.native_filename(h, 'Race to Mars.mp3')[0], 'Race to Mars.mp3')
        # escp's visible upload title has no extension; the exact free upload ID
        # binds identity and its safe native filename/format is retained verbatim.
        self.assertEqual(subject.native_filename(headers('Synthasia.flac', 'audio/flac'), 'Synthasia')[1], '.flac')

    def test_quoted_filename_comma_is_not_a_combined_header(self):
        name = 'Keep My Rhythm, If You Can.ogg'
        self.assertEqual(subject.native_filename(headers(name, 'audio/ogg'), name),
                         (name, '.ogg', 'audio/ogg'))

    def test_header_duplicates_combined_values_conflicts_and_unsafe_paths_rejected(self):
        invalid = [
            'inline; filename="Race to Mars.mp3"',
            'attachment; filename="Race to Mars.mp3", attachment; filename="other.mp3"',
            'attachment; filename="Race to Mars.mp3"; filename="other.mp3"',
            'attachment; filename="Race to Mars.mp3"; filename*=UTF-8\'\'Other.mp3',
            'attachment; filename="unterminated.mp3',
            'attachment; filename="dangling\\',
        ]
        invalid += ['attachment; filename="' + name + '"' for name in (
            '../song.mp3', '..\\song.mp3', '%2e%2e%2fsong.mp3', 'song∕other.mp3',
            'song／other.mp3', ' song.mp3', 'song.mp3 ', 'song.zip', 'song\x00.mp3')]
        for value in invalid:
            h = headers()
            h.replace_header('Content-Disposition', value)
            with self.subTest(disposition=value), self.assertRaises(ValueError):
                subject.native_filename(h, 'escp title')
        for key in ('Content-Disposition', 'Content-Type'):
            h = headers()
            h[key] = h[key]
            with self.subTest(duplicate=key), self.assertRaises(ValueError):
                subject.native_filename(h, 'Race to Mars.mp3')
        with self.assertRaises(ValueError):
            subject.native_filename(headers('Other.mp3'), 'Race to Mars.mp3')
        with self.assertRaises(ValueError):
            subject.native_filename(headers(media_type='text/html'), 'Race to Mars.mp3')

    def test_acquisition_is_bounded_and_receipt_has_no_temporary_credentials(self):
        item = row()
        fixture = FixtureClient(item['id'])
        client = subject.EvidenceClient(item['source'])
        client.client = fixture
        _, response, opener = media_fixture()
        body, receipt = subject.acquire(item, client, opener)
        self.assertEqual(body, b'native bytes')
        self.assertEqual(response.requested_sizes, [subject.SOURCE_LIMIT + 1])
        self.assertEqual(receipt['native']['fileName'], 'Race to Mars.mp3')
        self.assertEqual(len(receipt['licenseObservation']['pageSha256']), 64)
        self.assertTrue(receipt['audioAcquired'])
        self.assertFalse(receipt['listeningApproval'])
        self.assertFalse(receipt['admitted'])
        text = json.dumps(receipt)
        for value in ('X-Amz-', 'ephemeral-credential', 'private-', 'csrf_token', '<meta', '/download/'):
            self.assertNotIn(value, text)

    def test_oversize_length_duplicate_encoding_redirect_and_truncation_fail_closed(self):
        mutations = [
            lambda h: h.replace_header('Content-Length', str(subject.SOURCE_LIMIT + 1)),
            lambda h: h.replace_header('Content-Length', '20'),
            lambda h: h.replace_header('Content-Length', '-1'),
            lambda h: h.add_header('Content-Length', '12'),
            lambda h: h.add_header('Content-Encoding', 'gzip'),
            lambda h: (h.add_header('Content-Encoding', 'identity'), h.add_header('Content-Encoding', 'gzip')),
        ]
        for change in mutations:
            h = headers(size=12)
            change(h)
            resolution, _, opener = media_fixture(response_headers=h)
            with self.assertRaises(ValueError):
                subject.fetch_media(resolution, opener)
        resolution, response, opener = media_fixture()
        response.url = 'https://evil.example/media.mp3'
        with self.assertRaises(ValueError):
            subject.fetch_media(resolution, opener)
        self.assertEqual(response.requested_sizes, [])

    def test_unannounced_oversize_body_and_empty_response_are_rejected(self):
        for body in (b'', b'x' * 17):
            resolution, response, opener = media_fixture(body=body, response_headers=headers())
            with patch.object(subject, 'SOURCE_LIMIT', 16), self.assertRaises(ValueError):
                subject.fetch_media(resolution, opener)
            self.assertEqual(response.requested_sizes, [17])

    def test_network_errors_redacted_and_unregistered_cdn_never_requested(self):
        resolution, _, opener = media_fixture()
        opener.open.side_effect = OSError(resolution.download_url + ' cookie-secret')
        with self.assertRaisesRegex(ValueError, 'temporary authorization omitted') as caught:
            subject.fetch_media(resolution, opener)
        self.assertNotIn('X-Amz-', str(caught.exception))
        self.assertNotIn('cookie-secret', str(caught.exception))
        bad = SimpleNamespace(**resolution.__dict__)
        bad.download_url = 'https://evil.test/signed?credential=secret'
        fresh = Mock()
        with self.assertRaises(ValueError):
            subject.fetch_media(bad, fresh)
        fresh.open.assert_not_called()

    def test_decoder_must_match_native_extension_and_single_audio_stream(self):
        def probe(container='mp3', codec='mp3'):
            return {'format': {'format_name': container}, 'streams': [
                {'codec_type': 'audio', 'codec_name': codec}]}
        for suffix, container, codec in [('.mp3', 'mp3', 'mp3'), ('.ogg', 'ogg', 'vorbis'),
                                          ('.ogg', 'ogg', 'opus'), ('.flac', 'flac', 'flac'),
                                          ('.wav', 'wav', 'pcm_s16le')]:
            subject.validate_native_probe(suffix, probe(container, codec))
        attached = probe()
        attached['streams'].append({'codec_type': 'video', 'codec_name': 'mjpeg', 'disposition': {'attached_pic': 1}})
        subject.validate_native_probe('.mp3', attached)
        for bad in (probe('ogg'), probe('mp3', 'aac'), {'format': {'format_name': 'mp3'}, 'streams': []},
                    {'format': {'format_name': 'mp3'}, 'streams': probe()['streams'] * 2},
                    {'format': {'format_name': 'mp3'}, 'streams': [
                        {'codec_type': 'audio', 'codec_name': 'mp3'}, {'codec_type': 'video'}]}):
            with self.assertRaises(ValueError):
                subject.validate_native_probe('.mp3', bad)

    def test_octet_stream_requires_same_decoder_verification(self):
        self.assertEqual(subject.native_filename(headers(media_type='application/octet-stream'),
                                                'Race to Mars.mp3')[1], '.mp3')
        with self.assertRaises(ValueError):
            subject.validate_native_probe('.mp3', {'format': {'format_name': 'matroska'}, 'streams': []})

    def test_size_based_delivery_volumes_split_and_preserve_every_track(self):
        tracks = [{'id': 'track.' + str(i), 'family': 'metal' if i < 4 else 'synth90s',
                   'delivery': {'bytes': 24 * 1024 ** 2}} for i in range(10)]
        volumes = prepare.delivery_volumes(tracks)
        self.assertEqual(len(volumes), 5)
        self.assertEqual([key for volume in volumes for key in volume['tracks']], [t['id'] for t in tracks])
        for volume in volumes:
            self.assertLessEqual(volume['audioBytes'] + volume['metadataReservationBytes'], 64 * 1024 ** 2)
            self.assertEqual(volume['status'], 'size-checked-plan-listening-pending')
        too_large = copy.deepcopy(tracks[:1])
        too_large[0]['delivery']['bytes'] = prepare.VOLUME_LIMIT
        with self.assertRaises(ValueError):
            prepare.delivery_volumes(too_large)
        too_large[0]['delivery']['bytes'] = True
        with self.assertRaises(ValueError):
            prepare.delivery_volumes(too_large)

    def test_production_scratch_and_free_space_guards_fail_before_acquisition(self):
        class File:
            def __init__(self, size): self.size = size
            def is_file(self): return True
            def stat(self): return SimpleNamespace(st_size=self.size)
        root = Mock()
        root.rglob.return_value = [File(prepare.TOTAL_LIMIT - prepare.ROW_RESERVATION + 1)]
        root.glob.return_value = []
        with self.assertRaisesRegex(ValueError, '650 MiB'):
            prepare.reserve_row(root)
        root.rglob.return_value = []
        root.glob.return_value = [File(prepare.SCRATCH_LIMIT - prepare.DERIVATIVE_LIMIT + 1)]
        with self.assertRaisesRegex(ValueError, '256 MiB'):
            prepare.reserve_row(root)
        root.glob.return_value = []
        with patch('prepare.shutil.disk_usage', return_value=SimpleNamespace(free=prepare.RESERVE - 1)):
            with self.assertRaisesRegex(ValueError, '1 GiB'):
                prepare.reserve_row(root)
        root.rglob.return_value = [File(prepare.TOTAL_LIMIT + 1)]
        with self.assertRaisesRegex(ValueError, '650 MiB'):
            prepare.verify_storage(root)
        root.rglob.return_value = []
        root.glob.return_value = [File(prepare.SCRATCH_LIMIT + 1)]
        with self.assertRaisesRegex(ValueError, '256 MiB'):
            prepare.verify_storage(root)

    def test_semantic_evidence_and_original_filename_can_be_retained_without_signed_url(self):
        _, receipt = subject.acquire(row(), self._client(), media_fixture()[2])
        fake_path = Mock()
        output = Mock()
        output.__truediv__ = Mock(return_value=fake_path)
        partial = {}
        with patch('prepare.acquire_itch', return_value=(b'native bytes', receipt)):
            body, native, evidence = prepare.itch_evidence(row(), output, partial)
        stored = fake_path.write_bytes.call_args.args[0]
        self.assertEqual(body, b'native bytes')
        self.assertEqual(native['fileName'], 'Race to Mars.mp3')
        self.assertEqual(evidence['sourceSnapshot']['url'], row()['source'])
        self.assertNotIn(b'X-Amz-', stored)
        self.assertNotIn(b'private-', stored)
        self.assertNotIn(b'<meta', stored)
        self.assertEqual(json.loads(stored)['native']['sha256'], subject.hashlib.sha256(body).hexdigest())

    def _client(self):
        client = subject.EvidenceClient(row()['source'])
        client.client = FixtureClient()
        return client


if __name__ == '__main__':
    unittest.main()
