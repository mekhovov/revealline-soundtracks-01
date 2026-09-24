import { constants } from "node:fs";
import { createHash, randomBytes } from "node:crypto";
import {
  lstat,
  mkdir,
  open,
  readFile,
  rename,
  rm,
  statfs,
  writeFile,
} from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  buildUnifiedCatalogue,
  serializeCatalogue,
} from "./build-unified-catalogue.mjs";
import { buildUpdatedRootManifest } from "./update-root-metadata.mjs";
import { validateBatchIndex, verifyPreviewBatch } from "../verify.mjs";

const repository = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const BATCH_ID = /^[a-z0-9][a-z0-9-]{0,63}$/;
const TRACK_ID = /^[a-z0-9][a-z0-9._-]{0,159}$/;
const MAX_TRACK_BYTES = 100_000_000;
const MAX_BATCH_BYTES = 64 * 1024 * 1024;
const MAX_PUBLIC_BYTES = 800_000_000;
const MINIMUM_FREE_BYTES = 1024 ** 3;
const LICENSES = new Map([
  ["https://creativecommons.org/publicdomain/zero/1.0/", "CC0 1.0 Universal"],
  ["https://creativecommons.org/licenses/by/3.0/", "CC BY 3.0 Unported"],
  ["https://creativecommons.org/licenses/by/4.0/", "CC BY 4.0 International"],
]);
const hash = (bytes) => createHash("sha256").update(bytes).digest("hex");
const pin = (file, bytes) => ({
  path: file,
  bytes: bytes.length,
  sha256: hash(bytes),
});
const json = (value) => Buffer.from(`${JSON.stringify(value, null, 2)}\n`);

function demand(value, message) {
  if (!value) throw new Error(message);
}
function safeURL(value) {
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password;
  } catch {
    return false;
  }
}
function cleanText(value, label, max = 2048) {
  demand(
    typeof value === "string" && value.trim() && value.length <= max,
    `${label} is required.`,
  );
  return value.trim();
}

export function validateUploadManifest(value) {
  demand(
    value && typeof value === "object" && !Array.isArray(value),
    "Upload manifest must be an object.",
  );
  demand(
    BATCH_ID.test(value.batchId),
    "batchId must be lowercase letters, digits and hyphens.",
  );
  const title = cleanText(value.title, "Batch title", 160);
  const description = cleanText(value.description, "Batch description", 500);
  demand(
    Array.isArray(value.tracks) &&
      value.tracks.length >= 1 &&
      value.tracks.length <= 20,
    "A batch needs 1–20 tracks.",
  );
  const ids = new Set();
  const tracks = value.tracks.map((track) => {
    demand(
      track && typeof track === "object" && !Array.isArray(track),
      "Each track must be an object.",
    );
    demand(
      TRACK_ID.test(track.id) && !ids.has(track.id),
      "Track IDs must be unique lowercase identifiers.",
    );
    ids.add(track.id);
    demand(
      safeURL(track.source),
      `A secure creator source is required for ${track.id}.`,
    );
    demand(
      LICENSES.has(track.licenseURL),
      `Unsupported licence for ${track.id}.`,
    );
    demand(
      track.license === LICENSES.get(track.licenseURL),
      `Licence label and URL differ for ${track.id}.`,
    );
    demand(
      Array.isArray(track.tags) &&
        track.tags.length >= 1 &&
        track.tags.length <= 16,
      `Tags are required for ${track.id}.`,
    );
    return {
      id: track.id,
      file: cleanText(track.file, `File for ${track.id}`, 4096),
      title: cleanText(track.title, `Title for ${track.id}`, 200),
      artist: cleanText(track.artist, `Artist for ${track.id}`, 200),
      source: track.source,
      license: track.license,
      licenseURL: track.licenseURL,
      credit: cleanText(track.credit, `Credit for ${track.id}`),
      tags: [
        ...new Set(
          track.tags.map((tag) => cleanText(tag, `Tag for ${track.id}`, 80)),
        ),
      ],
    };
  });
  return { batchId: value.batchId, title, description, tracks };
}

function mp3Signature(bytes) {
  return (
    bytes.subarray(0, 3).toString("ascii") === "ID3" ||
    (bytes[0] === 0xff && (bytes[1] & 0xe0) === 0xe0)
  );
}
const escapeHTML = (value) =>
  String(value).replace(
    /[&<>"']/g,
    (character) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        character
      ],
  );

async function ordinaryDirectory(directory, label) {
  const stat = await lstat(directory);
  demand(
    stat.isDirectory() && !stat.isSymbolicLink(),
    `${label} must be an ordinary directory.`,
  );
}
async function absent(target, label) {
  try {
    await lstat(target);
    throw new Error(`${label} already exists.`);
  } catch (error) {
    if (error.code !== "ENOENT") throw error;
  }
}
async function stableFileBytes(file, expectedSize) {
  const handle = await open(file, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const before = await handle.stat();
    demand(
      before.isFile() && before.size === expectedSize,
      `MP3 changed before reading: ${file}.`,
    );
    const bytes = Buffer.allocUnsafe(expectedSize);
    let offset = 0;
    while (offset < expectedSize) {
      const result = await handle.read(
        bytes,
        offset,
        expectedSize - offset,
        offset,
      );
      demand(result.bytesRead > 0, `MP3 ended while reading: ${file}.`);
      offset += result.bytesRead;
    }
    const extra = Buffer.allocUnsafe(1);
    const overflow = await handle.read(extra, 0, 1, expectedSize);
    const after = await handle.stat();
    demand(
      overflow.bytesRead === 0 &&
        after.size === before.size &&
        after.mtimeMs === before.mtimeMs &&
        after.ctimeMs === before.ctimeMs,
      `MP3 changed while reading: ${file}.`,
    );
    return bytes;
  } finally {
    await handle.close();
  }
}
async function currentPublicBytes(repositoryRoot, batches) {
  const rootManifestBytes = await readFile(
    path.join(repositoryRoot, "deployment-manifest.json"),
  );
  const rootManifest = JSON.parse(rootManifestBytes);
  let total =
    rootManifestBytes.length +
    rootManifest.files.reduce((sum, file) => sum + file.bytes, 0);
  const batchIndexBytes = await readFile(
    path.join(repositoryRoot, "batches.json"),
  );
  total += batchIndexBytes.length;
  for (const declaration of batches) {
    const bytes = await readFile(
      path.join(repositoryRoot, declaration.manifest.path),
    );
    demand(
      bytes.length === declaration.manifest.bytes &&
        hash(bytes) === declaration.manifest.sha256,
      `Batch manifest pin differs: ${declaration.id}.`,
    );
    const value = JSON.parse(bytes);
    total +=
      bytes.length + value.files.reduce((sum, file) => sum + file.bytes, 0);
  }
  return total;
}

function batchFiles(manifest, prepared) {
  const catalogue = {
    format: "revealline-licensed-preview-catalogue.v1",
    status: "licensed-preview",
    listeningApproval: "not-reviewed",
    gameCatalogueAdmission: false,
    archive: {
      id: manifest.batchId,
      baseURL: `https://mekhovov.github.io/revealline-soundtracks-01/batches/${manifest.batchId}/`,
      inventorySha256: "",
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
      contentId: "unknown",
      recordingModeEligible: false,
      fileName: track.fileName,
      path: `objects/${track.sha256}.mp3`,
      bytes: track.bytes.length,
      sha256: track.sha256,
    })),
  };
  const inventory = {
    format: "revealline-soundtrack-archive.v1",
    id: manifest.batchId,
    files: catalogue.tracks.map((track) => ({
      path: track.path,
      bytes: track.bytes,
      sha256: track.sha256,
    })),
  };
  const inventoryBytes = json(inventory);
  catalogue.archive.inventorySha256 = hash(inventoryBytes);
  const catalogueBytes = json(catalogue);
  const cards = catalogue.tracks
    .map(
      (track) =>
        `<article><h2>${escapeHTML(track.title)}</h2><p>${escapeHTML(track.artist)}</p><audio controls preload="metadata" src="${track.path}"></audio><p><a href="${track.path}" download="${escapeHTML(track.fileName)}">MP3 ↓</a> · <a href="${escapeHTML(track.source)}">Creator source ↗</a> · <a href="${escapeHTML(track.licenseURL)}">${escapeHTML(track.license)}</a></p></article>`,
    )
    .join("\n");
  const files = new Map([
    [".nojekyll", Buffer.alloc(0)],
    [
      "README.md",
      Buffer.from(
        `# ${manifest.title}\n\n${manifest.description}\n\nListening review and game catalogue admission are pending.\n`,
      ),
    ],
    [
      "CREDITS.md",
      Buffer.from(
        `# Credits\n\n${catalogue.tracks.map((track) => `- **${track.title}** — ${track.artist}. ${track.credit} [Source](${track.source}) · [${track.license}](${track.licenseURL}) · SHA-256 \`${track.sha256}\`.`).join("\n")}\n`,
      ),
    ],
    [
      "index.html",
      Buffer.from(
        `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHTML(manifest.title)} · RevealLine</title><link rel="stylesheet" href="style.css"></head><body><main><p><a href="../../">← All RevealLine soundtracks</a></p><h1>${escapeHTML(manifest.title)}</h1><p>${escapeHTML(manifest.description)}</p><p><strong>Listening review pending.</strong> Publication does not mean game-playlist admission.</p>${cards}</main><script src="player.mjs" type="module"></script></body></html>\n`,
      ),
    ],
    [
      "style.css",
      Buffer.from(
        "body{margin:0;background:#090b0f;color:#f5f1e7;font:16px/1.5 system-ui,sans-serif}main{width:min(850px,92%);margin:3rem auto}a{color:#f4d638}article{border-top:1px solid #343e4b;padding:1.25rem 0}audio{width:100%;max-width:520px}h1{font-size:clamp(2rem,7vw,4rem)}\n",
      ),
    ],
    [
      "player.mjs",
      Buffer.from(
        "// Batch audio uses native controls; the unified root player owns endless playback.\n",
      ),
    ],
    ["inventory.json", inventoryBytes],
    ["preview-catalogue.json", catalogueBytes],
  ]);
  for (const track of prepared)
    files.set(`objects/${track.sha256}.mp3`, track.bytes);
  return { files, catalogueBytes };
}

export async function commitTransaction({
  repositoryRoot,
  batchId,
  transactionRoot,
  stageBatch,
  rootFiles,
  operations = {},
}) {
  const move = operations.rename ?? rename;
  const remove = operations.rm ?? rm;
  const finalBatch = path.join(repositoryRoot, "batches", batchId);
  const backups = path.join(transactionRoot, "backups");
  await mkdir(backups);
  const replaced = [];
  let batchMoved = false;
  try {
    await move(stageBatch, finalBatch);
    batchMoved = true;
    for (const name of rootFiles.keys()) {
      await move(path.join(repositoryRoot, name), path.join(backups, name));
      replaced.push(name);
      await move(
        path.join(transactionRoot, "new", name),
        path.join(repositoryRoot, name),
      );
    }
  } catch (error) {
    const rollbackErrors = [];
    for (const name of [...replaced].reverse()) {
      try {
        await remove(path.join(repositoryRoot, name), { force: true });
        await move(path.join(backups, name), path.join(repositoryRoot, name));
      } catch (rollbackError) {
        rollbackErrors.push(rollbackError);
      }
    }
    if (batchMoved) {
      try {
        await remove(finalBatch, { recursive: true, force: true });
      } catch (rollbackError) {
        rollbackErrors.push(rollbackError);
      }
    }
    if (rollbackErrors.length) {
      const recovery = new AggregateError(
        [error, ...rollbackErrors],
        `Upload commit and rollback failed. Recovery files are retained at ${transactionRoot}.`,
      );
      recovery.preserveTransaction = true;
      throw recovery;
    }
    throw error;
  }
}

export async function prepareUpload(manifestPath, options = {}) {
  const repositoryRoot = path.resolve(options.repositoryRoot ?? repository);
  const absoluteManifest = path.resolve(manifestPath);
  await ordinaryDirectory(repositoryRoot, "Repository root");
  await ordinaryDirectory(path.join(repositoryRoot, "batches"), "batches");
  await ordinaryDirectory(path.join(repositoryRoot, "intake"), "intake");
  const manifestStat = await lstat(absoluteManifest);
  demand(
    manifestStat.isFile() &&
      !manifestStat.isSymbolicLink() &&
      manifestStat.size <= 512 * 1024,
    "Upload manifest must be a bounded ordinary file.",
  );
  const manifest = validateUploadManifest(
    JSON.parse(await readFile(absoluteManifest, "utf8")),
  );
  const lockPath = path.join(repositoryRoot, "intake", ".upload.lock");
  let lock;
  try {
    lock = await open(lockPath, "wx");
    try {
      await lock.writeFile(
        `${JSON.stringify({ pid: process.pid, batchId: manifest.batchId })}\n`,
      );
    } catch (error) {
      await lock.close();
      await rm(lockPath, { force: true });
      throw error;
    }
  } catch (error) {
    if (error.code === "EEXIST")
      throw new Error(
        "Another soundtrack upload owns the archive writer lock.",
      );
    throw error;
  }
  try {
    const batchRoot = path.join(repositoryRoot, "batches", manifest.batchId);
    await absent(batchRoot, `Batch ${manifest.batchId}`);

    const batchesValue = JSON.parse(
      await readFile(path.join(repositoryRoot, "batches.json"), "utf8"),
    );
    const batches = validateBatchIndex(batchesValue);
    demand(
      batches.length < 32,
      "The public archive already contains 32 batches.",
    );
    const currentCatalogue = JSON.parse(
      await readFile(path.join(repositoryRoot, "catalogue.json"), "utf8"),
    );
    demand(
      currentCatalogue?.format === "revealline-public-soundtrack-catalogue.v1",
      "Unexpected unified catalogue.",
    );
    const knownIds = new Set();
    const knownHashes = new Set();
    for (const track of currentCatalogue.tracks) {
      knownIds.add(track.id);
      for (const alias of track.aliases ?? []) knownIds.add(alias.id);
      knownHashes.add(track.audio.sha256);
    }
    for (const track of manifest.tracks)
      demand(
        !knownIds.has(track.id),
        `Recording identity already exists: ${track.id}.`,
      );
    demand(
      currentCatalogue.counts.declaredTracks + manifest.tracks.length <= 256,
      "Unified catalogue may contain at most 256 recordings.",
    );

    const sources = [];
    let audioBytes = 0;
    for (const track of manifest.tracks) {
      const sourcePath = path.resolve(
        path.dirname(absoluteManifest),
        track.file,
      );
      const stat = await lstat(sourcePath);
      demand(
        stat.isFile() && !stat.isSymbolicLink(),
        `MP3 must be an ordinary file: ${track.file}.`,
      );
      demand(
        stat.size > 0 && stat.size < MAX_TRACK_BYTES,
        `MP3 size is invalid: ${track.file}.`,
      );
      audioBytes += stat.size;
      demand(
        audioBytes <= MAX_BATCH_BYTES,
        "A public batch may contain at most 64 MiB of audio.",
      );
      sources.push({
        ...track,
        sourcePath,
        expectedSize: stat.size,
        fileName: path.basename(sourcePath),
      });
    }
    const existingPublicBytes = await currentPublicBytes(
      repositoryRoot,
      batches,
    );
    demand(
      existingPublicBytes + audioBytes + 8 * 1024 * 1024 < MAX_PUBLIC_BYTES,
      "The public archive would exceed its 800 MB budget.",
    );
    const available =
      options.availableBytes ??
      (async () => {
        const disk = await statfs(repositoryRoot);
        return disk.bavail * disk.bsize;
      });
    const freeBytes = await available(repositoryRoot);
    const minimumFreeBytes = options.minimumFreeBytes ?? MINIMUM_FREE_BYTES;
    demand(
      freeBytes >= minimumFreeBytes + audioBytes + 8 * 1024 * 1024,
      "Upload must leave at least 1 GiB free.",
    );

    const prepared = [];
    for (const source of sources) {
      const bytes = await stableFileBytes(
        source.sourcePath,
        source.expectedSize,
      );
      demand(
        mp3Signature(bytes),
        `File does not begin with an MP3 signature: ${source.file}.`,
      );
      const sha256 = hash(bytes);
      demand(
        !knownHashes.has(sha256),
        `Exact recording already exists: ${source.file}.`,
      );
      knownHashes.add(sha256);
      prepared.push({ ...source, bytes, sha256 });
    }

    const generated = batchFiles(manifest, prepared);
    const deployment = {
      format: "revealline-soundtrack-preview-deployment.v1",
      id: manifest.batchId,
      expected: { trackCount: prepared.length, audioBytes },
      files: [...generated.files].map(([name, bytes]) => pin(name, bytes)),
      provenance: { localUpload: true, listeningApproval: false },
    };
    const deploymentBytes = json(deployment);
    const updatedBatches = {
      ...batchesValue,
      batches: [
        ...batches,
        {
          id: manifest.batchId,
          manifest: pin(
            `batches/${manifest.batchId}/deployment-manifest.json`,
            deploymentBytes,
          ),
        },
      ],
    };
    validateBatchIndex(updatedBatches);
    const batchesBytes = json(updatedBatches);
    const overrides = new Map([
      ["batches.json", batchesBytes],
      [
        `batches/${manifest.batchId}/preview-catalogue.json`,
        generated.catalogueBytes,
      ],
    ]);
    const unified = await buildUnifiedCatalogue({ repositoryRoot, overrides });
    demand(
      unified.counts.declaredTracks <= 256 &&
        unified.counts.uniqueRecordings <= 256,
      "Unified catalogue exceeds 256 recordings.",
    );
    const catalogueBytes = Buffer.from(serializeCatalogue(unified));
    overrides.set("catalogue.json", catalogueBytes);
    const rootManifest = await buildUpdatedRootManifest({
      repositoryRoot,
      overrides,
    });
    const rootFiles = new Map([
      ["batches.json", batchesBytes],
      ["catalogue.json", catalogueBytes],
      ["deployment-manifest.json", rootManifest.bytes],
    ]);

    await options.beforeCommit?.({
      prepared: prepared.map(({ bytes, ...track }) => ({
        ...track,
        bytes: bytes.length,
      })),
    });
    const token = `${manifest.batchId}-${process.pid}-${randomBytes(6).toString("hex")}`;
    const transactionRoot = path.join(
      repositoryRoot,
      "intake",
      `.upload-${token}`,
    );
    const stageBatch = path.join(transactionRoot, "batch");
    let preserveTransaction = false;
    try {
      await mkdir(path.join(stageBatch, "objects"), { recursive: true });
      for (const [name, bytes] of generated.files)
        await writeFile(path.join(stageBatch, name), bytes, { flag: "wx" });
      await writeFile(
        path.join(stageBatch, "deployment-manifest.json"),
        deploymentBytes,
        { flag: "wx" },
      );
      await verifyPreviewBatch(stageBatch, {
        id: manifest.batchId,
        baseURL: "https://mekhovov.github.io/revealline-soundtracks-01/",
        manifest: pin(
          `batches/${manifest.batchId}/deployment-manifest.json`,
          deploymentBytes,
        ),
      });
      await mkdir(path.join(transactionRoot, "new"));
      for (const [name, bytes] of rootFiles)
        await writeFile(path.join(transactionRoot, "new", name), bytes, {
          flag: "wx",
        });
      await absent(batchRoot, `Batch ${manifest.batchId}`);
      await commitTransaction({
        repositoryRoot,
        batchId: manifest.batchId,
        transactionRoot,
        stageBatch,
        rootFiles,
      });
    } catch (error) {
      preserveTransaction = error.preserveTransaction === true;
      throw error;
    } finally {
      if (!preserveTransaction)
        await rm(transactionRoot, { recursive: true, force: true });
    }
    return { batchId: manifest.batchId, tracks: prepared.length, audioBytes };
  } finally {
    try {
      await lock.close();
    } finally {
      await rm(lockPath, { force: true });
    }
  }
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const position = process.argv.indexOf("--manifest");
  demand(
    position >= 0 && process.argv[position + 1],
    "Usage: node intake/add-upload.mjs --manifest FILE.json",
  );
  const result = await prepareUpload(process.argv[position + 1]);
  console.log(`Prepared ${result.tracks} recording(s) in ${result.batchId}.`);
}
