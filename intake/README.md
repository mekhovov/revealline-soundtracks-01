# Core soundtrack expansion intake

This directory prepares a separate retro/metal candidate batch without changing
the existing 70 published recordings or their immutable inventory. It is excluded
from Pages staging. The game does not discover or admit these candidates.

`core-20260924.json` records 14 distinct candidate compositions absent from the
existing catalogue: six metal recordings and eight retro recordings. Source
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

Local use requires at least 1 GiB free after reservation. No model, sample library,
or complete source collection is downloaded. Active production is bounded to
650 MiB. Process one recording at a time; no decoded PCM album is written.

Run the non-network tests with:

```sh
python3 -m unittest discover -s intake -p 'test_*.py'
```
