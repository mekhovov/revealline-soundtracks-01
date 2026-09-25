import { constants } from 'node:fs';
import {
  lstat,
  mkdtemp,
  open,
  readdir,
  rm,
  writeFile,
} from 'node:fs/promises';
import { spawn } from 'node:child_process';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { prepareUpload } from './add-upload.mjs';
import {
  LICENSES_BY_KEY,
  createRightsMetadata,
} from '../rights-policy.mjs';

const repository = path.resolve(fileURLToPath(new URL('..', import.meta.url)));

function demand(value, message) {
  if (!value) throw new Error(message);
}
function slug(value, maximum = 64) {
  const result = String(value)
    .normalize('NFKD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, maximum)
    .replace(/-+$/g, '');
  return result || 'soundtrack';
}
function titleFromFile(file) {
  return path
    .basename(file, path.extname(file))
    .replace(/[._-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}
function synchsafe(bytes, offset) {
  return (
    (bytes[offset] << 21) |
    (bytes[offset + 1] << 14) |
    (bytes[offset + 2] << 7) |
    bytes[offset + 3]
  );
}
function decodeTextFrame(bytes) {
  if (!bytes.length) return '';
  const encoding = bytes[0],
    body = bytes.subarray(1);
  let value;
  if (encoding === 0) value = body.toString('latin1');
  else if (encoding === 3) value = body.toString('utf8');
  else {
    let data = body;
    if (encoding === 1 && data[0] === 0xfe && data[1] === 0xff) {
      data = Buffer.from(data.subarray(2));
      data.swap16();
    } else if (encoding === 1 && data[0] === 0xff && data[1] === 0xfe)
      data = data.subarray(2);
    else if (encoding === 2) {
      data = Buffer.from(data);
      data.swap16();
    }
    value = data.toString('utf16le');
  }
  return value.replace(/\0/g, '').trim();
}

export async function readID3(file) {
  const handle = await open(file, constants.O_RDONLY | constants.O_NOFOLLOW);
  try {
    const header = Buffer.alloc(10);
    const first = await handle.read(header, 0, header.length, 0);
    if (first.bytesRead !== 10 || header.subarray(0, 3).toString('ascii') !== 'ID3')
      return {};
    const version = header[3];
    if (![3, 4].includes(version)) return {};
    const tagBytes = Math.min(synchsafe(header, 6), 1024 * 1024);
    const body = Buffer.alloc(tagBytes);
    const result = await handle.read(body, 0, tagBytes, 10);
    const tags = {};
    let offset = 0;
    while (offset + 10 <= result.bytesRead) {
      const id = body.subarray(offset, offset + 4).toString('ascii');
      if (!/^[A-Z0-9]{4}$/.test(id)) break;
      const size =
        version === 4 ? synchsafe(body, offset + 4) : body.readUInt32BE(offset + 4);
      if (size <= 0 || offset + 10 + size > result.bytesRead) break;
      if (id === 'TIT2') tags.title = decodeTextFrame(body.subarray(offset + 10, offset + 10 + size));
      if (id === 'TPE1') tags.artist = decodeTextFrame(body.subarray(offset + 10, offset + 10 + size));
      offset += 10 + size;
    }
    return tags;
  } finally {
    await handle.close();
  }
}

async function mp3Files(input) {
  const found = [];
  async function visit(candidate, depth) {
    demand(depth <= 8, 'Music folder nesting exceeds eight levels.');
    const stat = await lstat(candidate);
    demand(!stat.isSymbolicLink(), `Symbolic links are not accepted: ${candidate}`);
    if (stat.isFile()) {
      if (path.extname(candidate).toLowerCase() === '.mp3') found.push(path.resolve(candidate));
      return;
    }
    demand(stat.isDirectory(), `Music input must be an MP3 or folder: ${candidate}`);
    const entries = await readdir(candidate, { withFileTypes: true });
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name)))
      await visit(path.join(candidate, entry.name), depth + 1);
  }
  await visit(path.resolve(input), 0);
  demand(found.length >= 1, 'No MP3 files were found.');
  demand(found.length <= 20, 'One automated batch is limited to 20 MP3 files.');
  return found;
}

export async function createUploadManifest(input, options) {
  demand(options?.confirmRights === true, 'Pass --confirm-rights after verifying public MP3 redistribution and web-game playback rights.');
  demand(/^https:\/\//.test(options.source ?? ''), 'A secure exact creator/source URL is required.');
  const license = LICENSES_BY_KEY.get(options.license);
  demand(
    license,
    'Use --license cc0, cc-by-3.0, cc-by-4.0, cc-by-sa-3.0 or cc-by-sa-4.0.',
  );
  if (license.shareAlike) {
    demand(
      /^https:\/\//.test(options.rightsEvidence ?? ''),
      'CC BY-SA intake requires --rights-evidence with the exact licence evidence URL.',
    );
    demand(
      options.derivativeNotice?.trim(),
      'CC BY-SA intake requires --derivative-notice describing MP3 conversion or confirming unchanged bytes.',
    );
  }
  const files = await mp3Files(input),
    commonArtist = options.artist?.trim(),
    tags = [...new Set((options.tags ?? []).map((tag) => tag.trim()).filter(Boolean))];
  demand(tags.length >= 1, 'Choose at least one style/tag with --styles.');
  const inputName = titleFromFile(path.resolve(input)),
    date = options.date ?? new Date().toISOString().slice(0, 10).replaceAll('-', ''),
    batchId = options.batchId ?? `${slug(inputName, 48)}-${date}`,
    ids = new Map();
  const tracks = [];
  for (const file of files) {
    const id3 = await readID3(file),
      title = id3.title || titleFromFile(file),
      artist = commonArtist || id3.artist;
    demand(artist, `Artist is missing from ID3 metadata for ${file}; pass --artist.`);
    const base = `${slug(artist, 70)}.${slug(title, 70)}`,
      occurrence = (ids.get(base) ?? 0) + 1;
    ids.set(base, occurrence);
    const id = occurrence === 1 ? base : `${base}.${occurrence}`;
    const credit = `${title} by ${artist}. ${license.label}. Source: ${options.source}`;
    tracks.push({
      id,
      file,
      title,
      artist,
      source: options.source,
      license: license.label,
      licenseURL: license.url,
      credit,
      rights: createRightsMetadata({
        licenseURL: license.url,
        rightsEvidenceURL: options.rightsEvidence ?? options.source,
        attribution: credit,
        derivativeChangeNotice:
          options.derivativeNotice ??
          'Exact submitted MP3 bytes retained; no archive changes declared.',
      }),
      tags,
    });
  }
  return {
    batchId,
    title: options.batchTitle ?? (files.length === 1 ? tracks[0].title : inputName),
    description:
      options.description ??
      `Publicly redistributable music prepared from ${files.length} reviewed MP3 recording${files.length === 1 ? '' : 's'}.`,
    tracks,
  };
}

function parseArguments(argv) {
  const options = { tags: [] }, positional = [];
  for (let index = 0; index < argv.length; index++) {
    const value = argv[index];
    if (!value.startsWith('--')) positional.push(value);
    else if (value === '--confirm-rights') options.confirmRights = true;
    else if (value === '--open-pr') options.openPR = true;
    else {
      const next = argv[++index];
      demand(next, `Missing value after ${value}.`);
      const key = {
        '--source': 'source', '--license': 'license', '--artist': 'artist',
        '--styles': 'tags', '--batch-id': 'batchId', '--batch-title': 'batchTitle',
        '--description': 'description', '--rights-evidence': 'rightsEvidence',
        '--derivative-notice': 'derivativeNotice',
      }[value];
      demand(key, `Unknown option: ${value}`);
      options[key] = key === 'tags' ? next.split(',') : next;
    }
  }
  demand(positional.length === 1, 'Choose exactly one MP3 file or one folder.');
  return { input: positional[0], options };
}

async function run(command, args, { cwd = repository, capture = false } = {}) {
  return await new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      stdio: capture ? ['ignore', 'pipe', 'inherit'] : 'inherit',
    });
    let output = '';
    if (capture) child.stdout.on('data', (chunk) => (output += chunk));
    child.on('error', reject);
    child.on('exit', (code) =>
      code === 0 ? resolve(output.trim()) : reject(new Error(`${command} exited with ${code}.`)),
    );
  });
}

async function ensureCleanCheckout() {
  const dirty = await run('git', ['status', '--porcelain'], { capture: true });
  demand(!dirty, 'Start from a clean archive checkout so unrelated changes cannot enter the intake PR.');
}

async function openPullRequest(manifest) {
  let branch = await run('git', ['branch', '--show-current'], { capture: true });
  if (branch === 'main') {
    branch = `codex/soundtrack-${manifest.batchId}`;
    await run('git', ['switch', '-c', branch]);
  }
  demand(branch.startsWith('codex/'), 'Use a dedicated codex/ branch before --open-pr.');
  await run('git', [
    'add', '--', `batches/${manifest.batchId}`, 'batches.json', 'catalogue.json',
    'deployment-manifest.json',
  ]);
  await run('git', ['diff', '--cached', '--check']);
  await run('git', ['commit', '-m', `Add ${manifest.title} to the public soundtrack catalogue`]);
  await run('git', ['push', '-u', 'origin', branch]);
  const temporary = await mkdtemp(path.join(os.tmpdir(), 'revealline-music-pr-'));
  try {
    const body = path.join(temporary, 'body.md');
    await writeFile(
      body,
      `Adds ${manifest.tracks.length} exact MP3 recording${manifest.tracks.length === 1 ? '' : 's'} to the public archive through the rights-aware intake tool.\n\nEvery recording retains its creator source, supported Creative Commons licence, credit, exact SHA-256 object path and listening-pending status. The generated unified catalogue and deployment pins passed the repository verification suite.\n`,
    );
    await run('gh', [
      'pr', 'create', '--base', 'main', '--head', branch,
      '--title', `Add ${manifest.title} to the public soundtrack catalogue`, '--body-file', body,
    ]);
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

export async function automateMusicIntake(input, options) {
  await ensureCleanCheckout();
  const manifest = await createUploadManifest(input, options),
    temporary = await mkdtemp(path.join(os.tmpdir(), 'revealline-music-intake-'));
  try {
    const manifestFile = path.join(temporary, 'upload.json');
    await writeFile(manifestFile, `${JSON.stringify(manifest, null, 2)}\n`);
    await prepareUpload(manifestFile);
    await run(process.execPath, ['intake/build-unified-catalogue.mjs', '--check']);
    await run(process.execPath, ['--test', 'test-verify.mjs']);
    await run(process.execPath, ['verify.mjs']);
    await run('git', ['diff', '--check']);
    if (options.openPR) await openPullRequest(manifest);
    return manifest;
  } finally {
    await rm(temporary, { recursive: true, force: true });
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { input, options } = parseArguments(process.argv.slice(2));
  const result = await automateMusicIntake(input, options);
  console.log(
    `Prepared ${result.tracks.length} recording(s) in ${result.batchId}.${options.openPR ? ' Pull request opened.' : ' Review the generated diff, then commit it or rerun with --open-pr from a clean branch.'}`,
  );
}
