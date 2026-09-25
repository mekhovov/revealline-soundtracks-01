import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import test from "node:test";

const sha256 = (bytes) => createHash("sha256").update(bytes).digest("hex");

test("runner2088 keeps exact native bytes and pending rights metadata", async () => {
  const evidence = JSON.parse(
    await readFile("intake/runner2088-source-20260925.json", "utf8"),
  );
  const catalogue = JSON.parse(
    await readFile(
      "batches/synth-runner2088-audition-20260925/preview-catalogue.json",
      "utf8",
    ),
  );
  assert.equal(catalogue.tracks.length, 1);
  const track = catalogue.tracks[0];
  assert.equal(track.id, "wekont.runner2088");
  assert.equal(track.source, evidence.source);
  assert.equal(track.licenseURL, evidence.licenseURL);
  assert.equal(track.sha256, evidence.nativeSha256);
  assert.equal(track.bytes, evidence.nativeBytes);
  assert.equal(track.contentId, "unknown");
  assert.equal(track.recordingModeEligible, false);
  assert.equal(catalogue.listeningApproval, "not-reviewed");
  assert.equal(catalogue.gameCatalogueAdmission, false);
  const bytes = await readFile(
    `batches/synth-runner2088-audition-20260925/${track.path}`,
  );
  assert.equal(bytes.length, evidence.nativeBytes);
  assert.equal(sha256(bytes), evidence.nativeSha256);
  assert.equal(evidence.changeNotice, "No audio changes; exact creator-published MP3 bytes retained.");
  assert.equal(evidence.listeningApproval, false);
  assert.equal(evidence.gameCatalogueAdmission, false);
  assert.equal(evidence.defaultPlaylist, false);
});
