# Add music to the RevealLine public soundtrack catalogue

The archive is a static, reviewed GitHub Pages site. Publishing an MP3 is therefore a repository change: the exact bytes, creator credit and licence are reviewed in a pull request, then GitHub Pages deploys them. There is no anonymous browser upload endpoint and no external player embed.

Once a batch is published, `catalogue.json` exposes it to both the archive page and RevealLine’s in-game archive browser. Players stream the chosen SHA-256-addressed MP3 directly; they do not need to open this site in another tab.

## Before uploading

You need recording-specific permission for all of the following:

- public MP3 redistribution;
- playback inside a web game;
- commercial use if RevealLine may be distributed commercially;
- any adaptation you made, such as conversion or loudness processing.

A YouTube upload, a public-domain melody, or possession of an MP3 does not establish rights to redistribute that recording. The intake tool accepts CC0 1.0, CC BY 3.0/4.0 and CC BY-SA 3.0/4.0. Use the exact creator/source URL and preserve the required credit. Do not upload private UA-FPV recordings until their recording-specific permissions are documented.

CC BY-SA requires more than a licence label. Preserve the exact page that proves the recording's licence, disclose conversion, normalization or other changes, and distribute the MP3 derivative under the reviewed compatible ShareAlike licence. The archive conservatively excludes ShareAlike recordings from Recording mode. This metadata records obligations; it does not establish that an unrelated source file is licensed correctly.

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

If MP3s do not contain an artist tag, add `--artist "Creator name"`. For one MP3,
`--title "Exact song title"` overrides an absent or machine-oriented ID3/filename
title. The tool rejects `--title` for folders because one value cannot accurately
name several recordings. Optional `--batch-id`, `--batch-title` and `--description`
values override the generated album details.

```sh
node intake/add-music.mjs "/path/to/maximum_overdrive.mp3" \
  --title "Maximum Overdrive" \
  --artist "Bogart VGM" \
  --source "https://opengameart.org/content/maximum-overdrive" \
  --license cc-by-3.0 \
  --styles "synthwave,racing,gameplay" \
  --confirm-rights
```

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

For CC BY-SA, also pass the exact rights-evidence URL and a truthful derivative notice. If the submitted MP3 is the creator's exact file, say so. If it was converted, name the source format and every material processing step:

```sh
node intake/add-music.mjs "/path/to/sharealike-song.mp3" \
  --artist "Creator name" \
  --source "https://creator.example/song" \
  --license cc-by-sa-4.0 \
  --rights-evidence "https://creator.example/song#license" \
  --derivative-notice "Converted from WAV to 256 kbps MP3; loudness normalized." \
  --styles "ukrainian,gameplay" \
  --confirm-rights
```

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
      "rights": {
        "licenseId": "CC-BY",
        "licenseVersion": "4.0",
        "licenseURL": "https://creativecommons.org/licenses/by/4.0/",
        "rightsEvidenceURL": "https://creator.example/song#license",
        "attribution": "Song title by Creator name, licensed CC BY 4.0.",
        "derivativeChangeNotice": "Exact submitted MP3 bytes retained; no archive changes declared.",
        "shareAlike": {
          "required": false,
          "deliveryLicenseId": null,
          "deliveryLicenseVersion": null,
          "deliveryLicenseURL": null
        }
      },
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
   For CC BY-SA, also confirm the exact licence identity/version, rights-evidence URL, attribution, derivative change notice and matching ShareAlike delivery licence. A CC BY-SA row cannot be represented as CC BY or marked Recording-mode-safe.
7. Commit the generated batch and open a pull request. Do not add the temporary manifest or another copy of the source MP3.
8. Wait for the exact-head verification to pass. After review and merge, wait for the Pages deployment and verify the recording on the root page.
9. Open RevealLine, choose **Music → Online archive**, then select the new recording or **Play all**. A normal catalogue refresh is enough; no new game build is needed.

## Limits and behavior

- One batch contains 1–20 MP3 files and at most 64 MiB of audio.
- One MP3 must be smaller than 100 MB; the whole Pages archive remains below its verified 900 MB budget. This leaves 100 MB of headroom below [GitHub Pages' documented 1 GB published-site limit](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits). Start a new archive shard before reaching the 900 MB guard.
- Exact duplicate audio is rejected even when renamed.
- Folder intake is deterministic, ignores non-MP3 files, rejects symbolic links and scans no more than eight directory levels.
- The public catalogue may contain listening-pending auditions. Publication does not add a recording to the game’s default playlists or mark it musically approved.
- Offline installation, recovery bundles and standard-playlist admission remain separate reviewed actions.
- GitHub’s web editor has file-size limits. For larger permitted files, use Git or GitHub Desktop; the same intake command and pull-request checks apply.
