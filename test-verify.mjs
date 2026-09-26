import test from "node:test";
import assert from "node:assert/strict";
import {
  mkdir,
  mkdtemp,
  open,
  readFile,
  readdir,
  rename,
  writeFile,
  rm,
  symlink,
} from "node:fs/promises";
import { createHash } from "node:crypto";
import path from "node:path";
import os from "node:os";
import { fileURLToPath } from "node:url";
import {
  validateDeclarations,
  validateBatchDeclarations,
  validateBatchIndex,
  validateArchiveDirectory,
  verifyPreviewBatch,
  appendVerifiedPreviewBatch,
} from "./verify.mjs";
import {
  buildUnifiedCatalogue,
  serializeCatalogue,
} from "./intake/build-unified-catalogue.mjs";
import {
  commitTransaction,
  prepareUpload,
  validateUploadManifest,
} from "./intake/add-upload.mjs";
import {
  STYLE_GROUPS,
  buildPlaybackQueue,
  matchesStyles,
  stylesOf,
} from './playback-policy.mjs';
import { createUploadManifest, readID3 } from './intake/add-music.mjs';
import {
  allowsLegacyRightsArchive,
  createRightsMetadata,
  validateRecordingRights,
} from './rights-policy.mjs';

const source = fileURLToPath(new URL("./", import.meta.url));
const baseURL = "https://mekhovov.github.io/revealline-soundtracks-01/";
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const asPin = (file, bytes) => ({
  path: file,
  bytes: bytes.length,
  sha256: hash(bytes),
});
const json = (value) => Buffer.from(JSON.stringify(value));
async function fixture(t) {
  const root = await mkdtemp(
    path.join(os.tmpdir(), "soundtrack-preview-batch-"),
  );
  t.after(() => rm(root, { recursive: true, force: true }));
  const id = "core-fixture";
  // Byte-verifier fixture only: this is not a recording or listening approval.
  const audio = Buffer.from("synthetic audio bytes");
  const object = asPin(`objects/${hash(audio)}.mp3`, audio);
  const inventory = {
    format: "revealline-soundtrack-archive.v1",
    id,
    files: [object],
  };
  const catalogue = {
    format: "revealline-licensed-preview-catalogue.v1",
    status: "licensed-preview",
    gameCatalogueAdmission: false,
    listeningApproval: "not-reviewed",
    archive: {
      id,
      baseURL: `${baseURL}batches/${id}/`,
      inventorySha256: hash(json(inventory)),
    },
    tracks: [
      {
        id: "synthetic.fixture",
        ...object,
        title: "Synthetic fixture",
        artist: "Fixture only",
        source: "https://example.com/fixture",
        license: "CC0 1.0 Universal",
        licenseURL: "https://creativecommons.org/publicdomain/zero/1.0/",
        credit: "Synthetic test data, not a licensed recording.",
        rights: createRightsMetadata({
          licenseURL: "https://creativecommons.org/publicdomain/zero/1.0/",
          rightsEvidenceURL: "https://example.com/fixture#rights",
          attribution: "Synthetic test data, not a licensed recording.",
          derivativeChangeNotice: "Synthetic fixture bytes; no real recording.",
        }),
        recordingModeEligible: false,
      },
    ],
  };
  const files = new Map([
    [".nojekyll", Buffer.alloc(0)],
    ["index.html", Buffer.from("<p>Listening pending</p>")],
    ["style.css", Buffer.from("body {}")],
    ["player.mjs", Buffer.from("// Synthetic preview fixture")],
    ["README.md", Buffer.from("Synthetic listening-pending preview")],
    ["CREDITS.md", Buffer.from("Synthetic test attribution")],
    ["inventory.json", json(inventory)],
    ["preview-catalogue.json", json(catalogue)],
    [object.path, audio],
  ]);
  const manifest = {
    format: "revealline-soundtrack-preview-deployment.v1",
    id,
    expected: { trackCount: 1, audioBytes: audio.length },
    files: [...files].map(([name, body]) => asPin(name, body)),
    provenance: { fixture: true },
  };
  files.set("deployment-manifest.json", json(manifest));
  for (const [name, body] of files) {
    await mkdir(path.dirname(path.join(root, name)), { recursive: true });
    await writeFile(path.join(root, name), body);
  }
  const declaration = {
    id,
    manifest: asPin(`batches/${id}/deployment-manifest.json`, json(manifest)),
  };
  return {
    root,
    id,
    inventory,
    catalogue,
    manifest,
    declaration,
    files,
    object,
  };
}
test("root manifest preserves the original70 audio boundary and pins the current public shell", async () => {
  const body = await readFile(path.join(source, "deployment-manifest.json"));
  const manifest = JSON.parse(body),
    inventory = JSON.parse(await readFile(path.join(source, "inventory.json"))),
    catalogue = JSON.parse(
      await readFile(path.join(source, "preview-catalogue.json")),
    );
  const result = validateDeclarations(manifest, inventory, catalogue);
  assert.equal(result.trackCount, 70);
  assert.equal(result.audioBytes, 354986122);
  const objectPins = manifest.files.filter((file) =>
    file.path.startsWith("objects/"),
  );
  assert.equal(
    hash(Buffer.from(JSON.stringify(objectPins))),
    "21827d6b6d1ffd8193c0aac0929ae19e4f0f13ebf0c7934ac2fec10cf156c1d2",
  );
  for (const entry of manifest.files.filter(
    (file) => !file.path.startsWith("objects/"),
  )) {
    const actual = await readFile(path.join(source, entry.path));
    assert.equal(actual.length, entry.bytes);
    assert.equal(hash(actual), entry.sha256);
  }
  manifest.expected.trackCount = 71;
  assert.throws(
    () => validateDeclarations(manifest, inventory, catalogue),
    /pinned/,
  );
});
test("unified catalogue reproducibly exposes every published batch on the root page", async () => {
  const generated = await buildUnifiedCatalogue();
  const committed = await readFile(path.join(source, "catalogue.json"), "utf8");
  assert.equal(committed, serializeCatalogue(generated));
  assert.equal(
    generated.counts.declaredTracks,
    generated.sources.reduce((sum, item) => sum + item.declaredTracks, 0),
  );
  assert.equal(generated.counts.uniqueRecordings, generated.tracks.length);
  assert.equal(
    generated.counts.duplicateAliases,
    generated.counts.declaredTracks - generated.tracks.length,
  );
  assert.equal(
    generated.counts.audioBytes,
    generated.tracks.reduce((sum, item) => sum + item.audio.bytes, 0),
  );
  for (const title of [
    "Revenge's Waiting",
    "Pixel Damnation",
    "Anemo",
    "Trial of Thorns",
    "Carol of the Bells (Metal Version)",
  ])
    assert(
      generated.tracks.some((track) => track.title === title),
      `Missing ${title}`,
    );
  const shchedryk = generated.tracks.find(
    (track) => track.title === "Carol of the Bells (Metal Version)",
  );
  assert.equal(shchedryk.contentId, true);
  assert.equal(shchedryk.recordingModeEligible, false);
  assert(shchedryk.tags.some((tag) => /metal/i.test(tag)));
  assert(shchedryk.tags.some((tag) => /ukrain/i.test(tag)));
});
test("Ukrainian Commons publication is exactly bound to its hosted artifact and remains audition-only", async () => {
  const batchId = "ukrainian-commons-audition-20260925";
  const archiveRoot = path.join(source, "intake", "archive", batchId);
  const publicRoot = path.join(source, "batches", batchId);
  const binding = JSON.parse(
    await readFile(path.join(archiveRoot, "artifact-binding.json"), "utf8"),
  );
  const members = JSON.parse(
    await readFile(
      path.join(archiveRoot, "artifact-member-hashes.json"),
      "utf8",
    ),
  );
  const assembly = JSON.parse(
    await readFile(path.join(archiveRoot, "assembly-review.json"), "utf8"),
  );
  const receipt = await readFile(
    path.join(archiveRoot, "hosted-artifact", "receipt.json"),
  );
  const review = await readFile(
    path.join(archiveRoot, "hosted-artifact", "review.json"),
  );
  const catalogue = JSON.parse(
    await readFile(path.join(publicRoot, "preview-catalogue.json"), "utf8"),
  );
  const declarations = JSON.parse(
    await readFile(path.join(source, "batches.json"), "utf8"),
  );
  const declaration = declarations.batches.find((entry) => entry.id === batchId);

  assert.deepEqual(
    {
      workflowRun: binding.workflowRun,
      artifactId: binding.artifactId,
      artifactName: binding.artifactName,
      sourceManifestSha256: binding.sourceManifestSha256,
    },
    {
      workflowRun: 36067125672,
      artifactId: 10836663291,
      artifactName: "ukrainian-commons-audition-candidates",
      sourceManifestSha256:
        "99bc4dc890a1d2c28c222e3ae32eefa5b47f2bcd3750346ab7dba5bf9839e463",
    },
  );
  assert.equal(hash(receipt), binding.receiptSha256);
  assert.equal(hash(review), binding.reviewSha256);

  const memberByPath = new Map(
    members.members.map((member) => [member.path, member]),
  );
  for (const member of members.members.filter(
    ({ path: memberPath }) =>
      memberPath === "receipt.json" ||
      memberPath === "review.json" ||
      memberPath.startsWith("evidence/"),
  )) {
    const body = await readFile(
      path.join(archiveRoot, "hosted-artifact", member.path),
    );
    assert.equal(body.length, member.bytes);
    assert.equal(hash(body), member.sha256);
  }

  const expected = new Map(
    assembly.tracks.map((track) => [track.id, track]),
  );
  assert.equal(expected.size, 3);
  assert.equal(catalogue.listeningApproval, "not-reviewed");
  assert.equal(catalogue.gameCatalogueAdmission, false);
  for (const track of catalogue.tracks) {
    const reviewed = expected.get(track.id);
    assert(reviewed, `Unexpected Ukrainian Commons track ${track.id}`);
    assert.equal(track.sha256, reviewed.deliverySha256);
    assert.equal(track.bytes, reviewed.deliveryBytes);
    assert.equal(reviewed.completeDecode, true);
    assert.equal(reviewed.listeningApproval, false);
    assert.equal(reviewed.culturalReview, "pending");
    assert.equal(reviewed.gameplayReview, "pending");
    assert.equal(track.contentId, "unknown");
    assert.equal(track.recordingModeEligible, false);
    assert.equal(track.rights.licenseId, "CC-BY");
    assert.equal(track.rights.licenseVersion, "3.0");
    assert.equal(
      track.rights.licenseURL,
      "https://creativecommons.org/licenses/by/3.0/",
    );
    assert.match(
      track.rights.rightsEvidenceURL,
      /^https:\/\/commons\.wikimedia\.org\//,
    );
    const artifactObject = memberByPath.get(`objects/${track.sha256}.mp3`);
    assert.equal(artifactObject?.bytes, track.bytes);
    const publicObject = await readFile(path.join(publicRoot, track.path));
    assert.equal(hash(publicObject), track.sha256);
  }
  assert.equal(assembly.publicationState, "rights-cleared-audition-only");
  assert.equal(assembly.gameCatalogueAdmission, false);
  assert.equal(assembly.recordingModeEligible, false);
  assert(declaration, "Missing Ukrainian Commons batch declaration");
  const verified = await verifyPreviewBatch(publicRoot, {
    ...declaration,
    baseURL,
  });
  assert.equal(verified.trackCount, 3);
  assert.equal(verified.audioBytes, 13190922);
});
test('archive directory is bounded, exact and keeps the primary catalogue first', async () => {
  const directory = JSON.parse(
    await readFile(path.join(source, 'archive-directory.json'), 'utf8'),
  );
  assert.equal(validateArchiveDirectory(directory).length, 1);
  assert.equal(
    validateArchiveDirectory({
      ...directory,
      catalogues: [
        ...directory.catalogues,
        {
          id: 'revealline-soundtracks-02',
          url: 'https://mekhovov.github.io/revealline-soundtracks-02/catalogue.json',
          baseURL: 'https://mekhovov.github.io/revealline-soundtracks-02/',
          required: false,
        },
      ],
    }).length,
    2,
  );
  assert.throws(
    () =>
      validateArchiveDirectory({
        ...directory,
        catalogues: [
          ...directory.catalogues,
          {
            id: 'revealline-soundtracks-02',
            url: 'https://attacker.example/catalogue.json',
            baseURL: 'https://attacker.example/',
            required: false,
          },
        ],
      }),
    /directory entry/,
  );
  assert.throws(
    () =>
      validateArchiveDirectory({
        ...directory,
        catalogues: [{ ...directory.catalogues[0], required: false }],
      }),
    /primary soundtrack archive/,
  );
});
test('style selection supports mixed families and deterministic ordered or shuffled queues', () => {
  assert.deepEqual(stylesOf({ tags: ['Ukrainian', 'metal', 'synthwave'] }), [
    'ukrainian',
    'metal',
    'synth',
  ]);
  assert.equal(matchesStyles(['metal'], ['metal', 'ukrainian']), true);
  assert.equal(matchesStyles(['ambient'], ['metal', 'ukrainian']), false);
  assert.equal(matchesStyles(['metal'], []), false);
  const rows = ['a', 'b', 'c'];
  assert.deepEqual(
    buildPlaybackQueue(rows, { order: 'ordered', current: 'b', wrap: true }),
    ['c', 'a', 'b'],
  );
  assert.deepEqual(
    buildPlaybackQueue(rows, { order: 'ordered', current: 'b', wrap: false }),
    ['c'],
  );
  assert.deepEqual(
    buildPlaybackQueue(rows, { order: 'shuffle', current: 'a', random: () => 0 }),
    ['b', 'c', 'a'],
  );
  assert.equal(STYLE_GROUPS.length, 7);
});
test('root player exposes multi-style, queue-order and repeat controls', async () => {
  const html = await readFile(path.join(source, 'index.html'), 'utf8');
  const player = await readFile(path.join(source, 'player.mjs'), 'utf8');
  for (const id of ['styles', 'styles-all', 'styles-none', 'order', 'repeat'])
    assert.match(html, new RegExp(`id=["']${id}["']`));
  assert.match(player, /matchesStyles/);
  assert.match(player, /natural && repeat\.value === 'one'/);
});
test("local MP3 intake requires exact public credit and supported redistribution rights", () => {
  const valid = {
    batchId: "creator-album-20260924",
    title: "Creator — Album",
    description: "A reviewed public upload.",
    tracks: [
      {
        id: "creator.song",
        file: "/tmp/song.mp3",
        title: "Song",
        artist: "Creator",
        source: "https://creator.example/song",
        license: "CC BY 4.0 International",
        licenseURL: "https://creativecommons.org/licenses/by/4.0/",
        credit: "Song by Creator, CC BY 4.0.",
        tags: ["metal", "gameplay"],
      },
    ],
  };
  const normalized = validateUploadManifest(valid);
  assert.equal(normalized.tracks[0].rights.licenseId, 'CC-BY');
  assert.equal(normalized.tracks[0].rights.licenseVersion, '4.0');
  assert.equal(normalized.tracks[0].rights.shareAlike.required, false);
  assert.equal(normalized.tracks[0].recordingModeEligible, false);
  for (const changed of [
    {
      tracks: [
        { ...valid.tracks[0], licenseURL: "https://example.com/custom" },
      ],
    },
    { tracks: [valid.tracks[0], valid.tracks[0]] },
    { tracks: [{ ...valid.tracks[0], source: "file:///tmp/song" }] },
  ])
    assert.throws(() => validateUploadManifest({ ...valid, ...changed }));
});
test('CC BY-SA intake binds exact rights, changes and compatible delivery terms', () => {
  const credit = 'ShareAlike Song by Creator. CC BY-SA 4.0 International.';
  const rights = createRightsMetadata({
    licenseURL: 'https://creativecommons.org/licenses/by-sa/4.0/',
    rightsEvidenceURL: 'https://creator.example/sharealike-song#license',
    attribution: credit,
    derivativeChangeNotice: 'Converted from WAV to 256 kbps MP3; audio content unchanged.',
  });
  const track = {
    license: 'CC BY-SA 4.0 International',
    licenseURL: 'https://creativecommons.org/licenses/by-sa/4.0/',
    credit,
    rights,
    recordingModeEligible: false,
  };
  assert.equal(validateRecordingRights(track), rights);
  assert.deepEqual(rights.shareAlike, {
    required: true,
    deliveryLicenseId: 'CC-BY-SA',
    deliveryLicenseVersion: '4.0',
    deliveryLicenseURL: 'https://creativecommons.org/licenses/by-sa/4.0/',
  });
  for (const changed of [
    { ...track, license: 'CC BY 4.0 International' },
    { ...track, recordingModeEligible: true },
    { ...track, rights: { ...rights, licenseId: 'CC-BY' } },
    {
      ...track,
      rights: {
        ...rights,
        shareAlike: { ...rights.shareAlike, deliveryLicenseURL: null },
      },
    },
    { ...track, rights: undefined },
  ])
    assert.throws(() => validateRecordingRights(changed, { allowLegacy: true }));
});
test('legacy rights compatibility still validates exact licence labels and trusted archives', () => {
  const legacy = {
    license: 'CC BY 4.0 International',
    licenseURL: 'https://creativecommons.org/licenses/by/4.0/',
    credit: 'Legacy credit.',
    recordingModeEligible: false,
  };
  assert.equal(validateRecordingRights(legacy, { allowLegacy: true }), null);
  assert.throws(() =>
    validateRecordingRights({ ...legacy, license: undefined }, { allowLegacy: true }),
  );
  assert.throws(() =>
    validateRecordingRights(
      { ...legacy, license: 'CC0 1.0 Universal' },
      { allowLegacy: true },
    ),
  );
  assert.equal(allowsLegacyRightsArchive('licensed-preview-01'), true);
  assert.equal(allowsLegacyRightsArchive('core-fixture'), false);
});
test('folder automation refuses implicit ShareAlike terms and records an MP3 notice', async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'soundtrack-sharealike-intake-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const file = path.join(root, 'Dance.mp3');
  await writeFile(file, Buffer.from('fixture'));
  const options = {
    artist: 'Test Creator',
    source: 'https://creator.example/dance',
    license: 'cc-by-sa-4.0',
    tags: ['ukrainian', 'gameplay'],
    confirmRights: true,
    date: '20260925',
  };
  await assert.rejects(createUploadManifest(file, options), /rights-evidence/);
  await assert.rejects(
    createUploadManifest(file, {
      ...options,
      rightsEvidence: 'https://creator.example/dance#license',
    }),
    /derivative-notice/,
  );
  const manifest = await createUploadManifest(file, {
    ...options,
    rightsEvidence: 'https://creator.example/dance#license',
    derivativeNotice: 'Converted from source OGG to MP3; normalized to archive target.',
  });
  assert.equal(manifest.tracks[0].rights.shareAlike.required, true);
  assert.match(manifest.tracks[0].rights.derivativeChangeNotice, /OGG to MP3/);
});
test('one-file and folder automation derive metadata while keeping rights explicit', async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'soundtrack-folder-intake-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  await writeFile(path.join(root, '02_Night-Drive.mp3'), Buffer.from('not parsed here'));
  await writeFile(path.join(root, '01 Arcade Pulse.mp3'), Buffer.from('not parsed here'));
  await writeFile(path.join(root, 'notes.txt'), Buffer.from('ignored'));
  const manifest = await createUploadManifest(root, {
    artist: 'Test Creator',
    source: 'https://creator.example/album',
    license: 'cc-by-4.0',
    tags: ['synth', 'gameplay'],
    confirmRights: true,
    date: '20260924',
  });
  assert.match(manifest.batchId, /^soundtrack-folder-intake-[a-z0-9]+-20260924$/);
  assert.deepEqual(
    manifest.tracks.map((track) => track.title),
    ['01 Arcade Pulse', '02 Night Drive'],
  );
  assert(manifest.tracks.every((track) => track.artist === 'Test Creator'));
  assert(manifest.tracks.every((track) => track.license === 'CC BY 4.0 International'));
  await assert.rejects(
    createUploadManifest(root, {
      artist: 'Test Creator',
      source: 'https://creator.example/album',
      license: 'cc0',
      tags: ['synth'],
    }),
    /confirm-rights/,
  );
});
test('folder automation preserves an explicit creator attribution requirement', async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'soundtrack-attribution-intake-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const file = path.join(root, 'Maximum Overdrive.mp3');
  await writeFile(file, Buffer.from('fixture'));
  const attribution =
    'Maximum Overdrive by Bogart VGM. CC BY 3.0. Credit: Bogart VGM; https://www.facebook.com/BogartVGM/.';
  const manifest = await createUploadManifest(file, {
    artist: 'Bogart VGM',
    source: 'https://opengameart.org/content/maximum-overdrive',
    license: 'cc-by-3.0',
    tags: ['synthwave', 'racing'],
    attribution,
    confirmRights: true,
    date: '20260926',
  });
  assert.equal(manifest.tracks[0].credit, attribution);
  assert.equal(manifest.tracks[0].rights.attribution, attribution);
});
test('one-file automation accepts an explicit display title without permitting a folder-wide override', async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'soundtrack-title-intake-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const first = path.join(root, 'maximum_overdrive.mp3');
  await writeFile(first, Buffer.from('fixture'));
  const options = {
    artist: 'Bogart VGM',
    source: 'https://creator.example/maximum-overdrive',
    license: 'cc-by-3.0',
    tags: ['synthwave'],
    title: 'Maximum Overdrive',
    confirmRights: true,
    date: '20260926',
  };
  const manifest = await createUploadManifest(first, options);
  assert.equal(manifest.tracks[0].title, 'Maximum Overdrive');
  assert.equal(manifest.tracks[0].id, 'bogart-vgm.maximum-overdrive');
  await writeFile(path.join(root, 'second.mp3'), Buffer.from('fixture'));
  await assert.rejects(createUploadManifest(root, options), /--title only with one MP3/);
});
test('folder automation reads common ID3v2.3 title and artist text frames', async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), 'soundtrack-id3-intake-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const frame = (id, value) => {
    const text = Buffer.concat([Buffer.from([3]), Buffer.from(value)]),
      header = Buffer.alloc(10);
    header.write(id, 0, 'ascii');
    header.writeUInt32BE(text.length, 4);
    return Buffer.concat([header, text]);
  };
  const body = Buffer.concat([frame('TIT2', 'Signal Run'), frame('TPE1', 'ID3 Artist')]),
    header = Buffer.from([
      0x49, 0x44, 0x33, 3, 0, 0,
      (body.length >> 21) & 0x7f,
      (body.length >> 14) & 0x7f,
      (body.length >> 7) & 0x7f,
      body.length & 0x7f,
    ]),
    file = path.join(root, 'fallback.mp3');
  await writeFile(file, Buffer.concat([header, body, Buffer.from('audio')]));
  assert.deepEqual(await readID3(file), { title: 'Signal Run', artist: 'ID3 Artist' });
  const manifest = await createUploadManifest(file, {
    source: 'https://creator.example/signal-run',
    license: 'cc0',
    tags: ['electro'],
    confirmRights: true,
    date: '20260924',
  });
  assert.equal(manifest.tracks[0].title, 'Signal Run');
  assert.equal(manifest.tracks[0].artist, 'ID3 Artist');
});

async function uploadFixture(t, batchId = "upload-fixture") {
  const root = await mkdtemp(
    path.join(os.tmpdir(), "soundtrack-upload-repository-"),
  );
  t.after(() => rm(root, { recursive: true, force: true }));
  await mkdir(path.join(root, "batches"));
  await mkdir(path.join(root, "intake"));
  for (const name of [
    ".nojekyll",
    "CREDITS.md",
    "README.md",
    "UPLOAD_GUIDE.md",
    "catalogue.json",
    "archive-directory.json",
    "deployment-manifest.json",
    "index.html",
    "inventory.json",
    "playback-policy.mjs",
    "player.mjs",
    "preview-catalogue.json",
    "style.css",
    "batches.json",
  ])
    await writeFile(
      path.join(root, name),
      await readFile(path.join(source, name)),
    );
  const batches = JSON.parse(await readFile(path.join(source, "batches.json")));
  for (const batch of batches.batches) {
    const target = path.join(root, "batches", batch.id);
    await mkdir(target);
    for (const name of ["deployment-manifest.json", "preview-catalogue.json"])
      await writeFile(
        path.join(target, name),
        await readFile(path.join(source, "batches", batch.id, name)),
      );
  }
  const audio = path.join(root, "candidate.mp3");
  const original = Buffer.concat([Buffer.from("ID3"), Buffer.alloc(61, 7)]);
  await writeFile(audio, original);
  const upload = path.join(root, "upload.json");
  const manifest = {
    batchId,
    title: "Upload fixture",
    description: "A byte-level intake fixture, not a listening approval.",
    tracks: [
      {
        id: `${batchId}.track`,
        file: audio,
        title: "Fixture track",
        artist: "Fixture artist",
        source: "https://example.com/fixture-track",
        license: "CC0 1.0 Universal",
        licenseURL: "https://creativecommons.org/publicdomain/zero/1.0/",
        credit: "Synthetic fixture bytes under CC0.",
        tags: ["fixture", "gameplay"],
      },
    ],
  };
  await writeFile(upload, JSON.stringify(manifest));
  return { root, audio, original, upload, manifest };
}

const generousDisk = { availableBytes: async () => 10 * 1024 ** 3 };
async function intakeState(root) {
  return {
    batches: await readFile(path.join(root, "batches.json"), "utf8"),
    catalogue: await readFile(path.join(root, "catalogue.json"), "utf8"),
    deployment: await readFile(
      path.join(root, "deployment-manifest.json"),
      "utf8",
    ),
    directories: (await readdir(path.join(root, "batches"))).sort(),
    staging: (await readdir(path.join(root, "intake"))).filter((name) =>
      name.startsWith(".upload-"),
    ),
  };
}

test("upload intake commits exact validated bytes and reproducible catalogue metadata", async (t) => {
  const f = await uploadFixture(t, "successful-upload");
  const originalHash = hash(f.original);
  const result = await prepareUpload(f.upload, {
    repositoryRoot: f.root,
    ...generousDisk,
    beforeCommit: () =>
      writeFile(
        f.audio,
        Buffer.concat([Buffer.from("ID3"), Buffer.alloc(93, 9)]),
      ),
  });
  assert.deepEqual(result, {
    batchId: "successful-upload",
    tracks: 1,
    audioBytes: f.original.length,
  });
  assert.deepEqual(
    await readFile(
      path.join(
        f.root,
        "batches",
        "successful-upload",
        "objects",
        `${originalHash}.mp3`,
      ),
    ),
    f.original,
  );
  const generated = await buildUnifiedCatalogue({ repositoryRoot: f.root });
  assert.equal(
    await readFile(path.join(f.root, "catalogue.json"), "utf8"),
    serializeCatalogue(generated),
  );
  const uploaded = generated.tracks.find(
    (track) => track.id === "successful-upload.track",
  );
  assert(uploaded);
  assert.equal(uploaded.rights.licenseId, "CC0");
  assert.equal(uploaded.rights.licenseVersion, "1.0");
  assert.equal(uploaded.rights.attribution, "Synthetic fixture bytes under CC0.");
  assert.deepEqual(uploaded.rights.shareAlike, {
    required: false,
    deliveryLicenseId: null,
    deliveryLicenseVersion: null,
    deliveryLicenseURL: null,
  });
  assert.deepEqual(
    (await readdir(path.join(f.root, "intake"))).filter((name) =>
      name.startsWith(".upload-"),
    ),
    [],
  );
});

test("upload intake rejects global duplicate identities before any repository write", async (t) => {
  const f = await uploadFixture(t, "duplicate-identity-upload");
  const catalogue = JSON.parse(
    await readFile(path.join(f.root, "catalogue.json")),
  );
  f.manifest.tracks[0].id = catalogue.tracks[0].id;
  await writeFile(f.upload, JSON.stringify(f.manifest));
  const before = await intakeState(f.root);
  await assert.rejects(
    prepareUpload(f.upload, { repositoryRoot: f.root, ...generousDisk }),
    /identity already exists/,
  );
  assert.deepEqual(await intakeState(f.root), before);
});

test("upload intake enforces the 256-recording limit before any repository write", async (t) => {
  const f = await uploadFixture(t, "capacity-upload");
  const cataloguePath = path.join(f.root, "catalogue.json");
  const catalogue = JSON.parse(await readFile(cataloguePath));
  catalogue.counts.declaredTracks = 256;
  await writeFile(cataloguePath, JSON.stringify(catalogue));
  const before = await intakeState(f.root);
  await assert.rejects(
    prepareUpload(f.upload, { repositoryRoot: f.root, ...generousDisk }),
    /at most 256/,
  );
  assert.deepEqual(await intakeState(f.root), before);
});

test("upload intake refuses low disk reserve and batch-directory symlinks without external writes", async (t) => {
  const low = await uploadFixture(t, "low-disk-upload");
  const lowBefore = await intakeState(low.root);
  await assert.rejects(
    prepareUpload(low.upload, {
      repositoryRoot: low.root,
      availableBytes: async () => 0,
    }),
    /leave at least 1 GiB/,
  );
  assert.deepEqual(await intakeState(low.root), lowBefore);

  const linked = await uploadFixture(t, "linked-upload");
  const external = await mkdtemp(
    path.join(os.tmpdir(), "soundtrack-upload-external-"),
  );
  t.after(() => rm(external, { recursive: true, force: true }));
  await symlink(external, path.join(linked.root, "batches", "linked-upload"));
  await assert.rejects(
    prepareUpload(linked.upload, {
      repositoryRoot: linked.root,
      ...generousDisk,
    }),
    /already exists/,
  );
  assert.deepEqual(await readdir(external), []);
});

test("upload intake bounds each source before reading it", async (t) => {
  const f = await uploadFixture(t, "oversized-upload");
  const handle = await open(f.audio, "w");
  await handle.truncate(100_000_000);
  await handle.close();
  const before = await intakeState(f.root);
  await assert.rejects(
    prepareUpload(f.upload, { repositoryRoot: f.root, ...generousDisk }),
    /MP3 size is invalid/,
  );
  assert.deepEqual(await intakeState(f.root), before);
});

test("upload intake serializes concurrent writers before either can snapshot the catalogue", async (t) => {
  const f = await uploadFixture(t, "serialized-upload");
  let release;
  const paused = new Promise((resolve) => {
    release = resolve;
  });
  let entered;
  const waiting = new Promise((resolve) => {
    entered = resolve;
  });
  const first = prepareUpload(f.upload, {
    repositoryRoot: f.root,
    ...generousDisk,
    beforeCommit: async () => {
      entered();
      await paused;
    },
  });
  await waiting;
  await assert.rejects(
    prepareUpload(f.upload, { repositoryRoot: f.root, ...generousDisk }),
    /writer lock/,
  );
  release();
  await first;
  const catalogue = await buildUnifiedCatalogue({ repositoryRoot: f.root });
  assert.equal(
    catalogue.tracks.filter((track) => track.id === "serialized-upload.track")
      .length,
    1,
  );
});

test("incomplete rollback retains exact recovery backups", async (t) => {
  const root = await mkdtemp(
    path.join(os.tmpdir(), "soundtrack-upload-rollback-"),
  );
  t.after(() => rm(root, { recursive: true, force: true }));
  const transactionRoot = path.join(root, "transaction");
  const stageBatch = path.join(transactionRoot, "batch");
  await mkdir(path.join(root, "batches"));
  await mkdir(stageBatch, { recursive: true });
  await mkdir(path.join(transactionRoot, "new"));
  const rootFiles = new Map([
    ["batches.json", Buffer.from("new-index")],
    ["catalogue.json", Buffer.from("new-catalogue")],
  ]);
  for (const [name, bytes] of rootFiles) {
    await writeFile(path.join(root, name), Buffer.from(`old-${name}`));
    await writeFile(path.join(transactionRoot, "new", name), bytes);
  }
  const move = async (from, to) => {
    if (from === path.join(transactionRoot, "new", "catalogue.json")) {
      const error = new Error("install failed");
      error.code = "ENOSPC";
      throw error;
    }
    if (from === path.join(transactionRoot, "backups", "catalogue.json")) {
      const error = new Error("restore failed");
      error.code = "EACCES";
      throw error;
    }
    return rename(from, to);
  };
  let failure;
  try {
    await commitTransaction({
      repositoryRoot: root,
      batchId: "rollback-fixture",
      transactionRoot,
      stageBatch,
      rootFiles,
      operations: { rename: move },
    });
  } catch (error) {
    failure = error;
  }
  assert.equal(failure?.preserveTransaction, true);
  assert.match(failure.message, /Recovery files are retained/);
  assert.equal(
    await readFile(
      path.join(transactionRoot, "backups", "catalogue.json"),
      "utf8",
    ),
    "old-catalogue.json",
  );
});
test("a declared tiny preview batch verifies its exact static and object bytes reproducibly", async (t) => {
  const f = await fixture(t);
  const args = { ...f.declaration, baseURL };
  const first = await verifyPreviewBatch(f.root, args);
  assert.deepEqual(await verifyPreviewBatch(f.root, args), first);
  assert.equal(first.trackCount, 1);
  assert.equal(first.manifestSha256, f.declaration.manifest.sha256);
  assert.equal(first.baseURL, `${baseURL}batches/${f.id}/`);
  assert.equal(first.files.size, 9);
  assert.equal(
    first.totalBytes,
    [...f.files.values()].reduce((sum, bytes) => sum + bytes.length, 0),
  );
});
test("combining verified batches preserves root pins and enforces aggregate uniqueness and budgets", async (t) => {
  const f = await fixture(t);
  const batch = await verifyPreviewBatch(f.root, { ...f.declaration, baseURL });
  const rootDeclarations = validateDeclarations(
    JSON.parse(await readFile(path.join(source, "deployment-manifest.json"))),
    JSON.parse(await readFile(path.join(source, "inventory.json"))),
    JSON.parse(await readFile(path.join(source, "preview-catalogue.json"))),
  );
  const merged = structuredClone(rootDeclarations);
  appendVerifiedPreviewBatch(merged, f.declaration, batch);
  assert.equal(merged.trackCount, 71);
  for (const [name, pin] of rootDeclarations.files)
    assert.deepEqual(merged.files.get(name), pin);
  assert.deepEqual(merged.files.get(`batches/${f.id}/${f.object.path}`), {
    ...f.object,
    path: `batches/${f.id}/${f.object.path}`,
  });
  assert.throws(
    () => appendVerifiedPreviewBatch(merged, f.declaration, batch),
    /identity/,
  );
  for (const changed of [
    { trackCount: 256 },
    { totalBytes: 900000000 - batch.totalBytes },
  ]) {
    const refused = { ...structuredClone(rootDeclarations), ...changed };
    const before = structuredClone(refused);
    assert.throws(
      () => appendVerifiedPreviewBatch(refused, f.declaration, batch),
      /Combined previews/,
    );
    assert.deepEqual(refused, before);
  }
  const duplicateHash = structuredClone(rootDeclarations);
  duplicateHash.files.set("batches/earlier/" + f.object.path, {
    ...f.object,
    path: "batches/earlier/" + f.object.path,
  });
  assert.throws(
    () => appendVerifiedPreviewBatch(duplicateHash, f.declaration, batch),
    /recording hash/,
  );
});

test("batch declarations are explicit, unique, bounded and rooted at the exact batch path", async (t) => {
  const f = await fixture(t);
  const format = "revealline-soundtrack-preview-batches.v1";
  assert.deepEqual(validateBatchIndex({ format, batches: [] }), []);
  assert.deepEqual(validateBatchIndex({ format, batches: [f.declaration] }), [
    f.declaration,
  ]);
  for (const id of [
    "../escape",
    "UPPER",
    "with_underscore",
    "a/b",
    "a%2fb",
    "a\\b",
    "a\n",
    "a".repeat(65),
  ])
    assert.throws(() =>
      validateBatchIndex({ format, batches: [{ ...f.declaration, id }] }),
    );
  assert.throws(
    () =>
      validateBatchIndex({ format, batches: [f.declaration, f.declaration] }),
    /duplicate/,
  );
  for (const changed of [
    { path: "other.json" },
    { bytes: 524289 },
    { sha256: "not-a-hash" },
  ])
    assert.throws(() =>
      validateBatchIndex({
        format,
        batches: [
          {
            ...f.declaration,
            manifest: { ...f.declaration.manifest, ...changed },
          },
        ],
      }),
    );
});
for (const [name, mutate] of [
  [
    "more than20 recordings",
    (f) => {
      f.manifest.expected.trackCount = 21;
    },
  ],
  [
    "zero recordings",
    (f) => {
      f.manifest.expected.trackCount = 0;
    },
  ],
  [
    "invented game admission",
    (f) => {
      f.catalogue.gameCatalogueAdmission = true;
    },
  ],
  [
    "invented listening approval",
    (f) => {
      f.catalogue.listeningApproval = "approved";
    },
  ],
  [
    "another batch URL",
    (f) => {
      f.catalogue.archive.baseURL = `${baseURL}batches/other/`;
    },
  ],
  [
    "root archive URL",
    (f) => {
      f.catalogue.archive.baseURL = baseURL;
    },
  ],
  [
    "stale inventory pin",
    (f) => {
      f.catalogue.archive.inventorySha256 = "f".repeat(64);
    },
  ],
  [
    "unsupported licence",
    (f) => {
      f.catalogue.tracks[0].licenseURL = "https://example.com/noncommercial";
    },
  ],
  [
    "ShareAlike licence without explicit delivery terms",
    (f) => {
      Object.assign(f.catalogue.tracks[0], {
        license: "CC BY-SA 4.0 International",
        licenseURL: "https://creativecommons.org/licenses/by-sa/4.0/",
        recordingModeEligible: false,
      });
    },
  ],
  [
    "structured rights removed from a new batch",
    (f) => {
      delete f.catalogue.tracks[0].rights;
    },
  ],
  [
    "missing legacy licence label",
    (f) => {
      delete f.catalogue.tracks[0].license;
    },
  ],
  [
    "mismatched legacy licence label",
    (f) => {
      f.catalogue.tracks[0].license = "CC BY 4.0 International";
    },
  ],
  [
    "ShareAlike recording marked Recording-mode-safe",
    (f) => {
      const track = f.catalogue.tracks[0];
      Object.assign(track, {
        license: "CC BY-SA 4.0 International",
        licenseURL: "https://creativecommons.org/licenses/by-sa/4.0/",
        recordingModeEligible: true,
        rights: createRightsMetadata({
          licenseURL: "https://creativecommons.org/licenses/by-sa/4.0/",
          rightsEvidenceURL: "https://example.com/fixture#license",
          attribution: track.credit,
          derivativeChangeNotice: "Converted from WAV to MP3 for this fixture.",
        }),
      });
    },
  ],
  [
    "removed attribution",
    (f) => {
      f.catalogue.tracks[0].credit = "";
    },
  ],
  [
    "unknown audio object",
    (f) => {
      f.catalogue.tracks[0].path = "objects/unknown.mp3";
    },
  ],
  [
    "changed object bytes",
    (f) => {
      f.inventory.files[0].bytes++;
    },
  ],
  [
    "object alias",
    (f) => {
      f.inventory.files[0].path = "objects/../audio.mp3";
    },
  ],
  [
    "undeclared static entry",
    (f) => {
      f.manifest.files.push({
        path: "private.json",
        bytes: 0,
        sha256: hash(""),
      });
    },
  ],
])
  test(`preview batch refuses ${name}`, async (t) => {
    const f = await fixture(t);
    mutate(f);
    assert.throws(() =>
      validateBatchDeclarations(f.manifest, f.inventory, f.catalogue, {
        id: f.id,
        baseURL,
      }),
    );
  });
test("complete pin validation rejects changed bytes, missing files and unlisted additions", async (t) => {
  const f = await fixture(t);
  const args = { ...f.declaration, baseURL };
  const original = f.files.get(f.object.path);
  await writeFile(
    path.join(f.root, f.object.path),
    Buffer.alloc(original.length, 7),
  );
  await assert.rejects(verifyPreviewBatch(f.root, args), /SHA-256/);
  await writeFile(path.join(f.root, f.object.path), original);
  await writeFile(path.join(f.root, "extra.txt"), "unlisted");
  await assert.rejects(verifyPreviewBatch(f.root, args), /Unexpected/);
  await rm(path.join(f.root, "extra.txt"));
  await rm(path.join(f.root, f.object.path));
  await assert.rejects(verifyPreviewBatch(f.root, args), /exact deployment/);
});
test("batch manifest substitution and symbolic links are refused", async (t) => {
  const f = await fixture(t);
  await assert.rejects(
    verifyPreviewBatch(f.root, {
      ...f.declaration,
      baseURL,
      manifest: { ...f.declaration.manifest, sha256: "0".repeat(64) },
    }),
    /explicit pin/,
  );
  const object = path.join(f.root, f.object.path);
  await rm(object);
  await symlink(path.join(f.root, "README.md"), object);
  await assert.rejects(
    verifyPreviewBatch(f.root, { ...f.declaration, baseURL }),
    /Unexpected object/,
  );
  const alias = f.root + "-alias";
  t.after(() => rm(alias, { force: true }));
  await symlink(f.root, alias);
  await assert.rejects(
    verifyPreviewBatch(alias, { ...f.declaration, baseURL }),
    /ordinary directory/,
  );
});
