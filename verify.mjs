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

const EXPECTED_TRACKS = 70;
const EXPECTED_AUDIO_BYTES = 354986122;
const MAX_FILE_BYTES = 100000000;
const MAX_SITE_BYTES = 800000000;
const MANIFEST = 'deployment-manifest.json';
const STATIC = new Set([
  'index.html',
  'style.css',
  'player.mjs',
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
const PRIVATE = new Set(['.git', '.github', 'verify.mjs', 'render.mjs', 'intake']);
const LICENSES = new Set([
  'https://creativecommons.org/publicdomain/zero/1.0/',
  'https://creativecommons.org/licenses/by/3.0/',
  'https://creativecommons.org/licenses/by/4.0/',
]);
const validHash = (value) => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
const objectPath = (value) =>
  typeof value === 'string' && /^objects\/[a-f0-9]{64}\.mp3$/.test(value);
const demand = (value, message) => {
  if (!value) throw new Error(message);
};
const plain = (value) => value !== null && typeof value === 'object' && !Array.isArray(value);
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

/** Metadata-only boundary, exported to allow small synthetic refusal checks. */
export function validateDeclarations(manifest, inventory, catalogue) {
  exactKeys(manifest, ['format', 'id', 'expected', 'files', 'provenance'], 'deployment manifest');
  demand(
    manifest.format === 'revealline-soundtrack-preview-deployment.v1' &&
      typeof manifest.id === 'string' &&
      /^[a-zA-Z0-9][a-zA-Z0-9._-]{0,79}$/.test(manifest.id),
    'Invalid deployment identity.',
  );
  exactKeys(manifest.expected, ['trackCount', 'audioBytes'], 'expected payload');
  demand(
    manifest.expected.trackCount === EXPECTED_TRACKS &&
      manifest.expected.audioBytes === EXPECTED_AUDIO_BYTES,
    'Deployment differs from the pinned 70-recording payload.',
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
    REQUIRED.every((name) => files.has(name)) && total < MAX_SITE_BYTES,
    'Missing site file or excessive total size.',
  );
  demand(files.get('.nojekyll').bytes === 0, '.nojekyll must be empty.');
  exactKeys(inventory, ['format', 'id', 'files'], 'archive inventory');
  demand(
    inventory.format === 'revealline-soundtrack-archive.v1' &&
      inventory.id === manifest.id &&
      Array.isArray(inventory.files) &&
      inventory.files.length === EXPECTED_TRACKS,
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
    audioBytes === EXPECTED_AUDIO_BYTES &&
      [...files.keys()].filter(objectPath).length === EXPECTED_TRACKS,
    'Audio total or deployed object count differs.',
  );
  demand(
    plain(catalogue) &&
      catalogue.format === 'revealline-licensed-preview-catalogue.v1' &&
      catalogue.status === 'licensed-preview' &&
      catalogue.gameCatalogueAdmission === false &&
      catalogue.listeningApproval === 'not-reviewed' &&
      Array.isArray(catalogue.tracks) &&
      catalogue.tracks.length === EXPECTED_TRACKS,
    'Preview catalogue must contain exactly 70 unapproved preview recordings.',
  );
  exactKeys(catalogue.archive, ['id', 'baseURL', 'inventorySha256'], 'preview archive');
  demand(
    catalogue.archive.id === manifest.id &&
      typeof catalogue.archive.baseURL === 'string' &&
      /^https:\/\/mekhovov\.github\.io\/revealline-soundtracks-[0-9]+\/$/.test(
        catalogue.archive.baseURL,
      ) &&
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
      LICENSES.has(track.licenseURL) &&
        safeURL(track.source) &&
        typeof track.credit === 'string' &&
        track.credit.trim().length > 0 &&
        track.credit.length <= 2048,
      'Recording lacks supported redistribution license, source or attribution.',
    );
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
  return { files, totalBytes: total, audioBytes, trackCount: seen.size };
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

export async function verifyPreviewSite(source, { staged = false } = {}) {
  const root = await realpath(source);
  const manifest = await json(root, MANIFEST, 512 * 1024);
  const inventory = await json(root, 'inventory.json', 256 * 1024);
  const catalogue = await json(root, 'preview-catalogue.json', 1024 * 1024);
  const result = validateDeclarations(manifest, inventory, catalogue);
  const actual = new Set();
  for (const name of await readdir(root)) {
    const stat = await lstat(path.join(root, name));
    demand(!stat.isSymbolicLink(), `Symbolic link refused: ${name}`);
    if (!staged && PRIVATE.has(name)) continue;
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
    actual.size === result.files.size && [...actual].every((name) => result.files.has(name)),
    'Public files differ from the exact deployment manifest.',
  );
  const manifestStat = await lstat(path.join(root, MANIFEST));
  demand(result.totalBytes + manifestStat.size < MAX_SITE_BYTES, 'Site exceeds its 800 MB budget.');
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
  return { ...result, root, manifestSha256, totalBytes: result.totalBytes + manifestStat.size };
}

export async function stagePreviewSite(source, destination) {
  const verified = await verifyPreviewSite(source);
  const parent = await realpath(path.dirname(path.resolve(destination)));
  const target = path.join(parent, path.basename(destination));
  demand(
    target !== verified.root && !target.startsWith(path.join(verified.root, 'objects') + path.sep),
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
    { path: MANIFEST, bytes: (await lstat(path.join(verified.root, MANIFEST))).size },
  ];
  for (const entry of entries) {
    await reserve();
    const original = path.join(verified.root, entry.path);
    const output = path.join(target, entry.path);
    demand(!(await lstat(original)).isSymbolicLink(), 'Source became a symlink during staging.');
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
    staged.manifestSha256 === verified.manifestSha256,
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
    else throw new Error('Usage: node verify.mjs [--root SOURCE] [--stage NEW_DIRECTORY]');
  }
  const result = stage ? await stagePreviewSite(source, stage) : await verifyPreviewSite(source);
  console.log(
    JSON.stringify(
      {
        verified: true,
        tracks: result.trackCount,
        audioBytes: result.audioBytes,
        publicBytes: result.totalBytes,
        manifestSha256: result.manifestSha256,
        staged: Boolean(stage),
      },
      null,
      2,
    ),
  );
}
