# RevealLine music archive 01

[Listen and download](https://mekhovov.github.io/revealline-soundtracks-01/)

70 creator recordings, 354,986,122 exact MP3 bytes. Every objects/<sha256>.mp3 file is committed for reuse. Files are free to use under their individually listed CC0, CC BY 3.0 or CC BY 4.0 licenses; retain the required attribution and change notices in [CREDITS.md](CREDITS.md). The creators do not endorse this game.

This is a preview music archive, separate from the frozen RevealLine game release. It does not approve musical quality, grant Content ID clearance or automatically admit tracks into the game's trusted catalogue. UA-FPV and rejected AI recordings are excluded. No master files or duplicate album packages are included.

## Verify and deploy

Run `node verify.mjs` to read and hash every public file. Run `node verify.mjs --stage public` to prepare the exact Pages payload. The GitHub Actions workflow independently verifies and publishes it on main. `deployment-manifest.json` pins public files, `inventory.json` pins every immutable MP3 object, and `preview-catalogue.json` maps recordings to creator/source/license/conversion metadata. Keep old object paths immutable when extending the archive.

Authoring sources: [RevealLine soundtrack PR](https://github.com/mekhovov/revealline/pull/209). Source register, authorization and inventory hashes are embedded in the catalogue and deployment manifest.
