import json
import unittest
from urllib.parse import urlencode
from unittest.mock import Mock
import itch_source as subject


def signed(game, upload, **changes):
    values = {
        'X-Amz-Algorithm': 'AWS4-HMAC-SHA256',
        'X-Amz-Credential': 'ephemeral-credential/20260924/auto/s3/aws4_request',
        'X-Amz-Date': '20260924T030000Z',
        'X-Amz-Expires': '900',
        'X-Amz-SignedHeaders': 'host',
        'X-Amz-Signature': 'a' * 64,
    }
    values.update(changes)
    return f'https://{subject.CDN_HOST}/upload2/game/{game}/{upload}?' + urlencode(values)


class FixtureClient:
    def __init__(self, track_id='dos88.race-to-mars'):
        creator, self.upload, self.name, _ = subject.UPLOAD_PINS[track_id]
        self.source, self.game, license_link = subject.SOURCE_PINS[creator]
        self.page = '<a href="' + license_link + '">Creative Commons Attribution v4.0 International</a>'
        self.purchase = (
            '<meta name="csrf_token" value="private-purchase-token">'
            '<a class="direct_download_btn">No thanks</a>'
            "init_GamePurchase('#game_purchase_1', " +
            json.dumps({'id': self.game, 'slug': self.source.rsplit('/', 1)[1],
                        'min_price': 0, 'actual_price': 0}) + ');'
        )
        self.generated = {'url': self.source + '/download/private-key'}
        self.uploads = (
            '<meta name="csrf_token" value="private-download-token">'
            '<div class="uploads"><div class="upload">'
            f'<a class="button download_btn" data-upload_id="{self.upload}">Download</a>'
            '<div class="info_column"><div class="upload_name">'
            f'<strong class="name" title="{self.name}">{self.name}</strong>'
            '</div></div></div></div>'
        )
        self.result = {'url': signed(self.game, self.upload), 'external': False}
        self.requests = []

    def read(self, url, data=None):
        self.requests.append((url, data))
        if url == self.source:
            return self.page
        if url == self.source + '/purchase':
            return self.purchase
        if url == self.source + '/download_url':
            assert data == {'csrf_token': 'private-purchase-token'}
            return json.dumps(self.generated)
        if url == self.generated.get('url'):
            assert data is None
            return self.uploads
        if url == self.source + f'/file/{self.upload}?source=game_download':
            assert data == {'csrf_token': 'private-download-token'}
            return json.dumps(self.result)
        raise AssertionError('Unexpected request')


class ItchSourceTests(unittest.TestCase):
    def test_all_ten_exact_candidates_resolve_metadata_without_media_requests(self):
        self.assertEqual(len(subject.UPLOAD_PINS), 10)
        for track_id in subject.UPLOAD_PINS:
            with self.subTest(track_id=track_id):
                client = FixtureClient(track_id)
                result = subject.resolve(track_id, client)
                self.assertEqual(result.upload_name, client.name)
                self.assertEqual(len(client.requests), 5)
                self.assertTrue(all(url.startswith(client.source) for url, _ in client.requests))
                self.assertFalse(result.receipt()['audioAcquired'])
                self.assertFalse(result.receipt()['listeningApproval'])
                self.assertFalse(result.receipt()['admitted'])

    def test_encoded_download_key_stays_ephemeral_and_bounded(self):
        client = FixtureClient()
        client.generated['url'] = client.source + '/download/base64%2b%2f%3d%2esignature'
        result = subject.resolve('dos88.race-to-mars', client)
        self.assertNotIn('base64', json.dumps(result.receipt()))
        for token in ['%2e%2e', 'base64%252fescape', 'base64%00', 'a' * 201]:
            self.assertFalse(subject.valid_download_page(client.source,
                             client.source + '/download/' + token))

    def test_unknown_recording_never_requests(self):
        client = Mock()
        with self.assertRaises(subject.SourceChanged):
            subject.resolve('unreviewed', client)
        client.read.assert_not_called()

    def test_paid_or_changed_game_and_missing_free_choice_fail_before_download(self):
        changes = [
            ('"min_price": 0', '"min_price": 1'),
            ('"actual_price": 0', '"actual_price": 1'),
            ('"min_price": 0', '"min_price": false'),
            ('"id": 66639', '"id": 66640'),
            ('"slug": "dos-88-music-library"', '"slug": "other"'),
            ('direct_download_btn', 'checkout_btn'),
            ('name="csrf_token"', 'name="unrelated"'),
        ]
        for before, after in changes:
            with self.subTest(after=after):
                client = FixtureClient()
                client.purchase = client.purchase.replace(before, after)
                with self.assertRaises(subject.SourceChanged):
                    subject.resolve('dos88.race-to-mars', client)
                self.assertEqual(len(client.requests), 2)

    def test_licence_change_stops_before_purchase(self):
        client = FixtureClient()
        client.page = client.page.replace('assets-cc4-by', 'assets-cc4-by-nc')
        with self.assertRaises(subject.SourceChanged):
            subject.resolve('dos88.race-to-mars', client)
        self.assertEqual(len(client.requests), 1)

    def test_wrong_duplicate_or_missing_upload_title_fails_before_file_endpoint(self):
        changes = [
            ('data-upload_id="206071"', 'data-upload_id="206070"'),
            ('title="Race to Mars.mp3"', 'title="Alternate recording.mp3"'),
            ('class="name"', 'class="other"'),
            ('<strong class="name"', '<strong class="name" title="First"><strong class="name"'),
        ]
        for before, after in changes:
            with self.subTest(after=after):
                client = FixtureClient()
                client.uploads = client.uploads.replace(before, after)
                with self.assertRaises(subject.SourceChanged):
                    subject.resolve('dos88.race-to-mars', client)
                self.assertEqual(len(client.requests), 4)
        client = FixtureClient()
        client.uploads += client.uploads.replace('<meta name="csrf_token" value="private-download-token">', '')
        with self.assertRaises(subject.SourceChanged):
            subject.resolve('dos88.race-to-mars', client)

    def test_generated_page_rejects_external_origin_credentials_query_and_traversal(self):
        for value in [
            'https://evil.example/download/key',
            'http://dos88.itch.io/dos-88-music-library/download/key',
            'https://user@dos88.itch.io/dos-88-music-library/download/key',
            'https://dos88.itch.io/other/download/key',
            'https://dos88.itch.io/dos-88-music-library/download/key?other=1',
            'https://dos88.itch.io/dos-88-music-library/download/../purchase',
        ]:
            with self.subTest(url=value):
                client = FixtureClient()
                client.generated['url'] = value
                with self.assertRaises(subject.SourceChanged):
                    subject.resolve('dos88.race-to-mars', client)
                self.assertEqual(len(client.requests), 3)

    def test_file_response_refuses_external_quarantined_or_changed_protocol(self):
        for response in [
            {'url': signed(66639, 206071), 'external': True},
            {'url': signed(66639, 206071), 'external': 0},
            {'url': signed(66639, 206071)},
            {'url': signed(66639, 206071), 'external': False, 'lightbox': {}},
            {'errors': ['Not available']},
        ]:
            with self.subTest(keys=list(response)):
                client = FixtureClient()
                client.result = response
                with self.assertRaises(subject.SourceChanged):
                    subject.resolve('dos88.race-to-mars', client)

    def test_cdn_is_exact_creator_upload_and_signed_shape(self):
        valid = signed(66639, 206071)
        bad = [
            valid.replace(subject.CDN_HOST, 'evil.example'),
            valid.replace('https:', 'http:'),
            valid.replace(subject.CDN_HOST, 'user@' + subject.CDN_HOST),
            valid.replace('/66639/', '/66640/'),
            valid.replace('/206071?', '/206070?'),
            valid + '#fragment',
            valid + '&extra=1',
            valid + '&X-Amz-Expires=900',
            valid.replace('900', '0'),
            signed(66639, 206071, **{'X-Amz-Algorithm': 'other'}),
            signed(66639, 206071, **{'X-Amz-Signature': 'bad'}),
            signed(66639, 206071, **{'X-Amz-Expires': '86401'}),
        ]
        for value in bad:
            with self.subTest(url=value[:60]):
                with self.assertRaises(subject.SourceChanged):
                    subject.checked_cdn(value, 66639, 206071)

    def test_tokens_are_not_exposed_by_repr_or_receipt(self):
        result = subject.resolve('dos88.race-to-mars', FixtureClient())
        safe = repr(result) + json.dumps(result.receipt())
        for secret in ['X-Amz-', 'ephemeral-credential', 'private-', 'a' * 64]:
            self.assertNotIn(secret, safe)
        self.assertIn('X-Amz-Signature', result.download_url)

    def test_redirects_are_rejected_before_follow(self):
        with self.assertRaisesRegex(subject.SourceChanged, 'Unexpected metadata redirect'):
            subject.NoRedirects().redirect_request(None, None, 302, '', {}, 'https://evil.example')

    def test_client_rejects_unregistered_origin_and_endpoints_without_io(self):
        with self.assertRaises(subject.SourceChanged):
            subject.MetadataClient('https://evil.example')
        client = subject.MetadataClient(subject.SOURCE_PINS['dos88'][0])
        client.opener = Mock()
        for url in ['https://evil.example/', client.source + '/purchase?key=1',
                    client.source + '/file/206071?source=other',
                    client.source + '/download/../purchase']:
            with self.subTest(url=url):
                with self.assertRaises(subject.SourceChanged):
                    client.read(url)
        client.opener.open.assert_not_called()

    def test_client_limits_response_and_redacts_network_errors(self):
        client = subject.MetadataClient(subject.SOURCE_PINS['dos88'][0])
        response = Mock()
        response.url = client.source
        response.read.return_value = b'x' * (subject.PAGE_LIMIT + 1)
        client.opener = Mock()
        client.opener.open.return_value.__enter__ = Mock(return_value=response)
        client.opener.open.return_value.__exit__ = Mock(return_value=None)
        with self.assertRaisesRegex(subject.SourceChanged, 'bounded size'):
            client.read(client.source)
        client.opener.open.side_effect = OSError('secret temporary key')
        with self.assertRaisesRegex(subject.SourceChanged, 'no media was fetched') as caught:
            client.read(client.source)
        self.assertNotIn('secret', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
