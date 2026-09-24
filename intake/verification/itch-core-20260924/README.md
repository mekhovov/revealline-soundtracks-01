# Ten pending retro and metal auditions

This source change connects the merged public itch download resolver to the existing hosted core intake. It queues four DOS-88, two escp and four David KBD individual recordings. These are six synth and four metal candidates, not approved game additions and not Ukrainian repertoire. Content ID status is unknown and Recording mode eligibility remains false.

The active manifest has an identical named copy at `intake/itch-core-audition-20260924.json`. The prior two-song Nakarada manifest remains byte-for-byte archived at `intake/archive/metal-nakarada-audition-20260924/source-manifest.json` (SHA-256 c26eb3c1357beee40ea6ceac5001fb15651d5fb86d494722da1628e7bd65c1dd). The earlier thirteen-song archive is unchanged.

## Acquisition and evidence

Only the exact reviewed free upload IDs are permitted. The paid 716 MB archive is not requested. Public licence facts, page SHA-256, creator/source identity, upload ID, native filename/MIME/size/hash and delivery facts are retained. Raw itch HTML is intentionally not retained because it can contain anonymous session keys. Cookies, CSRF values, generated page keys and signed media query strings stay in transient memory and are excluded from receipts and error text.

Downloads validate the exact HTTPS CDN identity before requesting, refuse redirects and encoded responses, reject ambiguous or unsafe Content-Disposition names, and bound the response to 64 MiB even without Content-Length. DOS-88 and David KBD filenames must exactly match the reviewed upload names. escp's visible upload titles lack extensions: the exact upload ID binds the recording, and the returned safe filename is retained for review. Supported native formats are MP3, Ogg Vorbis/Opus, FLAC and PCM WAV; ffprobe must agree with the extension and find one audio stream. Attached cover art is allowed. Every complete original and derivative must decode successfully.

Sources stay unchanged in hash-addressed originals. Derivatives retain the existing 256 kbps MP3 / −16 LUFS ±1 LU / ≤−1 dBTP checks and pinned game MP3 inspector. Actual byte counts split delivery-volume plans at 64 MiB with 512 KiB reserved for metadata. These plans are not published albums; final packaging must still verify the completed package size.

## Storage and verification

Hosted intake reserves each row against the 650 MiB total production budget, keeps at least 1 GiB free, caps each derivative at 24 MiB and reserves scratch against 256 MiB. Partial sources and failed derivative evidence are retained and budgeted. No local media was acquired and no local files were written while the workstation was out of space.

The memory-only source run passed 46 tests, including all 13 existing resolver regressions and 14 new adapter/integration-boundary tests. Three existing tests requiring temporary files were excluded locally; the unchanged hosted workflow's `test_*.py` discovery runs all 49 tests before acquisition. Actual acquisition, full decoding, loudness measurements and runtime inspection are pending that hosted run. Full-track/repeated listening, game transitions, warning audibility and game admission remain pending.

No public inventory, preview page, MP3, game default, workflow or listening approval changes in this PR. A separate reviewed archive publication PR is required after the produced evidence has been inspected.
