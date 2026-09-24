# Add music to the RevealLine public soundtrack catalogue

The archive is a static, reviewed GitHub Pages site. Publishing an MP3 is therefore a repository change: the exact bytes, creator credit and licence are reviewed in a pull request, then GitHub Pages deploys them. There is no anonymous browser upload endpoint and no external player embed.

Once a batch is published, `catalogue.json` exposes it to both the archive page and RevealLine’s in-game archive browser. Players stream the chosen SHA-256-addressed MP3 directly; they do not need to open this site in another tab.

## Before uploading

You need recording-specific permission for all of the following:

- public MP3 redistribution;
- playback inside a web game;
- commercial use if RevealLine may be distributed commercially;
- any adaptation you made, such as conversion or loudness processing.

A YouTube upload, a public-domain melody, or possession of an MP3 does not establish rights to redistribute that recording. The intake tool currently accepts CC0 1.0, CC BY 3.0 and CC BY 4.0. Use the exact creator/source URL and preserve the required credit. Do not upload private UA-FPV recordings until their recording-specific permissions are documented.

## Fast path: one MP3 or one folder

The automated intake command accepts one `.mp3` file or recursively discovers up to 20 MP3s in one folder. It reads title and artist from ID3 tags when available, falls back to the filename for the title, creates stable IDs, hashes and immutable object paths, generates the batch page and unified catalogue, and runs every archive verification check.

From a clean checkout, drag a file or folder into your terminal after the command and provide the shared source, licence and style tags:

```sh
node intake/add-music.mjs "/path/to/song-or-folder" \
  --source "https://creator.example/album" \
  --license cc-by-4.0 \
  --styles "metal,ukrainian,gameplay,high energy" \
  --confirm-rights
```

If MP3s do not contain an artist tag, add `--artist "Creator name"`. Optional `--batch-id`, `--batch-title` and `--description` values override the generated album details.

Add `--open-pr` to complete the Git workflow too. The command requires a clean checkout, creates a `codex/` branch when run from `main`, validates the generated archive, commits only the generated batch/catalogue files, pushes the branch and opens the pull request:

```sh
node intake/add-music.mjs "/path/to/album" \
  --artist "Creator name" \
  --source "https://creator.example/album" \
  --license cc0 \
  --styles "synth,electro,gameplay" \
  --confirm-rights \
  --open-pr
```

`--confirm-rights` is deliberately required. The script can automate file and catalogue work, but it cannot infer legal permission from an MP3, filename or website. A reviewer still checks the exact creator/source, licence and credits before merging. GitHub Pages deployment begins after the reviewed PR merges; the game reads the updated catalogue automatically.

## Advanced path: per-track metadata

Use the manifest form when songs in one folder have different artists, source pages, licences, credits or tags.

1. Create a branch from the latest `main` of `mekhovov/revealline-soundtracks-01`.
2. Create a temporary JSON manifest outside the repository. File paths may be absolute or relative to that temporary manifest:

```json
{
  "batchId": "creator-album-20260924",
  "title": "Creator — Album name",
  "description": "Licensed soundtrack intake for RevealLine.",
  "tracks": [
    {
      "id": "creator.song-id",
      "file": "/Users/me/Music/song.mp3",
      "title": "Song title",
      "artist": "Creator name",
      "source": "https://creator.example/song",
      "license": "CC BY 4.0 International",
      "licenseURL": "https://creativecommons.org/licenses/by/4.0/",
      "credit": "Song title by Creator name, licensed CC BY 4.0.",
      "tags": ["metal", "gameplay", "high energy"]
    }
  ]
}
```

3. From the repository root, run:

```sh
node intake/add-upload.mjs --manifest /absolute/path/to/upload.json
```

4. The command takes the archive writer lock, checks file and archive limits before reading audio, preserves at least 1 GiB of free disk, rejects existing IDs/hashes and writes the validated MP3 bytes to `batches/<batch-id>/objects/<sha256>.mp3`. It verifies the complete staged batch before transactionally publishing the batch, index, catalogue and root pins. A failed admission leaves the published archive unchanged; if both a commit and its rollback fail, the error names the retained recovery directory.
5. Run the same checks as CI:

```sh
node intake/build-unified-catalogue.mjs --check
node --test test-verify.mjs
node verify.mjs
```

6. Review the generated diff. Confirm every title, artist, source, licence, credit, tag, byte count and SHA-256 value.
7. Commit the generated batch and open a pull request. Do not add the temporary manifest or another copy of the source MP3.
8. Wait for the exact-head verification to pass. After review and merge, wait for the Pages deployment and verify the recording on the root page.
9. Open RevealLine, choose **Music → Online archive**, then select the new recording or **Play all**. A normal catalogue refresh is enough; no new game build is needed.

## Limits and behavior

- One batch contains 1–20 MP3 files and at most 64 MiB of audio.
- One MP3 must be smaller than 100 MB; the whole Pages archive remains below its verified 800 MB budget.
- Exact duplicate audio is rejected even when renamed.
- Folder intake is deterministic, ignores non-MP3 files, rejects symbolic links and scans no more than eight directory levels.
- The public catalogue may contain listening-pending auditions. Publication does not add a recording to the game’s default playlists or mark it musically approved.
- Offline installation, recovery bundles and standard-playlist admission remain separate reviewed actions.
- GitHub’s web editor has file-size limits. For larger permitted files, use Git or GitHub Desktop; the same intake command and pull-request checks apply.
