import { constants, createReadStream } from 'node:fs';
import {
  copyFile,
  link,
  lstat,
  mkdir,
  open,
  readFile,
  readdir,
  realpath,
  statfs,
} from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  LICENSES_BY_URL,
  allowsLegacyRightsArchive,
  validateRecordingRights,
} from './rights-policy.mjs';

const EXPECTED_TRACKS = 70;
const EXPECTED_AUDIO_BYTES = 354986122;
const MAX_FILE_BYTES = 100000000;
// Keep 100 MB of headroom below GitHub Pages' documented 1 GB published-site
// limit. New recordings must move to another archive shard before this guard
// is reached.
const MAX_SITE_BYTES = 900000000;
const MANIFEST = 'deployment-manifest.json';
const BATCHES = 'batches.json';
const DIRECTORY = 'archive-directory.json';
const BATCH_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
const STATIC = new Set([
  'index.html',
  'style.css',
  'player.mjs',
  'playback-policy.mjs',
  'catalogue.json',
  DIRECTORY,
  'UPLOAD_GUIDE.md',
  'inventory.json',
  'preview-catalogue.json',
  '.nojekyll',
  'README.md',
  'CREDITS.md',
]);
const REQUIRED = [
  'index.html',
  'style.css',
  'player.mjs',
  'inventory.json',
  'preview-catalogue.json',
  '.nojekyll',
  'README.md',
  'CREDITS.md',
];
const ROOT_REQUIRED = [
  ...REQUIRED,
  'playback-policy.mjs',
  'catalogue.json',
  DIRECTORY,
  'UPLOAD_GUIDE.md',
];
const PRIVATE = new Set([
  '.git',
  '.github',
  'verify.mjs',
  'test-verify.mjs',
  'render.mjs',
  'rights-policy.mjs',
  'intake',
]);
const validHash = (value) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const objectPath = (value) =>
  typeof value === 'string' && /^objects\/[a-f0-9]{64}\.mp3$/.test(value);
const demand = (value, message) => {
  if (!value) throw new Error(message);
};
const plain = (value) =>
  value !== null && typeof value === 'object' && !Array.isArray(value);
function exactKeys(value, keys, label) {
  demand(
    plain(value) &&
      Object.keys(value).every((key) => keys.includes(key)) &&
      keys.every((key) => Object.hasOwn(value, key)),
    `Invalid ${label} fields.`,
  );
}
function safeURL(value) {
  try {
    const url = new URL(value);
    return (
      typeof value === 'string' &&
      value.length <= 2048 &&
      ['https:', 'http:'].includes(url.protocol) &&
      !url.username &&
      !url.password
    );
  } catch {
    return false;
  }
}
function pin(value) {
  exactKeys(value, ['path', 'bytes', 'sha256'], 'file pin');
  demand(
    (STATIC.has(value.path) || objectPath(value.path)) &&
      Number.isSafeInteger(value.bytes) &&
      value.bytes >= 0 &&
      value.bytes < MAX_FILE_BYTES &&
      validHash(value.sha256),
    'Invalid public file pin.',
  );
  if (objectPath(value.path))
    demand(
      value.path === `objects/${value.sha256}.mp3` && value.bytes > 0,
      'Audio object name differs from its hash.',
    );
  return value;
}

function validatePayloadDeclarations(manifest, inventory, catalogue, expected) {
  exactKeys(
    manifest,
    ['format', 'id', 'expected', 'files', 'provenance'],
    'deployment manifest',
  );
  demand(
    manifest.format === 'revealline-soundtrack-preview-deployment.v1' &&
      typeof manifest.id === 'string' &&
      /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$/.test(manifest.id),
    'Invalid deployment identity.',
  );
  exactKeys(manifest.expected, ['trackCount', 'audioBytes'], 'expected payload');
  demand(
    manifest.expected.trackCount === expected.trackCount &&
      manifest.expected.audioBytes === expected.audioBytes,
    'Deployment differs from its pinned recording payload.',
  );
  demand(plain(manifest.provenance), 'Deployment provenance must be an object.');
  demand(
    Array.isArray(manifest.files) && manifest.files.length <= 512,
    'Invalid deployment file list.',
  );
  const files = new Map();
  let total = 0;
  for (const entry of manifest.files) {
    pin(entry);
    demand(!files.has(entry.path), 'Duplicate deployment file.');
    files.set(entry.path, entry);
    total += entry.bytes;
  }
  demand(
    (expected.baseURL ? REQUIRED : ROOT_REQUIRED).every((name) => files.has(name)) &&
      total < MAX_SITE_BYTES,
    'Missing site file or excessive total size.',
  );
  demand(files.get('.nojekyll').bytes === 0, '.nojekyll must be empty.');
  exactKeys(inventory, ['format', 'id', 'files'], 'archive inventory');
  demand(
    inventory.format === 'revealline-soundtrack-archive.v1' &&
      inventory.id === manifest.id &&
      Array.isArray(inventory.files) &&
      inventory.files.length === expected.trackCount,
    'Archive identity/count differs.',
  );
  const objects = new Map();
  let audioBytes = 0;
  for (const entry of inventory.files) {
    pin(entry);
    demand(
      objectPath(entry.path) && !objects.has(entry.path),
      'Duplicate or non-audio inventory entry.',
    );
    const declared = files.get(entry.path);
    demand(
      declared && declared.bytes === entry.bytes && declared.sha256 === entry.sha256,
      'Inventory differs from deployment pins.',
    );
    objects.set(entry.path, entry);
    audioBytes += entry.bytes;
  }
  demand(
    audioBytes === expected.audioBytes &&
      [...files.keys()].filter(objectPath).length === expected.trackCount,
    'Audio total or deployed object count differs.',
  );
  demand(
    plain(catalogue) &&
      catalogue.format === 'revealline-licensed-preview-catalogue.v1' &&
      catalogue.status === 'licensed-preview' &&
      catalogue.gameCatalogueAdmission === false &&
      catalogue.listeningApproval === 'not-reviewed' &&
      Array.isArray(catalogue.tracks) &&
      catalogue.tracks.length === expected.trackCount,
    'Preview catalogue must contain exactly its declared unapproved preview recordings.',
  );
  exactKeys(catalogue.archive, ['id', 'baseURL', 'inventorySha256'], 'preview archive');
  demand(
    catalogue.archive.id === manifest.id &&
      typeof catalogue.archive.baseURL === 'string' &&
      (expected.baseURL
        ? catalogue.archive.baseURL === expected.baseURL
        : /^https:\/\/mekhovov\.github\.io\/revealline-soundtracks-[0-9]+\/$/.test(
            catalogue.archive.baseURL,
          )) &&
      catalogue.archive.baseURL === new URL(catalogue.archive.baseURL).href &&
      catalogue.archive.inventorySha256 === files.get('inventory.json').sha256,
    'Preview archive differs from the project-owned inventory.',
  );
  const seen = new Set();
  const ids = new Set();
  for (const track of catalogue.tracks) {
    demand(plain(track), 'Invalid preview recording.');
    const entry = objects.get(track.path);
    demand(
      entry &&
        track.sha256 === entry.sha256 &&
        track.bytes === entry.bytes &&
        !seen.has(track.path),
      'Preview recording differs from its inventory object.',
    );
    demand(
      typeof track.id === 'string' &&
        track.id.length > 0 &&
        track.id.length <= 160 &&
        !ids.has(track.id),
      'Missing or duplicate preview recording identity.',
    );
    demand(
      LICENSES_BY_URL.has(track.licenseURL) &&
        safeURL(track.source) &&
        typeof track.credit === 'string' &&
        track.credit.trim().length > 0 &&
        track.credit.length <= 2048,
      'Recording lacks supported redistribution license, source or attribution.',
    );
    validateRecordingRights(track, {
      allowLegacy: allowsLegacyRightsArchive(catalogue.archive.id),
    });
    demand(
      typeof track.title === 'string' &&
        track.title.trim().length > 0 &&
        typeof track.artist === 'string' &&
        track.artist.trim().length > 0,
      'Recording title and artist are required.',
    );
    seen.add(track.path);
    ids.add(track.id);
  }
  return {
    files,
    totalBytes: total,
    audioBytes,
    trackCount: seen.size,
    recordingIds: ids,
  };
}

/** Root publication keeps its historical 70-track/byte boundary unchanged. */
export function validateDeclarations(manifest, inventory, catalogue) {
  return validatePayloadDeclarations(manifest, inventory, catalogue, {
    trackCount: EXPECTED_TRACKS,
    audioBytes: EXPECTED_AUDIO_BYTES,
  });
}

export function validateBatchDeclarations(
  manifest,
  inventory,
  catalogue,
  { id, baseURL },
) {
  demand(
    typeof id === 'string' && BATCH_ID.test(id) && id === id.trim(),
    'Invalid preview batch identity.',
  );
  demand(
    typeof baseURL === 'string' &&
      /^https:\/\/mekhovov\.github\.io\/revealline-soundtracks-[0-9]+\/$/.test(baseURL) &&
      baseURL === new URL(baseURL).href,
    'Preview batches require a project-owned root URL.',
  );
  demand(
    manifest?.id === id &&
      Number.isSafeInteger(manifest.expected?.trackCount) &&
      manifest.expected.trackCount >= 1 &&
      manifest.expected.trackCount <= 20 &&
      Number.isSafeInteger(manifest.expected.audioBytes) &&
      manifest.expected.audioBytes > 0,
    'Preview batch must declare 1–20 recordings and their exact audio bytes.',
  );
  return validatePayloadDeclarations(manifest, inventory, catalogue, {
    ...manifest.expected,
    baseURL: `${baseURL}batches/${id}/`,
  });
}

export function validateBatchIndex(value) {
  exactKeys(value, ['format', 'batches'], 'preview batch index');
  demand(
    value.format === 'revealline-soundtrack-preview-batches.v1' &&
      Array.isArray(value.batches) &&
      value.batches.length <= 32,
    'Invalid preview batch index.',
  );
  const ids = new Set();
  for (const entry of value.batches) {
    exactKeys(entry, ['id', 'manifest'], 'preview batch declaration');
    exactKeys(entry.manifest, ['path', 'bytes', 'sha256'], 'preview batch manifest pin');
    demand(
      typeof entry.id === 'string' &&
        BATCH_ID.test(entry.id) &&
        entry.id === entry.id.trim() &&
        !ids.has(entry.id) &&
        entry.manifest.path === `batches/${entry.id}/${MANIFEST}` &&
        Number.isSafeInteger(entry.manifest.bytes) &&
        entry.manifest.bytes > 0 &&
        entry.manifest.bytes <= 512 * 1024 &&
        validHash(entry.manifest.sha256),
      'Invalid or duplicate preview batch pin.',
    );
    ids.add(entry.id);
  }
  return value.batches;
}

export function validateArchiveDirectory(value) {
  exactKeys(value, ['format', 'catalogues'], 'archive directory');
  demand(
    value.format === 'revealline-public-soundtrack-directory.v1' &&
      Array.isArray(value.catalogues) &&
      value.catalogues.length >= 1 &&
      value.catalogues.length <= 8,
    'Invalid archive directory.',
  );
  const ids = new Set(),
    urls = new Set();
  for (const entry of value.catalogues) {
    exactKeys(entry, ['id', 'url', 'baseURL', 'required'], 'archive directory entry');
    const match = /^revealline-soundtracks-([0-9]{2})$/.exec(entry.id),
      expectedBaseURL = match
        ? `https://mekhovov.github.io/revealline-soundtracks-${match[1]}/`
        : '';
    demand(
      match &&
        entry.baseURL === expectedBaseURL &&
        entry.url === `${expectedBaseURL}catalogue.json` &&
        typeof entry.required === 'boolean' &&
        !ids.has(entry.id) &&
        !urls.has(entry.url),
      'Invalid or duplicate archive directory entry.',
    );
    ids.add(entry.id);
    urls.add(entry.url);
  }
  demand(
    value.catalogues[0].id === 'revealline-soundtracks-01' &&
      value.catalogues[0].required === true,
    'The primary soundtrack archive must remain required and first.',
  );
  return value.catalogues;
}

async function json(root, name, maxBytes) {
  const file = path.join(root, name);
  const stat = await lstat(file);
  demand(
    stat.isFile() && !stat.isSymbolicLink() && stat.size <= maxBytes,
    `Invalid or oversized ${name}.`,
  );
  return JSON.parse(await readFile(file, 'utf8'));
}
async function hashFile(file, expectedBytes) {
  const handle = await open(file, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const before = await handle.stat();
    demand(
      before.isFile() && before.size === expectedBytes && before.size < MAX_FILE_BYTES,
      `File size differs: ${file}`,
    );
    const hash = createHash('sha256');
    let bytes = 0;
    for await (const block of createReadStream(file, {
      fd: handle.fd,
      autoClose: false,
      highWaterMark: 64 * 1024,
    })) {
      bytes += block.length;
      demand(bytes <= expectedBytes, `File grew during verification: ${file}`);
      hash.update(block);
    }
    const after = await handle.stat();
    demand(
      bytes === expectedBytes &&
        after.size === before.size &&
        after.mtimeMs === before.mtimeMs &&
        after.ctimeMs === before.ctimeMs,
      `File changed during verification: ${file}`,
    );
    return hash.digest('hex');
  } finally {
    await handle.close();
  }
}

async function verifyPayloadSite(source, { staged = false, batchId, baseURL } = {}) {
  const root = await realpath(source);
  const manifest = await json(root, MANIFEST, 512 * 1024);
  const inventory = await json(root, 'inventory.json', 256 * 1024);
  const catalogue = await json(root, 'preview-catalogue.json', 1024 * 1024);
  const result = batchId
    ? validateBatchDeclarations(manifest, inventory, catalogue, {
        id: batchId,
        baseURL,
      })
    : validateDeclarations(manifest, inventory, catalogue);
  const actual = new Set();
  for (const name of await readdir(root)) {
    const stat = await lstat(path.join(root, name));
    demand(!stat.isSymbolicLink(), `Symbolic link refused: ${name}`);
    if (!batchId && !staged && PRIVATE.has(name)) continue;
    if (!batchId && [BATCHES, 'batches'].includes(name)) continue;
    if (name === 'objects') {
      demand(stat.isDirectory(), 'objects must be an ordinary directory.');
      for (const object of await readdir(path.join(root, name))) {
        const relative = `objects/${object}`;
        const entry = await lstat(path.join(root, relative));
        demand(
          entry.isFile() && !entry.isSymbolicLink() && objectPath(relative),
          `Unexpected object: ${relative}`,
        );
        actual.add(relative);
      }
    } else {
      demand(
        stat.isFile() && (name === MANIFEST || STATIC.has(name)),
        `Unexpected public root entry: ${name}`,
      );
      if (name !== MANIFEST) actual.add(name);
    }
  }
  demand(
    actual.size === result.files.size &&
      [...actual].every((name) => result.files.has(name)),
    'Public files differ from the exact deployment manifest.',
  );
  const manifestStat = await lstat(path.join(root, MANIFEST));
  demand(
    result.totalBytes + manifestStat.size < MAX_SITE_BYTES,
    'Site exceeds its 900 MB budget.',
  );
  for (const entry of result.files.values()) {
    demand(
      (await hashFile(path.join(root, entry.path), entry.bytes)) === entry.sha256,
      `SHA-256 differs: ${entry.path}`,
    );
  }
  const manifestSha256 = await hashFile(path.join(root, MANIFEST), manifestStat.size);
  // Detect changes to metadata between parsing and the full file pass.
  demand(
    JSON.stringify(await json(root, MANIFEST, 512 * 1024)) === JSON.stringify(manifest) &&
      JSON.stringify(await json(root, 'inventory.json', 256 * 1024)) ===
        JSON.stringify(inventory) &&
      JSON.stringify(await json(root, 'preview-catalogue.json', 1024 * 1024)) ===
        JSON.stringify(catalogue),
    'Deployment metadata changed during verification.',
  );
  return {
    ...result,
    root,
    manifestSha256,
    manifestBytes: manifestStat.size,
    baseURL: catalogue.archive.baseURL,
    totalBytes: result.totalBytes + manifestStat.size,
  };
}

/** Also exported for tiny file/hash tests without the historic 338 MiB payload. */
export async function verifyPreviewBatch(source, { id, baseURL, manifest }) {
  validateBatchIndex({
    format: 'revealline-soundtrack-preview-batches.v1',
    batches: [{ id, manifest }],
  });
  const stat = await lstat(source);
  demand(
    stat.isDirectory() && !stat.isSymbolicLink(),
    'Preview batch must be an ordinary directory.',
  );
  const result = await verifyPayloadSite(source, {
    staged: true,
    batchId: id,
    baseURL,
  });
  demand(
    result.manifestSha256 === manifest.sha256 && result.manifestBytes === manifest.bytes,
    'Preview batch deployment manifest differs from its explicit pin.',
  );
  return result;
}

/** Combine results only after both payloads have passed their own byte checks. */
export function appendVerifiedPreviewBatch(result, entry, batch) {
  demand(
    result.trackCount + batch.trackCount <= 256 &&
      result.totalBytes + batch.totalBytes < MAX_SITE_BYTES,
    'Combined previews exceed 256 recordings or the 900 MB site budget.',
  );
  const hashes = new Set(
    [...result.files.values()]
      .filter((file) => /(?:^|\/)objects\//.test(file.path))
      .map((file) => file.sha256),
  );
  for (const id of batch.recordingIds)
    demand(
      !result.recordingIds.has(id),
      'A preview batch duplicates an existing recording identity.',
    );
  for (const file of batch.files.values())
    if (objectPath(file.path))
      demand(
        !hashes.has(file.sha256),
        'A preview batch duplicates an existing recording hash.',
      );
  for (const id of batch.recordingIds) result.recordingIds.add(id);
  for (const file of batch.files.values())
    result.files.set(`batches/${entry.id}/${file.path}`, {
      ...file,
      path: `batches/${entry.id}/${file.path}`,
    });
  result.files.set(entry.manifest.path, entry.manifest);
  result.trackCount += batch.trackCount;
  result.audioBytes += batch.audioBytes;
  result.totalBytes += batch.totalBytes;
}

export async function verifyPreviewSite(source, { staged = false } = {}) {
  const result = await verifyPayloadSite(source, { staged });
  const root = result.root;
  validateArchiveDirectory(await json(root, DIRECTORY, 64 * 1024));
  let declaration,
    declarationBytes = 0;
  try {
    declaration = await json(root, BATCHES, 512 * 1024);
    declarationBytes = (await lstat(path.join(root, BATCHES))).size;
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  const batches = declaration ? validateBatchIndex(declaration) : [];
  const expectedIds = new Set(batches.map((entry) => entry.id));
  let actualIds = [];
  try {
    const stat = await lstat(path.join(root, 'batches'));
    demand(
      stat.isDirectory() && !stat.isSymbolicLink(),
      'batches must be an ordinary directory.',
    );
    actualIds = await readdir(path.join(root, 'batches'));
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  demand(
    actualIds.length === expectedIds.size && actualIds.every((id) => expectedIds.has(id)),
    'Preview batch directories differ from the explicit declarations.',
  );
  for (const entry of batches) {
    const batch = await verifyPreviewBatch(path.join(root, 'batches', entry.id), {
      id: entry.id,
      baseURL: result.baseURL,
      manifest: entry.manifest,
    });
    appendVerifiedPreviewBatch(result, entry, batch);
  }
  result.batchesSha256 = null;
  if (declaration) {
    result.batchesSha256 = await hashFile(path.join(root, BATCHES), declarationBytes);
    demand(
      JSON.stringify(await json(root, BATCHES, 512 * 1024)) ===
        JSON.stringify(declaration),
      'Preview batch declarations changed during verification.',
    );
    result.files.set(BATCHES, {
      path: BATCHES,
      bytes: declarationBytes,
      sha256: result.batchesSha256,
    });
    result.totalBytes += declarationBytes;
  }
  demand(
    result.trackCount <= 256 && result.totalBytes < MAX_SITE_BYTES,
    'Combined previews exceed 256 recordings or the 900 MB site budget.',
  );
  return result;
}

export async function stagePreviewSite(source, destination) {
  const verified = await verifyPreviewSite(source);
  const parent = await realpath(path.dirname(path.resolve(destination)));
  const target = path.join(parent, path.basename(destination));
  demand(
    target !== verified.root &&
      !['objects', 'batches'].some(
        (name) =>
          target === path.join(verified.root, name) ||
          target.startsWith(path.join(verified.root, name) + path.sep),
      ),
    'Invalid staging destination.',
  );
  let remaining = verified.totalBytes;
  const reserve = async () => {
    const disk = await statfs(parent);
    demand(
      disk.bavail * disk.bsize >= 1024 ** 3 + remaining + 1024 ** 2,
      'Staging must leave at least 1 GiB free.',
    );
  };
  await reserve();
  await mkdir(target); // No recursive creation: an existing target is never overwritten.
  await mkdir(path.join(target, 'objects'));
  const entries = [
    ...verified.files.values(),
    {
      path: MANIFEST,
      bytes: (await lstat(path.join(verified.root, MANIFEST))).size,
    },
  ];
  for (const entry of entries) {
    await reserve();
    const original = path.join(verified.root, entry.path);
    const output = path.join(target, entry.path);
    await mkdir(path.dirname(output), { recursive: true });
    demand(
      !(await lstat(original)).isSymbolicLink(),
      'Source became a symlink during staging.',
    );
    try {
      await link(original, output);
    } catch (error) {
      if (!['EXDEV', 'EPERM', 'ENOTSUP', 'EOPNOTSUPP'].includes(error.code)) throw error;
      await copyFile(original, output, constants.COPYFILE_EXCL);
    }
    remaining -= entry.bytes;
  }
  const staged = await verifyPreviewSite(target, { staged: true });
  demand(
    staged.manifestSha256 === verified.manifestSha256 &&
      staged.batchesSha256 === verified.batchesSha256,
    'Staged manifest differs from the verified source.',
  );
  return staged;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  let source = process.cwd();
  let stage;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--root' && args[i + 1]) source = path.resolve(args[++i]);
    else if (args[i] === '--stage' && args[i + 1]) stage = path.resolve(args[++i]);
    else
      throw new Error('Usage: node verify.mjs [--root SOURCE] [--stage NEW_DIRECTORY]');
  }
  const result = stage
    ? await stagePreviewSite(source, stage)
    : await verifyPreviewSite(source);
  console.log(
    JSON.stringify(
      {
        verified: true,
        tracks: result.trackCount,
        audioBytes: result.audioBytes,
        publicBytes: result.totalBytes,
        manifestSha256: result.manifestSha256,
        batchesSha256: result.batchesSha256,
        staged: Boolean(stage),
      },
      null,
      2,
    ),
  );
}
