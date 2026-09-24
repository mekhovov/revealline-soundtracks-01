import { createHash } from 'node:crypto';
import { copyFile, mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { buildUnifiedCatalogue, serializeCatalogue } from './build-unified-catalogue.mjs';
import { updateRootMetadataPins } from './update-root-metadata.mjs';

const repository = path.resolve(fileURLToPath(new URL('..', import.meta.url)));
const BATCH_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
const TRACK_ID = /^[a-z0-9][a-z0-9._-]{0,159}$/;
const LICENSES = new Map([
  ['https://creativecommons.org/publicdomain/zero/1.0/', 'CC0 1.0 Universal'],
  ['https://creativecommons.org/licenses/by/3.0/', 'CC BY 3.0 Unported'],
  ['https://creativecommons.org/licenses/by/4.0/', 'CC BY 4.0 International'],
]);
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const pin = (file, bytes) => ({ path: file, bytes: bytes.length, sha256: hash(bytes) });
const json = (value) => Buffer.from(`${JSON.stringify(value, null, 2)}\n`);

function demand(value, message) {
  if (!value) throw new Error(message);
}
function safeURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === 'https:' && !url.username && !url.password;
  } catch {
    return false;
  }
}
function cleanText(value, label, max = 2048) {
  demand(typeof value === 'string' && value.trim() && value.length <= max, `${label} is required.`);
  return value.trim();
}

export function validateUploadManifest(value) {
  demand(value && typeof value === 'object' && !Array.isArray(value), 'Upload manifest must be an object.');
  demand(BATCH_ID.test(value.batchId), 'batchId must be lowercase letters, digits and hyphens.');
  const title = cleanText(value.title, 'Batch title', 160);
  const description = cleanText(value.description, 'Batch description', 500);
  demand(Array.isArray(value.tracks) && value.tracks.length >= 1 && value.tracks.length <= 20, 'A batch needs 1–20 tracks.');
  const ids = new Set();
  const tracks = value.tracks.map((track) => {
    demand(track && typeof track === 'object' && !Array.isArray(track), 'Each track must be an object.');
    demand(TRACK_ID.test(track.id) && !ids.has(track.id), 'Track IDs must be unique lowercase identifiers.');
    ids.add(track.id);
    demand(safeURL(track.source), `A secure creator source is required for ${track.id}.`);
    demand(LICENSES.has(track.licenseURL), `Unsupported licence for ${track.id}.`);
    demand(track.license === LICENSES.get(track.licenseURL), `Licence label and URL differ for ${track.id}.`);
    demand(Array.isArray(track.tags) && track.tags.length >= 1 && track.tags.length <= 16, `Tags are required for ${track.id}.`);
    return {
      id: track.id,
      file: cleanText(track.file, `File for ${track.id}`, 4096),
      title: cleanText(track.title, `Title for ${track.id}`, 200),
      artist: cleanText(track.artist, `Artist for ${track.id}`, 200),
      source: track.source,
      license: track.license,
      licenseURL: track.licenseURL,
      credit: cleanText(track.credit, `Credit for ${track.id}`),
      tags: [...new Set(track.tags.map((tag) => cleanText(tag, `Tag for ${track.id}`, 80)))],
    };
  });
  return { batchId: value.batchId, title, description, tracks };
}

function mp3Signature(bytes) {
  return (
    bytes.subarray(0, 3).toString('ascii') === 'ID3' ||
    (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)
  );
}
const escapeHTML = (value) =>
  String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);

export async function prepareUpload(manifestPath) {
  const absoluteManifest = path.resolve(manifestPath);
  const manifest = validateUploadManifest(JSON.parse(await readFile(absoluteManifest, 'utf8')));
  const batchRoot = path.join(repository, 'batches', manifest.batchId);
  try {
    await readFile(path.join(batchRoot, 'deployment-manifest.json'));
    throw new Error(`Batch already exists: ${manifest.batchId}.`);
  } catch (error) {
    if (error.code !== 'ENOENT') throw error;
  }
  const currentCatalogue = JSON.parse(await readFile(path.join(repository, 'catalogue.json'), 'utf8'));
  const knownHashes = new Set(currentCatalogue.tracks.map((track) => track.audio.sha256));
  const prepared = [];
  let audioBytes = 0;
  for (const track of manifest.tracks) {
    const sourcePath = path.resolve(path.dirname(absoluteManifest), track.file);
    const bytes = await readFile(sourcePath);
    demand(bytes.length > 0 && bytes.length < 100_000_000, `MP3 size is invalid: ${track.file}.`);
    demand(mp3Signature(bytes), `File does not begin with an MP3 signature: ${track.file}.`);
    const sha256 = hash(bytes);
    demand(!knownHashes.has(sha256), `Exact recording already exists: ${track.file}.`);
    knownHashes.add(sha256);
    audioBytes += bytes.length;
    prepared.push({ ...track, sourcePath, bytes, sha256, fileName: path.basename(sourcePath) });
  }
  demand(audioBytes <= 64 * 1024 * 1024, 'A public batch may contain at most 64 MiB of audio.');

  await mkdir(path.join(batchRoot, 'objects'), { recursive: true });
  const catalogue = {
    format: 'revealline-licensed-preview-catalogue.v1',
    status: 'licensed-preview',
    listeningApproval: 'not-reviewed',
    gameCatalogueAdmission: false,
    archive: {
      id: manifest.batchId,
      baseURL: `https://mekhovov.github.io/revealline-soundtracks-01/batches/${manifest.batchId}/`,
      inventorySha256: '',
    },
    tracks: prepared.map((track) => ({
      id: track.id,
      title: track.title,
      artist: track.artist,
      source: track.source,
      license: track.license,
      licenseURL: track.licenseURL,
      credit: track.credit,
      tags: track.tags,
      fileName: track.fileName,
      path: `objects/${track.sha256}.mp3`,
      bytes: track.bytes.length,
      sha256: track.sha256,
    })),
  };
  const inventory = {
    format: 'revealline-soundtrack-archive.v1',
    id: manifest.batchId,
    files: catalogue.tracks.map((track) => ({ path: track.path, bytes: track.bytes, sha256: track.sha256 })),
  };
  const inventoryBytes = json(inventory);
  catalogue.archive.inventorySha256 = hash(inventoryBytes);
  const catalogueBytes = json(catalogue);
  const cards = catalogue.tracks.map((track) => `<article><h2>${escapeHTML(track.title)}</h2><p>${escapeHTML(track.artist)}</p><audio controls preload="metadata" src="${track.path}"></audio><p><a href="${track.path}" download="${escapeHTML(track.fileName)}">MP3 ↓</a> · <a href="${escapeHTML(track.source)}">Creator source ↗</a> · <a href="${escapeHTML(track.licenseURL)}">${escapeHTML(track.license)}</a></p></article>`).join('\n');
  const html = Buffer.from(`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHTML(manifest.title)} · RevealLine</title><link rel="stylesheet" href="style.css"></head><body><main><p><a href="../../">← All RevealLine soundtracks</a></p><h1>${escapeHTML(manifest.title)}</h1><p>${escapeHTML(manifest.description)}</p><p><strong>Listening review pending.</strong> Publication does not mean game-playlist admission.</p>${cards}</main><script src="player.mjs" type="module"></script></body></html>\n`);
  const style = Buffer.from('body{margin:0;background:#090b0f;color:#f5f1e7;font:16px/1.5 system-ui,sans-serif}main{width:min(850px,92%);margin:3rem auto}a{color:#f4d638}article{border-top:1px solid #343e4b;padding:1.25rem 0}audio{width:100%;max-width:520px}h1{font-size:clamp(2rem,7vw,4rem)}\n');
  const player = Buffer.from("// Batch audio uses native controls; the unified root player owns endless playback.\n");
  const readme = Buffer.from(`# ${manifest.title}\n\n${manifest.description}\n\nListening review and game catalogue admission are pending.\n`);
  const credits = Buffer.from(`# Credits\n\n${catalogue.tracks.map((track) => `- **${track.title}** — ${track.artist}. ${track.credit} [Source](${track.source}) · [${track.license}](${track.licenseURL}) · SHA-256 \`${track.sha256}\`.`).join('\n')}\n`);
  const files = new Map([
    ['.nojekyll', Buffer.alloc(0)], ['README.md', readme], ['CREDITS.md', credits],
    ['index.html', html], ['style.css', style], ['player.mjs', player],
    ['inventory.json', inventoryBytes], ['preview-catalogue.json', catalogueBytes],
  ]);
  for (const track of prepared) {
    const objectPath = `objects/${track.sha256}.mp3`;
    await copyFile(track.sourcePath, path.join(batchRoot, objectPath));
    files.set(objectPath, track.bytes);
  }
  for (const [name, bytes] of files) if (!name.startsWith('objects/')) await writeFile(path.join(batchRoot, name), bytes);
  const deployment = {
    format: 'revealline-soundtrack-preview-deployment.v1', id: manifest.batchId,
    expected: { trackCount: prepared.length, audioBytes },
    files: [...files].map(([name, bytes]) => pin(name, bytes)),
    provenance: { localUpload: true, listeningApproval: false },
  };
  const deploymentBytes = json(deployment);
  await writeFile(path.join(batchRoot, 'deployment-manifest.json'), deploymentBytes);
  const batchesPath = path.join(repository, 'batches.json');
  const batches = JSON.parse(await readFile(batchesPath, 'utf8'));
  batches.batches.push({ id: manifest.batchId, manifest: pin(`batches/${manifest.batchId}/deployment-manifest.json`, deploymentBytes) });
  await writeFile(batchesPath, json(batches));
  await writeFile(path.join(repository, 'catalogue.json'), serializeCatalogue(await buildUnifiedCatalogue()));
  await updateRootMetadataPins();
  return { batchId: manifest.batchId, tracks: prepared.length, audioBytes };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const position = process.argv.indexOf('--manifest');
  demand(position >= 0 && process.argv[position + 1], 'Usage: node intake/add-upload.mjs --manifest FILE.json');
  const result = await prepareUpload(process.argv[position + 1]);
  console.log(`Prepared ${result.tracks} recording(s) in ${result.batchId}.`);
}
