# Second synth/electro and rhythmic-metal audition intake

This source-only intake prepares twelve additional recordings after the first
approved-direction slate. It publishes no audio, grants no listening approval,
admits no recording into the game, changes no default, and leaves every track
ineligible for Recording mode. No audio was downloaded locally while preparing
this revision.

All selected source pages publish CC BY 4.0. The five explicit `-full.ogg`
synth files and six complete metal album files are available through their
respective zero-price itch acquisition routes. The OGA recording is an
individually linked MP3 named **Neon Action Full**. CC BY 4.0 permits public
redistribution with attribution, a licence link, and an indication of changes.
Source-page cover artwork is outside this intake.

## Repaired exact slate

| Recording | Exact free file | Source / upload ID | Published duration evidence |
| --- | --- | --- | --- |
| Cyber Lights | `DavidKBD - Electric Pulse - 03 - Cyber Lights-full.ogg` | [Electric Pulse](https://davidkbd.itch.io/electric-pulse-synthwave-retro-futuristic-music-pack), 8382058 | 4:11 |
| Neon Arcadia Awakening | `DavidKBD - Electric Pulse - 05 - Neon Arcadia Awakening-full.ogg` | Electric Pulse, 8382061 | 3:52 |
| Time Warp | `DavidKBD - Electric Pulse - 06 - Time Warp-full.ogg` | Electric Pulse, 8382063 | 3:56 |
| Quantum Ripples of Sound | `DavidKBD - Electric Pulse - 08 - Quantum Ripples of Sound-full.ogg` | Electric Pulse, 8382067 | 5:02 |
| Synthetic Power Surge | `DavidKBD - Electric Pulse - 10 - Synthetic Power Surge-full.ogg` | Electric Pulse, 8382551 | 4:11 |
| Neon Action Full | `Neon Action Full.mp3` | [Bogart VGM / OGA](https://opengameart.org/content/neon-action) | Exact MP3 duration pending hosted decode; only the explicitly named Full file is selected |
| Solar Storm | `DavidKBD - Interstellar vol2 02 - Solar Storm.ogg` | [Interstellar vol. 2](https://davidkbd.itch.io/interstellar-vol2-edm-metal-music-pack), 13507642 | 4:03 |
| Galactic Battle | `DavidKBD - Interstellar vol2 04 - Galactic Battle.ogg` | Interstellar vol. 2, 13507638 | 4:13 |
| Orbital Assault | `DavidKBD - Interstellar vol2 09 - Orbital Assault.ogg` | Interstellar vol. 2, 13507646 | 3:23 |
| They want death | `DavidKBD - Purgatory Pack vol2 - 02 - They want death.ogg` | [Purgatory vol. 2](https://davidkbd.itch.io/purgatory-vol-2-extreme-metal-music-pack), 12451195 | 4:11 |
| Insanity is your flame | `DavidKBD - Purgatory Pack vol2 - 04 - Insanity is your flame.ogg` | Purgatory vol. 2, 12451193 | 3:12 |
| Sin, their pity, their agony | `DavidKBD - Purgatory Pack vol2 - 05 - Sin, their pity, their agony.ogg` | Purgatory vol. 2, 12451194 | 3:55 |

David KBD's official album pages document the listed composition durations:
[Electric Pulse](https://davidkbd.bandcamp.com/album/electric-pulse-synthwave-retro-futuristic-music-pack-original-game-soundtrack),
[Interstellar vol. 2](https://davidkbd.bandcamp.com/album/interstellar-vol-2-edm-metal-music-pack-original-game-soundtrack),
and [Purgatory vol. 2](https://davidkbd.bandcamp.com/album/purgatory-vol-2-extreme-metal-music-pack-original-game-soundtrack).
The exact freely downloadable files still have to pass hosted decoding and the
unchanged 180–720 second envelope. Album duration evidence never overrides an
exact-file failure.

The synth half targets complete outrun/synthwave arrangements. The metal half
targets rhythmic EDM-metal and extreme metal in the direction the user asked
to continue. Purgatory vol. 2 is creator-described as containing vocals;
lyrics, explicit content, Content ID, transitions, warning audibility and game
suitability remain unreviewed. Every approval flag is false.

## Preserved failed hosted evidence

The first source revision at commit
`ad0374b6cd6087d85d1814ae5d0c83da421113a6` failed all twelve candidates in
[hosted run 36069462468](https://github.com/mekhovov/revealline-soundtracks-01/actions/runs/36069462468).
Its partial artifact is `10837930834`, 18,660,997 bytes, SHA-256
`9db0681e34eae57e327baf89cb5297692e190ec6c5af082921f4a77beeb0c6f3`.
That evidence is retained and is not relabelled as a successful audition.

The exact free Pink Bloom, HexaPuppies, Reckless and original Purgatory files
were short loop assets below three minutes, even where a longer album edition
exists. The Great Machine and Disaster also returned native filenames that did
not equal their visible upload titles. Keep My Rhythm reached an inherited
parser refusal because its quoted filename contains a comma; the parser now
accepts commas only inside a well-formed quoted filename while continuing to
reject duplicate and combined header values. Keep My Rhythm remains held until
its exact native duration is separately proven.

## Fail-closed preparation and deduplication

- The complete manifest hash is checked before network access; local audio
  acquisition remains refused.
- Itch sources are bound to origin, slug, game ID, normalized description hash,
  CC BY badge, direct licence link, upload ID and visible filename. The free
  route must remain available.
- The OGA page must still link the exact full MP3 and licence. Redirects,
  alternate files, external hosts and changed terms stop intake.
- Cookies, CSRF values, private download keys and signed URLs remain ephemeral.
  Receipts contain only source facts, exact hashes and technical results.
- The hosted preparation keeps native bytes, performs complete decode and
  loudness checks, and records all failures without manufacturing success.
- Duplicate checks now cover delivery hashes in the unified 104-recording
  public catalogue plus native and derivative hashes retained by every public
  preview catalogue. A re-encoding cannot bypass byte-level source dedupe.
- Production, scratch, free-space and volume limits are unchanged.

## Holds and exclusions

- The twelve files from the failed revision remain explicit short/mismatched
  holds. They are neither silently replaced under old IDs nor registered by
  this revision.
- **Turbo Batido PowerMetal, ElectroMetal and BlackMetal Instrumental** remain
  short-loop reserves below the full-arrangement floor.
- **See You in Hell FREE** remains held because its current page says both that
  commercial projects require PRO and that free tracks may be used
  commercially; an older creator devlog calls the free version non-commercial.
- **Mach Overdrive** remains excluded because its source description prohibits
  standalone redistribution despite the displayed CC BY badge.
- Mini-loops, cinematics, stings, paid archives, alternate encodings and
  alternate arrangements are excluded from this distinct-composition slate.

## Source-only verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s intake -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 intake/prepare_second_directions.py --check
node verify.mjs
```

These commands fetch no audio. A fresh hosted result is required before any
candidate artifact exists, and technical success still cannot establish
musical approval.
