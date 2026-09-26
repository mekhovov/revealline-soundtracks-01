# RevealLine music archive 01

[Listen and download](https://mekhovov.github.io/revealline-soundtracks-01/)

The single-page player indexes the original 70-recording collection and every published batch. It currently exposes 155 unique recordings across 19 collections and streams only the selected SHA-256-addressed MP3. Search, style and collection filters all use the generated [catalogue.json](catalogue.json).

[archive-directory.json](archive-directory.json) is the bounded discovery contract for scale-out. It keeps this archive first and required while allowing reviewed, project-owned successor shards to be added without moving existing recording URLs or identities. The game must validate every listed catalogue independently; a directory entry cannot grant listening approval, default-playlist admission or recording rights.

The original collection preserves 354,986,122 exact MP3 bytes. Every `objects/<sha256>.mp3` file is committed for reuse. Files are free to use under their individually listed CC0, CC BY 3.0 or CC BY 4.0 licenses; retain the required attribution and change notices in [CREDITS.md](CREDITS.md) and each batch. The creators do not endorse this game.

This is a preview music archive, separate from the frozen RevealLine game release. Publication makes a recording available to the archive player and online game browser; it does not approve musical quality, grant Content ID clearance or automatically admit tracks into the game's standard playlists. UA-FPV and rejected AI recordings are excluded. No master files or duplicate album packages are stored in the Pages payload.

To publish another permitted MP3 or album, follow [UPLOAD_GUIDE.md](UPLOAD_GUIDE.md). The checked-in automation accepts one song or folder, creates an immutable batch, updates the batch index, rebuilds the public catalogue, runs verification and can open the pull request. CI refuses stale catalogue output, duplicate identities/hashes, missing credit, unsupported licences and incomplete ShareAlike delivery terms.

The [Ukrainian Commons audition](batches/ukrainian-commons-audition-20260925/)
contains three separately credited CC BY 3.0 performances whose exact hosted
derivatives and source evidence are preserved in the repository. They remain
listening-pending and outside the game's standard playlists.

## Ready-made playlist previews

The [playlist downloads](https://mekhovov.github.io/revealline-soundtracks-01/#playlist-downloads) link to 15 `.rlsound` assets in the [playlist preview prerelease](https://github.com/mekhovov/revealline-soundtracks-01/releases/tag/preview-playlists-2026-09-21). Each pack contains its credited MP3s and one playlist set to shuffle and repeat all. Short-cue packs are labelled separately. These are manual-import previews, not listening-approved or automatically installed game albums. The 70 immutable MP3 object URLs remain available individually.

Packs require **RevealLine v0.78.0 or newer**. If your game does not offer **Add album file to draft**, use the individual MP3 downloads until the new framework is available.

1. Download one pack and keep a backup of any existing music library.
2. Open **Settings → Music library & playlists**, choose the pack under **Soundtrack recovery or album file (.rlsound)**, then select **Add album file to draft → Save all changes**. **Review backup as replacement draft** is a different action that replaces the library.
3. Choose the imported playlist, select **Save & use playlist**, turn sound on and press **Play music** if paused.
4. To combine installed styles, choose **My mix**, select the genres and use **Save & use music selection**. This clears the explicit playlist selection.

Choose a subset: all 70 recordings use **338.54 MiB** of audio, exceeding the **256 MiB shared media budget** before other saved images, chapters or audio. There are also **123 custom-track slots** and **26 custom-playlist slots**. Download size includes pack metadata; the game checks actual available storage when saving. Keep the downloaded files as a backup.

Public packs retain the same audio bytes and recording IDs, with creator/source/license links and conversion notices in their metadata. Keep those credits when sharing. [CREDITS.md](CREDITS.md) also lists every recording's attribution, including the requested artist links. Open licensing does not establish Content ID clearance.

If an older preview copy is already installed, keep it and its backup: changed credits can trigger an identity conflict. Do not use replacement import just to add an album.

## Verify and deploy

Run `node intake/build-unified-catalogue.mjs --check`, then `node verify.mjs` to read and hash every public file. Run `node verify.mjs --stage public` to prepare the exact Pages payload. The GitHub Actions workflow independently verifies and publishes it on main. `deployment-manifest.json` pins public files, `inventory.json` pins every immutable original-collection MP3 object, each batch carries its own equivalent pins, `catalogue.json` joins their public playback metadata, and `archive-directory.json` declares the bounded catalogue set. Keep old object paths immutable when extending the archive.

Authoring sources: [RevealLine soundtrack PR](https://github.com/mekhovov/revealline/pull/209). Source register, authorization and inventory hashes are embedded in the catalogue and deployment manifest.
