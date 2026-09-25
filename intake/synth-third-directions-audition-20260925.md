# Third synth-direction audition intake

This batch retains four source-verified OpenGameArt recordings for comparison only.
It does not publish them, add them to the game catalogue or default playlists, or
make them eligible for Recording mode. Musical fit, full-track listening,
repeated-play, device, transition, warning-audibility and gameplay review all
remain pending.

## Exact reviewed sources

| Candidate | Creator evidence | Licence and special terms | Exact native recording |
| --- | --- | --- | --- |
| **90s Racer Techno** — Bogart VGM | [OpenGameArt source](https://opengameart.org/content/90s-racer-techno) | CC BY 4.0. The creator requires credit and a link to [Bogart VGM on Facebook](https://www.facebook.com/BogartVGM/); the manifest credit includes both. | MP3, 6,919,579 bytes, SHA-256 `da4d941c6abfc4aa4f44191fa27cb06afb80681e0af8c7eb5c1a32ff5c85605b` |
| **Neon Pulse** — Arold Valda | [OpenGameArt source](https://opengameart.org/content/neon-pulse) | CC BY 4.0. The source says this release has Content ID disabled. Recording mode still remains disabled until the separate product review. | FLAC, 22,513,720 bytes, SHA-256 `533aceb7e3f81f4f2a8a23527526334697d6d7c074d5711a447accf41b01fed7` |
| **Prismatic Light** — tcarisland | [OpenGameArt source](https://opengameart.org/content/prismatic-light) | CC BY 4.0. The source publishes 140 BPM and asks for a notice after use without making advance contact a condition. | MP3, 5,511,488 bytes, SHA-256 `2e0a45a3423ade454c50ba61fe82e8c7e912a22ab390887607e02458cec8b239` |
| **Future Travel** — Zodik | [OpenGameArt source](https://opengameart.org/content/zodik-future-travel) | CC BY 3.0; source attribution says `Credits: Zodik`. | OGG Vorbis, 2,045,714 bytes, SHA-256 `10d7b71e7e48ce05f31fbfd820e6d669e6b7690b89fde9b199c25bbf07c2de92` |

The native files are stereo at 44.1 kHz. The exact pinned recordings passed a
complete local decode, two-pass normalization and the pinned game MP3 inspector
before this intake was proposed. This preflight used FFmpeg 9.0.2 and game
inspector revision `71a0ffeaeb5079ac6e87a7d80327c6b34948aaa3`:

| Candidate | Native duration | Native loudness / true peak | Preflight derivative | Encoded loudness / true peak |
| --- | ---: | ---: | --- | ---: |
| 90s Racer Techno | 172.912404 s | -10.68 LUFS / +0.02 dBTP | 5,535,494 bytes; `f7865e1c949bbbcb9a7354ec32c1e4afc95cfbb2091ec4b0d3d977ad9cd4d72a` | -15.99 LUFS / -5.06 dBTP |
| Neon Pulse | 193.695011 s | -14.26 LUFS / -0.99 dBTP | 6,200,049 bytes; `e6f7981168ff639a9b5e2026ef304120101424a97eab9cd814071111b25aab81` | -16.00 LUFS / -2.61 dBTP |
| Prismatic Light | 229.642417 s | -12.32 LUFS / +0.90 dBTP | 7,350,273 bytes; `508e121c46cbab205b40dd682108ea53d374175cb68907253f989e503ace0ea0` | -16.00 LUFS / -2.67 dBTP |
| Future Travel | 187.860952 s | -11.18 LUFS / +0.55 dBTP | 6,013,639 bytes; `3693ba39b997d9d6866c7c93e7534f67eb8a9fb69d76837cf05b877c97f6f1ad` | -16.00 LUFS / -4.29 dBTP |

All four rows completed without a decode, duration, duplicate, size, loudness,
true-peak or MP3 inspection failure. The derivatives total 25,099,455 bytes and
fit one 64 MiB optional synth volume with the metadata reserve. The pull-request
workflow repeats the complete acquisition and records its runner-specific
FFmpeg version and exact derivative identities in the retained receipt.

The two MP3 originals remain byte-exact even though the intake also produces a
separate consistent audition derivative. The FLAC and OGG originals remain
byte-exact beside their 256 kbps stereo MP3 derivatives. Every derivative uses
the established 44.1 kHz two-pass `loudnorm` process, aiming for -16 LUFS and
at most -1 dBTP after MP3 encoding; the encoder retries progressively lower
peak targets when needed. Every conversion is disclosed in the receipt.

## Duplicate and archive boundaries

Before intake, the four exact native SHA-256 values and normalized titles were
checked across the 128-track unified catalogue and every retained batch preview
catalogue. No exact native, derivative or title identity matched. The hosted
preparation repeats that check before it writes a source original or derivative.

Source pages are retained as SHA-256-addressed evidence. The manifest pins each
media URL, byte count, SHA-256 and native suffix, and pins the attribution or
rights sentence that must still appear on the source page. A changed page,
download, redirect, size, hash, format or required credit stops that row. Partial
failures remain in the hosted artifact rather than being reported as passes.
The preflight source-page snapshots were `eb28a813…` (Bogart), `7fcf1676…`
(Arold Valda), `66b848ff…` (tcarisland) and `df068f8d…` (Zodik); the hosted
receipt records every complete SHA-256 again instead of treating these mutable
snapshots as permanent authority.

The batch keeps the existing 1 GiB disk floor, 650 MiB production reservation,
256 MiB scratch reservation and 64 MiB optional-volume limit. It does not change
the public archive or any immutable release path.
