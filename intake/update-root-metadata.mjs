import { createHash } from 'node:crypto';
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const repository = path.resolve(fileURLToPath(new URL('..', import.meta.url)));
const PUBLIC_METADATA = [
  '.nojekyll', 'CREDITS.md', 'README.md', 'UPLOAD_GUIDE.md', 'catalogue.json',
  'index.html', 'inventory.json', 'player.mjs', 'preview-catalogue.json', 'style.css',
];
const digest = (bytes) => createHash('sha256').update(bytes).digest('hex');

export async function updateRootMetadataPins() {
  const manifestPath = path.join(repository, 'deployment-manifest.json');
  const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
  if (
    manifest.format !== 'revealline-soundtrack-preview-deployment.v1' ||
    manifest.expected?.trackCount !== 70 ||
    manifest.expected?.audioBytes !== 354986122
  ) throw new Error('Refusing to rewrite an unexpected root deployment manifest.');
  const objects = manifest.files.filter((entry) => entry.path.startsWith('objects/'));
  if (objects.length !== 70) throw new Error('Root audio pins changed or are incomplete.');
  const metadata = [];
  for (const file of PUBLIC_METADATA) {
    const bytes = await readFile(path.join(repository, file));
    metadata.push({ path: file, bytes: bytes.length, sha256: digest(bytes) });
  }
  manifest.files = [...metadata, ...objects];
  await writeFile(manifestPath, `${JSON.stringify(manifest, null, 2)}\n`);
  return manifest;
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await updateRootMetadataPins();
  console.log('Updated root metadata pins without changing the 70 audio-object pins.');
}
