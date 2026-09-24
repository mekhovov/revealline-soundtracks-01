# Core soundtrack expansion intake

This directory prepares separate candidate batches without changing the existing
96 published archive recordings or any immutable inventory. It is excluded from
Pages staging. The game does not discover or admit these candidates.

The active `core-20260924.json` is now byte-identical to
`metal-groove-audition-20260924.json`: four Alexander Nakarada recordings,
**Anemo, Trial of Thorns, Riffs Two and Apocalypse**. Each exact creator page
offers CC BY 4.0 and each recording remains excluded from Recording mode because
the creator reports Content ID registration. Source pages include unrelated
recommendations, so these rows require a unique, matching primary player.

The preceding ten-track itch manifest is retained unchanged both at
`itch-core-audition-20260924.json` and
`archive/itch-core-audition-20260924/source-manifest.json` (SHA-256
`02a28c838d2f68b2a22ef29b6e432deebfe772e5f86bc1614b73839dceaa89f9`).
The first thirteen-track manifest remains in
`archive/core-20260924/source-manifest.json`. Neither historical batch is
replaced or re-approved by changing the active intake.

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

## Review before opening the four-track pull request

No workflow files change for this batch. The existing core workflow runs on
matching pull requests or manual dispatch; it does not run for a branch push.
Review the exact branch commit **before opening the PR**. Opening or updating
a matching PR then runs tests and acquires the four-track active core manifest
into `candidate-output/`, preserving `core-soundtrack-candidates` as its
30-day artifact. It does not merely validate source.

The shared `prepare.py` change also matches the existing Ukrainian workflow:
the same PR will reacquire the already-published Shchedryk candidate into its
separate artifact. This does not replace its published bytes or renew musical
approval. Preserve the new receipt and any failure evidence separately.

The earlier manual-only workflow proposal could not be installed with the
available GitHub authorization. Its exact, uninstalled files and verification
are retained under
[`workflow-proposals/metal-groove-20260924/`](workflow-proposals/metal-groove-20260924/).
They are not active GitHub workflows and are not instructions to bypass permissions.

The current 650 MiB production, 256 MiB scratch and 1 GiB free-space limits remain
unchanged. Each new native source is capped at 16 MiB, each derivative at 24 MiB,
and delivery volumes retain the 64 MiB limit with metadata reserve. Native
originals and source/licensing/FAQ snapshots stay in the acquisition artifact.
Archive them before expiry. Actual duration, decoding, loudness, exact-hash
deduplication, complete listening and later public/game admission remain pending.
