# Approved directions: hosted audition intake

This is a twelve-recording **audition**, following the requested synth/electro and stronger metal directions. Approval of a direction is not approval of these recordings. The source manifest is immutable and hash-bound by `prepare_approved_directions.py`. Existing manifests, public audio, catalogues, players and historical batches are unchanged.

No audio was acquired locally while preparing this change. Anonymous source metadata was checked on 25 September 2026. Native acquisition, complete decoding, loudness measurement, 256 kbps MP3 conversion and technical verification run only in the distinct **Prepare approved-direction audition candidates** workflow. Its artifact is `approved-directions-audition-candidates`; it does not publish files or admit songs into the game.

## Exact slate and source bindings

All twelve source pages currently state **CC BY 4.0 International**. Retain the artist, title, source and licence link in every derivative. OGA's page additionally requests Bogart VGM's Facebook link; the manifest includes it. These sources permit redistribution under that licence; future public preview publication still requires review of the acquired exact files and evidence.

| Recording | Exact native upload name | Source game / upload ID | Suggested family |
| --- | --- | --- | --- |
| Bogart VGM — Retroracing Nightlife | `Retroracing Nightlife.mp3` | [OGA source](https://opengameart.org/content/retroracing-nightlife); linked native URL ends `Retroracing%20Nightlife_0.mp3` | Synth/electro |
| David KBD — Electric Pulse | `DavidKBD - Electric Pulse - 01 - Electric Pulse-full.ogg` | [Electric Pulse](https://davidkbd.itch.io/electric-pulse-synthwave-retro-futuristic-music-pack): 2187961 / 8382056 | Synth/electro |
| David KBD — Retrochrome Nights | `DavidKBD - Electric Pulse - 04 - Retrochrome Nights-full.ogg` | Electric Pulse: 2187961 / 8382060 | Synth/electro |
| David KBD — Vapor Trails Pursuit | `DavidKBD - Electric Pulse - 09 - Vapor Trails Pursuit-full.ogg` | Electric Pulse: 2187961 / 8382528 | Synth/electro |
| David KBD — Electric Dreams of Infinity | `DavidKBD - Electric Pulse - 07 - Electric Dreams of Infinity-full.ogg` | Electric Pulse: 2187961 / 8382065 | Synth/electro |
| David KBD — Digital Horizon | `DavidKBD - Electric Pulse - 02 - Digital Horizon-full.ogg` | Electric Pulse: 2187961 / 8382053 | Synth/electro |
| David KBD — Plasma Storm | `DavidKBD - InterstellarPack - 02 - Plasma Storm.ogg` | [Interstellar](https://davidkbd.itch.io/interstellar-edm-metal-music-pack): 1704727 / 6501647 | EDM/metal |
| David KBD — Meteor Shower | `DavidKBD - Interstellar vol2 01 - Meteor Shower.ogg` | [Interstellar vol. 2](https://davidkbd.itch.io/interstellar-vol2-edm-metal-music-pack): 2445174 / 13507636 | EDM/metal |
| David KBD — Urban Hairbanger | `DavidKBD - Hair And Knuckles Pack - 03 - Urban Hairbanger.ogg` | [Hair and Knuckles](https://davidkbd.itch.io/hair-and-kuckles-technometal-music-pack): 1182848 / 4397475 | Techno/metal |
| David KBD — Grave Rot Requiem | `DavidKBD-01 - Grave Rot Requiem.ogg` | [Purgatory vol. 3](https://davidkbd.itch.io/purgatory-vol-3-extreme-metal-music-pack): 3755088 / 14549171 | Extreme metal |
| David KBD — Devoured by Darkness | `DavidKBD-04 - Devoured by Darkness.ogg` | Purgatory vol. 3: 3755088 / 14549176 | Extreme metal |
| David KBD — Tear their fate | `DavidKBD - Purgatory Pack vol2 - 01 - Tear their fate.ogg` | [Purgatory vol. 2](https://davidkbd.itch.io/purgatory-vol-2-extreme-metal-music-pack): 2246806 / 12451192 | Extreme metal with vocals |

The source pages describe racing synthwave, cyberpunk synthwave, EDM/metal and techno/metal; these are research-based selection hypotheses, not listening findings. Proposed roles are gameplay, with medium-high synth and high metal energy. The five Electric Pulse selections use their individual full OGG uploads, not short variants, WAV duplicates or paid archives. Full-track durations will come from hosted decoding, not inferred filenames or loop endpoints. The existing 60–720 second recording envelope remains unchanged.

Purgatory vol. 3 publishes tempos of 170 BPM for Grave Rot Requiem and 105 BPM for Devoured by Darkness. Its loop endpoints are configuration data, not measured recording durations. The selected Purgatory vol. 2 file contains creator-described vocals. Its paid instrumental alternative is excluded. Lyrics, explicit content and suitability remain unreviewed for all twelve.

All twelve retain `contentId: "unknown"` and `recordingModeEligible: false`. The creator's [Purgatory I/II reply about Content ID](https://itch.io/post/16456992) is a useful lead; it does not automatically establish the status of every pack or this exact master. No lyrics, artwork or paid files are acquired by this intake.

## Fail-closed acquisition and evidence

- The entry point checks the complete manifest SHA-256 before any network access and refuses local acquisition or an existing output directory.
- Each itch source is bound to its exact origin, slug, game ID, upload ID and visible upload filename. Anonymous free access must still be offered at zero price; changing to a purchase, account requirement, external download or paid alternate stops intake.
- For these six new itch sources, both the asset licence badge and direct CC BY 4.0 link must remain. All normalized creator-description text and ordered link targets are hash-pinned. A new restriction, edited link or changed description requires review even if the CC BY badge remains.
- Session HTML, cookies, CSRF tokens, private download-page URLs and signed media URLs stay ephemeral. Receipts retain semantic source facts, description fingerprints and native hashes without temporary credentials.
- The CDN host, game/upload path, response filename and decoded format must match the exact recording. No redirects or cross-pairing between registered uploads are allowed.
- OGA uses the existing source-page/download-link/licence verification. The new entry point additionally hash-binds its exact title, artist, source, native URL, credit and pending flags through the immutable manifest.
- Hosted processing retains native bytes unchanged and normalized MP3 derivatives with exact hashes, decoder facts, measured duration, loudness attempts and failures. The original production, scratch, free-space and per-volume limits remain 650 MiB, 256 MiB, at least 1 GiB free and less than 64 MiB per planned volume including metadata reservation.
- The distinct artifact includes the source manifest, runner and PR-head revisions, intake source-file fingerprints, test output, successful recordings and partial failures. Review must verify the original hosted artifact's digest and tree binding before any later archive PR.
- Existing collection title/hash checks run before acceptance of a prepared recording. Matching names were absent from the 104-recording catalogue during source selection; exact audio deduplication remains a hosted check.

All listening, transition, warning-audibility, mono/small-speaker, offline, physical-device and public-game acceptance remains pending. Technical success alone does not approve musical fit. No Ukrainian designation is assigned to these recordings.

## Reserves and exclusion

- **Runner2088 — wekont** remains a short reserve: [creator distribution page](https://freemusicarchive.org/music/wekont/single/runner2088mp3/). The published duration is 97 seconds; it is not part of this manifest, and no audio was acquired.
- **City Limits Crash — David KBD**, from [Reckless vol. 2](https://davidkbd.itch.io/reckless-vol-2-punk-metal-music-pack), remains a short reserve. Creator loop timing is not a measured duration. It is not registered for acquisition here.
- **Street Beat** is excluded: its [current source description](https://davidkbd.itch.io/street-beat-electronictechno-music-pack) prohibits standalone redistribution despite an asset licence badge. Neither older comments nor the badge override that unresolved conflict. No Street Beat source or upload is allowlisted.

## Source-only validation

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s intake -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 intake/prepare_approved_directions.py --check
```

These commands use metadata fixtures and small temporary evidence only; they do not fetch audio or exercise the hosted FFmpeg pipeline. Existing historical-manifest hash tests remain in place, scoped to their original ten itch recordings. Hosted checks and any failures must be reported separately.
