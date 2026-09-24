# Core soundtrack expansion intake

This directory prepares a separate retro/metal candidate batch without changing
the existing 70 published recordings or their immutable inventory. It is excluded
from Pages staging. The game does not discover or admit these candidates.

`core-20260924.json` records 13 distinct candidate compositions absent from the
existing catalogue: six metal recordings and seven retro recordings. Source
pages advertise CC0 or CC BY 4.0; the latter retains Bogart VGM's requested artist
link. The exact downloaded page and recording must agree before preparation.

The pull-request workflow runs the repository's small intake checks, then uses a
hosted Ubuntu runner to retain original downloads, decode them completely,
prepare 256 kbps MP3 derivatives, measure encoded loudness and true peaks, and
inspect every MPEG frame using the pinned game's importer. It preserves partial
failures and source licence snapshots in a 30-day artifact. Source masters must
be archived before that artifact expires; it is not permanent storage.

The tool never grants listening approval, creates a release, updates the live
inventory or publishes Pages. A real full-track and in-game review is required
before a later versioned archive admission. Unknown Content ID status remains
unknown. The source filenames and hashes remain in the receipt; generated MP3
filenames use exact SHA-256 identities.

## Separate Ukrainian candidate

`ukrainian-shchedryk-20260924.json` prepares Alexander Nakarada's **Carol of the
Bells (Metal Version)** in a separate `ukrainian-shchedryk-candidate` hosted
artifact. Its creator's [track page](https://creatorchords.com/music/carol-of-the-bells-metal-version/)
offers this recording under CC BY 4.0 with the supplied artist attribution. The
allowlist binds that one page to its exact MP3; it does not grant access to other
CreatorChords recordings or arbitrary CDN paths. Redirects are checked before a
destination is requested. The original MP3 is bounded to 11 MiB and retained
unchanged alongside a measured derivative.

The receipt preserves raw, SHA-256-addressed snapshots of the track page, the
[licensing page](https://creatorchords.com/licensing-info/) and the
[FAQ](https://creatorchords.com/faq/). The licensing page reports Smart Content ID
registration: `contentId` stays `true`, and recording mode must exclude this
candidate. Attribution does not guarantee that an automated video claim cannot
occur. Changed licensing or Content ID evidence stops preparation for review.

The proposed descriptor is **Ukrainian-melody metal adaptation**. The
[Ukrainian Institute programme](https://ui.org.ua/wp-content/uploads/2022/12/programme_notes-from-ukraine.pdf)
documents the Shchedryk/Carol of the Bells connection; this is not a claim of
traditional instrumentation or a Ukrainian ensemble performance. Instrumental,
cultural, complete-track and game-listening reviews remain pending. Another
Shchedryk arrangement would not count as a new composition. This intake is not
game integration, a runtime CDN hotlink, or publication approval.

Local use requires at least 1 GiB free after reservation. No model, sample library,
or complete source collection is downloaded. Active production is bounded to
650 MiB. Process one recording at a time; no decoded PCM album is written.

Run the non-network tests with:

```sh
python3 -m unittest discover -s intake -p 'test_*.py'
```
