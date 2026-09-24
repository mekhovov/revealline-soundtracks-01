# Second synth/electro and rhythmic-metal audition intake

This source-only intake prepares twelve additional recordings after the first approved-direction slate. It does not publish audio, approve listening, admit a recording into the game, alter defaults, or make a track Recording-mode eligible. No audio was downloaded locally while preparing it.

All four exact itch source pages currently state **CC BY 4.0 International** and expose the selected OGG uploads through a zero-price public acquisition route. CC BY 4.0 permits copying and redistribution, including commercially, when attribution, the licence link, and modification notice are preserved. Cover artwork is outside this intake and must not be reused from the source pages without separate permission.

## Exact slate

| Recording | Exact free upload | Game / upload ID | Published album duration |
| --- | --- | --- | --- |
| Pink Bloom | `DavidKBD - Pink Bloom Pack - 01 - Pink Bloom.ogg` | 1635239 / 6233745 | 4:46 |
| To the Unknown | `DavidKBD - Pink Bloom Pack - 03 - To the Unknown.ogg` | 1635239 / 6233747 | 5:29 |
| Lightyear City | `DavidKBD - Pink Bloom Pack - 09 - Lightyear City.ogg` | 1635239 / 6233753 | 4:51 |
| HexaPuppies | `DavidKBD - HexaPuppies Pack - 01 - HexaPuppies.ogg` | 1020992 / 3749483 | 4:30 |
| The Great Machine | `DavidKBD - HexaPuppies Pack - 07 - The Great Machine - variation1.ogg` | 1020992 / 3749499 | 4:18 |
| Disaster | `DavidKBD - HexaPuppies Pack - 09 - Disaster - variation1.ogg` | 1020992 / 3749505 | 4:42 |
| Keep My Rhythm, If You Can | `DavidKBD - Reckless Punk-Metal Pack - 03 - Keep My Rhythm, If You Can.ogg` | 974022 / 12030737 | 4:01 |
| Dangerous and Bored | `DavidKBD - Reckless Punk-Metal Pack - 05 - Dangerous and Bored.ogg` | 974022 / 12030736 | 5:23 |
| Speedy and Hostile | `DavidKBD - Reckless Punk-Metal Pack - 10 - Speedy and Hostile.ogg` | 974022 / 12030742 | 3:47 |
| Purgatory | `01 - DavidKBD - Purgatory Pack - Purgatory.ogg` | 1498789 / 11733688 | 3:09 |
| On Fire | `06 - DavidKBD - Purgatory Pack - On Fire.ogg` | 1498789 / 11733968 | 3:05 |
| Hades | `07 - DavidKBD - Purgatory Pack - Hades.ogg` | 1498789 / 11733694 | 3:27 |

The duration values come from David KBD's official album distributions and describe the named compositions. The hosted workflow must measure each exact free OGG; no duration is inferred from its filename or byte size, and this batch rejects an exact recording shorter than three minutes. Only variation 1 of The Great Machine and Disaster is registered, so alternate arrangements do not inflate the composition count.

Sources: [Pink Bloom](https://davidkbd.itch.io/pink-bloom-synthwave-music-pack), [HexaPuppies](https://davidkbd.itch.io/hexapuppies-synthwave-music-pack), [Reckless](https://davidkbd.itch.io/reckless-punk-metal-music-pack), and [Purgatory](https://davidkbd.itch.io/purgatory-extreme-metal-music-pack).

The synth half is a listening hypothesis for fuller synthwave, moving bass, layered leads and electronic drums. The metal half emphasizes the user's approved punk-metal and extreme-metal direction. Exact vocal content, explicit content, Content ID, game balance, full-track structure and musical fit remain pending. Every recording therefore keeps `contentId: "unknown"`, `recordingModeEligible: false`, and all approval flags false.

## Fail-closed hosted preparation

- The complete manifest is SHA-256 bound before network access and local acquisition is refused.
- Each source is bound to the exact origin, slug, game ID, normalized creator-description digest, CC BY badge, direct licence link, upload ID and visible filename.
- The anonymous route must remain free. A purchase requirement, account handoff, external media URL, changed description, changed terms, alternate upload, cross-paired response or redirect stops intake.
- Cookies, CSRF values, download-page keys and signed CDN URLs remain ephemeral. Safe evidence retains semantic licence facts, exact source/upload identity, native hash, decoder facts, measured duration and processing results.
- Native acquisition and FFmpeg validation run only in the `Prepare second-direction audition candidates` workflow. Its artifact is `second-directions-audition-candidates`; it is review material rather than a public collection.
- Existing public inventory verification runs first. The shared production, scratch, free-space and per-volume limits remain unchanged.

## Reserves and exclusions

- **Turbo Batido — Ingame PowerMetal, ElectroMetal and BlackMetal Instrumental** remain short-loop reserves. The page is CC BY 4.0 and publicly free, but it documents them as loops and publishes no exact duration. None is registered in this full-track slate.
- **See You in Hell FREE** is held. Its current page says commercial projects require PRO and also says its free tracks may be used commercially, while its earlier creator devlog describes the free version as non-commercial. The exact README must resolve that conflict before acquisition. The $6 PRO pack separately states CC BY 4.0, but it is not a free intake source.
- **Mach Overdrive** is excluded from the public standalone archive because its current description expressly prohibits redistribution or resale of standalone audio despite displaying a CC BY badge.
- Mini-loops, cinematics, victory/failure stings, paid WAV archives, alternate encodings and other variants are not registered.

## Source-only verification

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s intake -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 intake/prepare_second_directions.py --check
node verify.mjs
```

These checks fetch no audio. Hosted technical success still cannot establish listening approval or suitability for RevealLine.
