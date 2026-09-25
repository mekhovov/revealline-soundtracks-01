import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import {
  allowsLegacyRightsArchive,
  validateRecordingRights,
} from "../rights-policy.mjs";

const root = path.resolve(fileURLToPath(new URL("..", import.meta.url)));
const digest = (bytes) => createHash("sha256").update(bytes).digest("hex");
const readJSON = async (repositoryRoot, overrides, file) => {
  const bytes =
    overrides?.get(file) ?? (await readFile(path.join(repositoryRoot, file)));
  return { bytes, value: JSON.parse(bytes) };
};

function demand(value, message) {
  if (!value) throw new Error(message);
}

function normalizedTags(track) {
  const source = Array.isArray(track.tags)
    ? [
        ...track.tags,
        ...(track.genres ?? []),
        ...(track.substyles ?? []),
        ...(track.creatorSubstyles ?? []),
        track.family,
        track.role,
      ]
    : [
        ...(track.genres ?? []),
        ...(track.substyles ?? []),
        ...(track.creatorSubstyles ?? []),
        track.family,
        track.role,
        ...(track.tags?.genres ?? []),
        ...(track.tags?.themes ?? []),
        track.tags?.role,
        Number.isFinite(track.tags?.energy)
          ? `energy ${track.tags.energy}`
          : null,
      ];
  return [...new Set(source.filter(Boolean).map((tag) => String(tag).trim()))];
}

function publicTrack(
  track,
  { batchId, rightsArchiveId, basePath, status, listeningApproval, admitted },
) {
  const rights = validateRecordingRights(track, {
    allowLegacy: allowsLegacyRightsArchive(rightsArchiveId),
  });
  demand(
    typeof track.id === "string" && track.id,
    "Track identity is required.",
  );
  demand(
    typeof track.title === "string" && track.title,
    `Missing title for ${track.id}.`,
  );
  demand(
    typeof track.artist === "string" && track.artist,
    `Missing artist for ${track.id}.`,
  );
  demand(/^[a-f0-9]{64}$/.test(track.sha256), `Invalid hash for ${track.id}.`);
  demand(
    Number.isSafeInteger(track.bytes) && track.bytes > 0,
    `Invalid bytes for ${track.id}.`,
  );
  demand(
    typeof track.path === "string" &&
      /^objects\/[a-f0-9]{64}\.mp3$/.test(track.path),
    `Invalid MP3 path for ${track.id}.`,
  );
  demand(
    track.path === `objects/${track.sha256}.mp3`,
    `MP3 hash path differs for ${track.id}.`,
  );
  return {
    id: track.id,
    title: track.title,
    artist: track.artist,
    durationSeconds: Number.isFinite(track.durationSeconds)
      ? track.durationSeconds
      : null,
    tags: normalizedTags(track),
    source: track.source,
    license: track.license ?? null,
    licenseURL: track.licenseURL,
    credit: track.credit,
    ...(rights ? { rights } : {}),
    fileName: track.fileName ?? `${track.title}.mp3`,
    archiveId: batchId,
    collection: batchId === "foundation-70" ? "Foundation collection" : batchId,
    status,
    listeningApproval,
    gameCatalogueAdmission: admitted === true,
    ...(track.default === false ? { default: false } : {}),
    contentId: track.contentId ?? "unknown",
    recordingModeEligible:
      rights?.shareAlike.required === true
        ? false
        : track.recordingModeEligible === true,
    audio: {
      path: `${basePath}${track.path}`,
      bytes: track.bytes,
      sha256: track.sha256,
    },
    aliases: [],
  };
}

export async function buildUnifiedCatalogue({
  repositoryRoot = root,
  overrides = new Map(),
} = {}) {
  const rootCatalogue = await readJSON(
    repositoryRoot,
    overrides,
    "preview-catalogue.json",
  );
  const batchIndex = await readJSON(repositoryRoot, overrides, "batches.json");
  demand(
    rootCatalogue.value.format === "revealline-licensed-preview-catalogue.v1",
    "Unexpected root catalogue format.",
  );
  demand(batchIndex.value.batches.length <= 32, "Too many published batches.");
  const batchIds = new Set();
  demand(
    batchIndex.value.format === "revealline-soundtrack-preview-batches.v1",
    "Unexpected batch index format.",
  );

  const sourceCatalogues = [
    {
      id: "foundation-70",
      path: "preview-catalogue.json",
      basePath: "",
      catalogue: rootCatalogue.value,
      sha256: digest(rootCatalogue.bytes),
    },
  ];
  for (const declaration of batchIndex.value.batches) {
    demand(
      typeof declaration.id === "string" &&
        /^[a-z0-9][a-z0-9-]{0,63}$/.test(declaration.id) &&
        !batchIds.has(declaration.id),
      "Invalid or duplicate batch identity.",
    );
    batchIds.add(declaration.id);
    const file = `batches/${declaration.id}/preview-catalogue.json`;
    const loaded = await readJSON(repositoryRoot, overrides, file);
    demand(
      loaded.value.archive?.id === declaration.id,
      `Batch catalogue identity differs: ${declaration.id}.`,
    );
    sourceCatalogues.push({
      id: declaration.id,
      path: file,
      basePath: `batches/${declaration.id}/`,
      catalogue: loaded.value,
      sha256: digest(loaded.bytes),
    });
  }

  const byHash = new Map();
  const byId = new Set();
  let declaredTracks = 0;
  for (const source of sourceCatalogues) {
    for (const track of source.catalogue.tracks) {
      declaredTracks++;
      demand(!byId.has(track.id), `Duplicate track identity: ${track.id}.`);
      byId.add(track.id);
      const existing = byHash.get(track.sha256);
      if (existing) {
        existing.aliases.push({
          id: track.id,
          title: track.title,
          archiveId: source.id,
        });
        continue;
      }
      byHash.set(
        track.sha256,
        publicTrack(track, {
          batchId: source.id,
          rightsArchiveId: source.catalogue.archive.id,
          basePath: source.basePath,
          status: source.catalogue.status,
          listeningApproval: source.catalogue.listeningApproval,
          admitted: source.catalogue.gameCatalogueAdmission,
        }),
      );
    }
  }

  const tracks = [...byHash.values()];
  demand(tracks.length <= 256, "Unified catalogue exceeds 256 recordings.");
  const audioBytes = tracks.reduce((sum, track) => sum + track.audio.bytes, 0);
  return {
    format: "revealline-public-soundtrack-catalogue.v1",
    archive: {
      id: "revealline-soundtracks-01",
      baseURL: "https://mekhovov.github.io/revealline-soundtracks-01/",
    },
    sources: sourceCatalogues.map(({ id, path: file, sha256, catalogue }) => ({
      id,
      path: file,
      sha256,
      status: catalogue.status,
      listeningApproval: catalogue.listeningApproval,
      gameCatalogueAdmission: catalogue.gameCatalogueAdmission === true,
      declaredTracks: catalogue.tracks.length,
    })),
    counts: {
      declaredTracks,
      uniqueRecordings: tracks.length,
      duplicateAliases: declaredTracks - tracks.length,
      audioBytes,
    },
    tracks,
  };
}

export function serializeCatalogue(catalogue) {
  return `${JSON.stringify(catalogue, null, 2)}\n`;
}

if (
  process.argv[1] &&
  path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  const catalogue = await buildUnifiedCatalogue();
  const serialized = serializeCatalogue(catalogue);
  const output = path.join(root, "catalogue.json");
  if (process.argv.includes("--write")) {
    await writeFile(output, serialized);
    console.log(
      `Wrote ${catalogue.counts.uniqueRecordings} unique recordings from ${catalogue.sources.length} collections.`,
    );
  } else if (process.argv.includes("--check")) {
    const current = await readFile(output, "utf8");
    demand(
      current === serialized,
      "catalogue.json is stale; run with --write.",
    );
    console.log(
      `Verified ${catalogue.counts.uniqueRecordings} unique recordings from ${catalogue.sources.length} collections.`,
    );
  } else {
    throw new Error(
      "Usage: node intake/build-unified-catalogue.mjs --write|--check",
    );
  }
}
