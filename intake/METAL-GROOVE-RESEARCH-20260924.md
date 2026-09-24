# Four-track metal groove intake research

The user considers the existing David KBD Eternity auditions worth keeping, but
wants stronger rhythmic drive and energy. This is a separate additive audition
slate. All four source titles were absent from the 96 archive catalogue entries
during the read-only check. Exact audio/hash deduplication and musical review
remain pending; no MP3 was acquired for this source PR.

## Exact creator evidence

On 24 September 2026, live HTTPS HTML inspection found these exact filenames in
each page's primary `div#mainTrack`, with matching `data-title` and `data-src`.
All four MP3s use the existing approved prefix
`https://d19p7hqu4j8vx0.cloudfront.net/media/media/data/mp3s/`.
The pages also link unrelated recommended songs, so intake now checks the primary
player for these four recordings rather than accepting any matching page link.

| Creator page / audition | Primary MP3 filename | Observed HTML SHA-256 |
| --- | --- | --- |
| [Anemo](https://creatorchords.com/music/anemo/) | `Anemo.mp3` | `701cb12e8a8dd4b0353d7848fad99194ff81a6f51560388c96ceb7ee242c1c19` |
| [Trial of Thorns](https://creatorchords.com/music/trial-of-thorns/) | `Trial_of_Thorns.mp3` | `fae598a74cbacb16bcd7f502f54e0d2d00ea3691dcfd9ff2177d0470f2077aa2` |
| [Riffs Two](https://creatorchords.com/music/riffs-two/) | `Riffs_Two.mp3` | `005a363691bcd6a3d5cab67a3fdd0d20b25e7dc6e12c4a9b58be6b206e513b85` |
| [Apocalypse](https://creatorchords.com/music/apocalypse/) | `Apocalypse.mp3` | `2871dbf6406f088a326a8b0b4a1aa7e3098d9dc924d56ecb08f1bdf48f8703ff` |

The observed HTML hashes identify this inspection only. Dynamic recommendations
can change page bytes; they are not permanent page pins. Hosted intake saves
fresh, exact source/licensing/FAQ bytes and hashes, checks the bound primary
recording and licence evidence, then acquires the exact allowlisted MP3.

Each exact track page offers free use with attribution under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). This permits commercial
game use and public redistribution with appropriate creator/source/licence
credits and modification notices. Do not rename the creator as RevealLine.
The manifest retains the creator's attribution text, with normalization changes
recorded separately by the existing preparation tool.

The [licensing page](https://creatorchords.com/licensing-info/) explicitly states
Smart Content ID registration. Its observed HTML SHA-256 was
`0ca324666025bd00e49f9659867d2d2f648f15af37cd53a113b6afda325e9ec6`.
The [FAQ](https://creatorchords.com/faq/) documents credit requirements and claims;
its observed hash was
`6252c7fa101d7d6bb5340203ddfb1c8a60a17e27e1eef97c9627108f0801a1aa`.
No claim-free assurance is made. All four rows remain `contentId: true` and
`recordingModeEligible: false`; changed licensing/Content ID evidence aborts
preparation for review.

## Musical research, not acceptance

| Recording | Creator-published length / BPM | Creator-published style |
| --- | --- | --- |
| Anemo | 4:38 / 131 | Metal, rock, industrial |
| Trial of Thorns | 3:57 / 133 | Metal, death metal, industrial |
| Riffs Two | 3:18 / 159 | Metal, thrash metal, progressive |
| Apocalypse | 3:37 / 145 | Metal, thrash metal, rock |

These are full-length audition leads rather than short boss cues. The priority
for Anemo and Trial of Thorns is an inference from their industrial metadata,
not a claim that a reviewer has heard stronger bass/kick coordination. BPM alone
does not prove energy or suitability. Review complete tracks for clear recurring
riffs, synchronized bass/kick attacks, rhythmic rests, developed returns and
sustained gameplay momentum before admission. Check actual warning audibility
and transitions in the game separately.

No Ukrainian classification, instrumental verification, full-track listening,
gameplay review or publication approval is granted. Preserve The Dobermann,
Folklore, all four David KBD auditions and the earlier six-track metal backups.

## Execution boundary

The existing workflow files are unchanged. A branch push does not run either
intake workflow, so independent review must finish before the PR is opened.
Opening that PR runs the existing core workflow against the active four-track
manifest and also runs the separate Shchedryk intake because both watch
`prepare.py`. This acquisition behavior is explicit, not source-only CI.
The reviewed head and actual workflow/merge checkout must both be bound to the
artifact before later publication; the existing workflow does not add a new
reviewed-head input.

The named four-track manifest and active core copy are byte-identical, with an
exact-hash regression. Historical manifests remain unchanged. Intake preserves
all source, derivative, production, scratch, volume and free-space guards, the
pinned game MP3 inspector, native originals and partial failures. No acquisition
has run at this branch-preparation stage. Publication and game admission need
separate review.

The uninstalled manual-only workflow proposal and authorization failures are
preserved under `workflow-proposals/metal-groove-20260924/`; they have no effect
on the active workflows.

[Source verification evidence](verification/metal-groove-intake-20260924.json)
records 55 in-memory test passes and the three filesystem tests deferred to CI.
The two primary-player regressions fail when that guard is deliberately removed.
Independent source review and all hosted acquisition/recording checks remain pending.
