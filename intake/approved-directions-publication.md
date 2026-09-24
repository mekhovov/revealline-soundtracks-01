# Publish the fixed twelve-recording audition artifact

The source intake is merged in PR #16. This assembler reuses its **original** successful artifact; it does not regenerate, re-encode or fetch any recording from a creator again.

- Source head: `ce8ec098b9d400f8a4b2fdba77f8dc548e09375e`.
- Original run: [36067987427](https://github.com/mekhovov/revealline-soundtracks-01/actions/runs/36067987427).
- Artifact: `10836959665`, exactly 128,698,822 bytes, ZIP SHA-256 `b632cb216cbb64db5bb08287a0e63eaebfdbf347d173f1cfe5c796c79670885c`.
- Original runner: `4c58001367033ede0f2566a572e4813426d61267`, with the same source tree `c19d3cb93ddfd3d0a947a2cb94adb86ef1f91d4f` as the intake head.
- Manifest SHA-256: `0b6ec9c6a04b90f7a283848fa064558a53df9a50a9c1858e0aa3ddf9abc4b532`.

`assemble_approved_directions.py` runs only through manual `operation: assemble` on the exact `codex/approved-directions-publication` branch. The job has read access to the artifact and write access to this review branch. It cannot run on main, create a release, deploy Pages or approve music. Normal PR events run source and archive verification without reacquiring audio. The manual `prepare` option retains the original intake workflow for separately requested future technical checks; it is not used for publication assembly.

Before writing, the assembler verifies GitHub artifact/run metadata, the original ZIP digest and byte count, safe unique member names, CRCs, every native/derivative/source-evidence hash, the exact manifest, original source-file hashes, pinned game inspector, all 81 original hosted tests, complete decode/duration/loudness receipts, pending review flags and planned volume sizes. It checks all 104 existing public identities and hashes for duplicates. The artifact is read only on the hosted runner; no local media download is needed.

The complete original artifact's members are retained byte-for-byte under `intake/archive/approved-directions-audition-20260925/hosted-artifact/`, with their original paths. Separate binding, member-hash and assembly-review documents record exactly what the assembler checked, and explicitly leave independent publication review pending. The original native files and licensed source evidence remain private to the repository's production area rather than the Pages payload.

Six synth/electro and six metal/fusion candidates become two immutable preview volumes, each below 64 MiB including metadata. Their search, playback, next, shuffle and repeat-all page reuses the earlier audited batch player and stylesheet. Credits, source filenames, source websites and licence links remain visible. Tear their fate is labelled as having creator-described vocals with lyrics and explicit-content suitability still pending.

The existing publication convention includes every batch in the root searchable player. Its count therefore becomes **116**, with the previous 104 track entries, identities, MP3 bytes and historical batches unchanged. The historical root boundary remains 70 recordings / 354,986,122 audio bytes. Only the batch index, reproducible unified catalogue and its root metadata pin change. Every new row retains `gameCatalogueAdmission: false`, `default: false`, `listeningApproval: "not-reviewed"`, `contentId: "unknown"` and `recordingModeEligible: false`. The catalogue generator preserves explicit false defaults only where present, leaving old rows unchanged.

The hosted job commits only the generated batch/retained-artifact files and those three root metadata files to the review branch after the full archive checks pass. A draft PR then receives independent review and exact-head CI. No merge or deployment is automatic. After an approved merge, the normal Pages pipeline must complete and the public MP3 lengths/hashes and actual playback must be verified. Full listening, musical fit, warnings, transitions, offline and physical-device checks are separate; publication does not complete them or admit these songs into standard game playlists.

Source-only tests use tiny in-memory ZIP and metadata fixtures. They do not pretend to decode real recordings. Original artifact inspection is performed by the hosted assembler; an independent reviewer must check its resulting evidence and publication diff before merge.
