import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, readFile, writeFile, rm, symlink } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import os from 'node:os';
import { fileURLToPath } from 'node:url';
import {
  validateDeclarations,
  validateBatchDeclarations,
  validateBatchIndex,
  verifyPreviewBatch,
  appendVerifiedPreviewBatch,
} from './verify.mjs';

const source = fileURLToPath(new URL('./', import.meta.url));
const baseURL = 'https://mekhovov.github.io/revealline-soundtracks-01/';
const hash = (bytes) => createHash('sha256').update(bytes).digest('hex');
const asPin = (file, bytes) => ({
  path: file,
  bytes: bytes.length,
  sha256: hash(bytes),
});
const json = (value) => Buffer.from(JSON.stringify(value));
async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), 'soundtrack-preview-batch-'));
  t.after(() => rm(root, { recursive: true, force: true }));
  const id = 'core-fixture';
  // Byte-verifier fixture only: this is not a recording or listening approval.
  const audio = Buffer.from('synthetic audio bytes');
  const object = asPin(`objects/${hash(audio)}.mp3`, audio);
  const inventory = {
    format: 'revealline-soundtrack-archive.v1',
    id,
    files: [object],
  };
  const catalogue = {
    format: 'revealline-licensed-preview-catalogue.v1',
    status: 'licensed-preview',
    gameCatalogueAdmission: false,
    listeningApproval: 'not-reviewed',
    archive: {
      id,
      baseURL: `${baseURL}batches/${id}/`,
      inventorySha256: hash(json(inventory)),
    },
    tracks: [
      {
        id: 'synthetic.fixture',
        ...object,
        title: 'Synthetic fixture',
        artist: 'Fixture only',
        source: 'https://example.com/fixture',
        licenseURL: 'https://creativecommons.org/publicdomain/zero/1.0/',
        credit: 'Synthetic test data, not a licensed recording.',
      },
    ],
  };
  const files = new Map([
    ['.nojekyll', Buffer.alloc(0)],
    ['index.html', Buffer.from('<p>Listening pending</p>')],
    ['style.css', Buffer.from('body {}')],
    ['player.mjs', Buffer.from('// Synthetic preview fixture')],
    ['README.md', Buffer.from('Synthetic listening-pending preview')],
    ['CREDITS.md', Buffer.from('Synthetic test attribution')],
    ['inventory.json', json(inventory)],
    ['preview-catalogue.json', json(catalogue)],
    [object.path, audio],
  ]);
  const manifest = {
    format: 'revealline-soundtrack-preview-deployment.v1',
    id,
    expected: { trackCount: 1, audioBytes: audio.length },
    files: [...files].map(([name, body]) => asPin(name, body)),
    provenance: { fixture: true },
  };
  files.set('deployment-manifest.json', json(manifest));
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
test('original70 root manifest, inventory and every static pin remain unchanged', async () => {
  const body = await readFile(path.join(source, 'deployment-manifest.json'));
  assert.equal(
    hash(body),
    '46ea74eb7e4240d48145f29080c0fa8094f5c2325290f95686645aab56488558',
  );
  const manifest = JSON.parse(body),
    inventory = JSON.parse(await readFile(path.join(source, 'inventory.json'))),
    catalogue = JSON.parse(await readFile(path.join(source, 'preview-catalogue.json')));
  const result = validateDeclarations(manifest, inventory, catalogue);
  assert.equal(result.trackCount, 70);
  assert.equal(result.audioBytes, 354986122);
  for (const entry of manifest.files.filter(
    (file) => !file.path.startsWith('objects/'),
  )) {
    const actual = await readFile(path.join(source, entry.path));
    assert.equal(actual.length, entry.bytes);
    assert.equal(hash(actual), entry.sha256);
  }
  manifest.expected.trackCount = 71;
  assert.throws(() => validateDeclarations(manifest, inventory, catalogue), /pinned/);
});
test('a declared tiny preview batch verifies its exact static and object bytes reproducibly', async (t) => {
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
test('combining verified batches preserves root pins and enforces aggregate uniqueness and budgets', async (t) => {
  const f = await fixture(t);
  const batch = await verifyPreviewBatch(f.root, { ...f.declaration, baseURL });
  const rootDeclarations = validateDeclarations(
    JSON.parse(await readFile(path.join(source, 'deployment-manifest.json'))),
    JSON.parse(await readFile(path.join(source, 'inventory.json'))),
    JSON.parse(await readFile(path.join(source, 'preview-catalogue.json'))),
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
    { totalBytes: 800000000 - batch.totalBytes },
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
  duplicateHash.files.set('batches/earlier/' + f.object.path, {
    ...f.object,
    path: 'batches/earlier/' + f.object.path,
  });
  assert.throws(
    () => appendVerifiedPreviewBatch(duplicateHash, f.declaration, batch),
    /recording hash/,
  );
});

test('batch declarations are explicit, unique, bounded and rooted at the exact batch path', async (t) => {
  const f = await fixture(t);
  const format = 'revealline-soundtrack-preview-batches.v1';
  assert.deepEqual(validateBatchIndex({ format, batches: [] }), []);
  assert.deepEqual(validateBatchIndex({ format, batches: [f.declaration] }), [
    f.declaration,
  ]);
  for (const id of [
    '../escape',
    'UPPER',
    'with_underscore',
    'a/b',
    'a%2fb',
    'a\\b',
    'a\n',
    'a'.repeat(65),
  ])
    assert.throws(() =>
      validateBatchIndex({ format, batches: [{ ...f.declaration, id }] }),
    );
  assert.throws(
    () => validateBatchIndex({ format, batches: [f.declaration, f.declaration] }),
    /duplicate/,
  );
  for (const changed of [
    { path: 'other.json' },
    { bytes: 524289 },
    { sha256: 'not-a-hash' },
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
    'more than20 recordings',
    (f) => {
      f.manifest.expected.trackCount = 21;
    },
  ],
  [
    'zero recordings',
    (f) => {
      f.manifest.expected.trackCount = 0;
    },
  ],
  [
    'invented game admission',
    (f) => {
      f.catalogue.gameCatalogueAdmission = true;
    },
  ],
  [
    'invented listening approval',
    (f) => {
      f.catalogue.listeningApproval = 'approved';
    },
  ],
  [
    'another batch URL',
    (f) => {
      f.catalogue.archive.baseURL = `${baseURL}batches/other/`;
    },
  ],
  [
    'root archive URL',
    (f) => {
      f.catalogue.archive.baseURL = baseURL;
    },
  ],
  [
    'stale inventory pin',
    (f) => {
      f.catalogue.archive.inventorySha256 = 'f'.repeat(64);
    },
  ],
  [
    'unsupported licence',
    (f) => {
      f.catalogue.tracks[0].licenseURL = 'https://example.com/noncommercial';
    },
  ],
  [
    'removed attribution',
    (f) => {
      f.catalogue.tracks[0].credit = '';
    },
  ],
  [
    'unknown audio object',
    (f) => {
      f.catalogue.tracks[0].path = 'objects/unknown.mp3';
    },
  ],
  [
    'changed object bytes',
    (f) => {
      f.inventory.files[0].bytes++;
    },
  ],
  [
    'object alias',
    (f) => {
      f.inventory.files[0].path = 'objects/../audio.mp3';
    },
  ],
  [
    'undeclared static entry',
    (f) => {
      f.manifest.files.push({
        path: 'private.json',
        bytes: 0,
        sha256: hash(''),
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
test('complete pin validation rejects changed bytes, missing files and unlisted additions', async (t) => {
  const f = await fixture(t);
  const args = { ...f.declaration, baseURL };
  const original = f.files.get(f.object.path);
  await writeFile(path.join(f.root, f.object.path), Buffer.alloc(original.length, 7));
  await assert.rejects(verifyPreviewBatch(f.root, args), /SHA-256/);
  await writeFile(path.join(f.root, f.object.path), original);
  await writeFile(path.join(f.root, 'extra.txt'), 'unlisted');
  await assert.rejects(verifyPreviewBatch(f.root, args), /Unexpected/);
  await rm(path.join(f.root, 'extra.txt'));
  await rm(path.join(f.root, f.object.path));
  await assert.rejects(verifyPreviewBatch(f.root, args), /exact deployment/);
});
test('batch manifest substitution and symbolic links are refused', async (t) => {
  const f = await fixture(t);
  await assert.rejects(
    verifyPreviewBatch(f.root, {
      ...f.declaration,
      baseURL,
      manifest: { ...f.declaration.manifest, sha256: '0'.repeat(64) },
    }),
    /explicit pin/,
  );
  const object = path.join(f.root, f.object.path);
  await rm(object);
  await symlink(path.join(f.root, 'README.md'), object);
  await assert.rejects(
    verifyPreviewBatch(f.root, { ...f.declaration, baseURL }),
    /Unexpected object/,
  );
  const alias = f.root + '-alias';
  t.after(() => rm(alias, { force: true }));
  await symlink(f.root, alias);
  await assert.rejects(
    verifyPreviewBatch(alias, { ...f.declaration, baseURL }),
    /ordinary directory/,
  );
});
