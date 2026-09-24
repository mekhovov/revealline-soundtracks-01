# Free itch.io candidate resolution — 24 September 2026

This is source-acquisition preparation, **not music admission or publication**.
No MP3/Ogg bytes were downloaded, auditioned or approved. The existing catalogue,
published inventory and intake manifests are unchanged.

## Reviewed public sources and stable uploads

All three creator pages currently display CC BY 4.0 and a public free-download
choice. The resolver only accepts the following existing creator/game/upload
bindings, then resolves a new temporary URL through the normal anonymous flow.

| Creator source | Game ID | Candidate | Upload ID | Exact public upload title |
| --- | ---: | --- | ---: | --- |
| [DOS-88 library](https://dos88.itch.io/dos-88-music-library) | 66639 | Crash Landing | 206068 | Crash Landing.mp3 |
| DOS-88 library | 66639 | Race to Mars | 206071 | Race to Mars.mp3 |
| DOS-88 library | 66639 | Automata v2 | 206072 | DOS-88 - Automatav2.mp3 |
| DOS-88 library | 66639 | City Stomper | 206074 | DOS-88 - City Stomper.mp3 |
| [escp — Synthasia](https://escpmusic.itch.io/synthasia) | 4662919 | Twilight City | 17878087 | Twilight City |
| escp — Synthasia | 4662919 | Synthasia | 17878086 | Synthasia |
| [David KBD — Eternity](https://davidkbd.itch.io/eternity-metal-scfi-music-pack) | 976471 | The Desolation of a Civilization | 6033123 | DavidKBD - Eternity Pack - 01 - The desolation of a civilization - oneshoot.ogg |
| David KBD — Eternity | 976471 | Agony Space-deep | 6033127 | DavidKBD - Eternity Pack - 02 - Agony Space-deep - oneshoot.ogg |
| David KBD — Eternity | 976471 | God of Darkness | 6033130 | DavidKBD - Eternity Pack - 06 - God of darkness - oneshoot.ogg |
| David KBD — Eternity | 976471 | Suffocation | 6033135 | DavidKBD - Eternity Pack - 07 - Suffocation - oneshoot.ogg |

The David KBD one-shot Ogg files are individually free. The 716 MB WAV archive is
a separate paid option and is explicitly outside this resolver. Alternate loop
encodings do not add compositions. escp's public upload titles omit extensions;
do not invent original filenames before acquisition verifies Content-Disposition.

## Observed anonymous flow

The live public purchase pages and itch.io's own checkout/download scripts expose:

1. GET the exact creator page and require its CC BY 4.0 asset-licence link.
2. GET its /purchase page; bind the exact game ID and slug, zero minimum/actual
   price, CSRF state and the "No thanks" free-download control.
3. POST only the anonymous CSRF token to /download_url. Follow only the returned
   same-creator /download/<temporary-key> metadata page.
4. Require the selected data-upload_id and its exact visible upload title in the
   same upload row. No paid file, arbitrary upload ID or alternative source is inferred.
5. POST only the fresh CSRF token to /file/<upload-id>?source=game_download.
6. Require external:false, the observed exact CDN host, and the exact
   /upload2/game/<game-id>/<upload-id> media path.

The current media host is
itchio-mirror.cb031a832f44726753d6267436f3b414.r2.cloudflarestorage.com.
Its signed URL is ephemeral. Never commit/log its query, anonymous CSRF tokens,
cookies or temporary download-page keys. Resolution.receipt() is deliberately
safe to persist; download_url is excluded from the object's representation.

No redirect is followed by the production metadata client. A changed host,
licence link, paid/download UI, upload ID/name, quarantined file or response shape
stops resolution for renewed review. There is no account login, payment, rating,
creator message, social action, CAPTCHA bypass or media request in this module.

## Verification and next integration

- Thirteen memory-only unit tests cover the ten candidates and rejection of
  changed licences/prices/game IDs, wrong or duplicate upload identity, hostile
  redirects/origins, changed CDN upload paths, altered signed URL shape, oversized
  responses and accidental token disclosure.
- A live metadata probe independently reached all ten exact registered uploads.
  Signed CDN URLs were not fetched. HEAD probes during initial research returned
  403 because these are signed GET URLs; this is not an audio availability pass.
- Initial parser probes rejected URL-encoded key punctuation. The resolver now
  accepts bounded base64/signature punctuation and rejects path traversal,
  double encoding and control bytes; the regression includes encoded keys.
- Local Python HTTPS was blocked by the company's certificate chain. Live metadata
  verification used curl's ordinary trusted TLS; no TLS verification was disabled.
  The production urllib client still needs a hosted live probe.
- These files do not alter prepare.py, admission policy, active intake manifests,
  Pages payload or published audio. The existing intake workflow discovers
  test_*.py when it next runs; its path filter does not automatically run for this
  standalone helper PR. Do not describe the helper's tests as hosted until run.

The next reviewed integration can call resolve(track_id), use its signed URL
only in memory, and validate GET response headers and actual source bytes on a
hosted runner. Preserve native sources and hash-bound evidence, enforce the
existing 64 MiB per-source / 650 MiB total / 1 GiB reserve guards, then retain the
normal complete decode, normalization, MP3 inspection and listening-pending
receipt. Obtain a safe original filename from verified response metadata; do not
derive an extension from the numeric CDN path.

Do not pass tokenized CDN URLs into the old receipt's persisted download/url
fields. Keep the stable creator/game/upload binding and safe CDN path instead.
Integrating this helper must explicitly preserve intake status
rights-reviewed-listening-pending, false listening approval and separate archive
publication/admission review.
