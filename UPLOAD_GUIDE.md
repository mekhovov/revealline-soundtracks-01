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

## Upload a local MP3 or album

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
- The public catalogue may contain listening-pending auditions. Publication does not add a recording to the game’s default playlists or mark it musically approved.
- Offline installation, recovery bundles and standard-playlist admission remain separate reviewed actions.
- GitHub’s web editor has file-size limits. For larger permitted files, use Git or GitHub Desktop; the same intake command and pull-request checks apply.
