#!/usr/bin/env python3
"""Prepare rights-reviewed candidates on a hosted runner; never approve or deploy music."""
import argparse
import hashlib
import html
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import time
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

RESERVE = 1024 ** 3
SOURCE_LIMIT = 64 * 1024 ** 2
TOTAL_LIMIT = 650 * 1024 ** 2
LICENSES = {'CC0 1.0 Universal': 'https://creativecommons.org/publicdomain/zero/1.0/',
            'CC BY 4.0 International': 'https://creativecommons.org/licenses/by/4.0/'}


def digest(body):
    return hashlib.sha256(body).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def allowed_url(value):
    url = urlparse(value)
    return (url.scheme == 'https' and url.hostname == 'opengameart.org'
            and url.port in (None, 443) and not url.username and not url.password)


def validate_manifest(value):
    if value.get('format') != 'revealline-core-intake.v1' or not 1 <= len(value.get('tracks', [])) <= 20:
        raise ValueError('Unsupported or excessive intake')
    ids = set()
    for row in value['tracks']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9.-]{0,79}', row['id']) or row['id'] in ids:
            raise ValueError('Invalid or duplicate identity')
        ids.add(row['id'])
        if row.get('licenseURL') != LICENSES.get(row.get('license')):
            raise ValueError('Unsupported exact source licence')
        if not allowed_url(row['source']) or not allowed_url(row['download']):
            raise ValueError('Unapproved source host')
        if not urlparse(row['download']).path.startswith('/sites/default/files/'):
            raise ValueError('Not an author-provided download')
        if row.get('status') != 'rights-reviewed-listening-pending':
            raise ValueError('Intake cannot grant listening approval')
    return value


def fetch(url, limit):
    if not allowed_url(url):
        raise ValueError('Unapproved source host')
    request = Request(url, headers={'User-Agent': 'RevealLine soundtrack archival intake/1.0'})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                if not allowed_url(response.url):
                    raise ValueError('Unexpected redirect host')
                body = response.read(limit + 1)
                if len(body) > limit:
                    raise ValueError('Source exceeds bounded intake size')
                return body, response.url
        except (OSError, TimeoutError):
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=240)
    if result.returncode:
        raise RuntimeError(result.stderr[-6000:])
    return result


def loudness(file, target=-16, peak=-1.5):
    result = command(['ffmpeg', '-hide_banner', '-nostdin', '-i', str(file), '-vn',
                      '-af', f'loudnorm=I={target}:TP={peak}:LRA=11:print_format=json',
                      '-f', 'null', '-'])
    match = re.search(r'\{\s*"input_i".*?\}', result.stderr, re.S)
    if not match:
        raise ValueError('No complete loudness measurement')
    facts = json.loads(match.group())
    if not all(math.isfinite(float(facts[k])) for k in ('input_i', 'input_tp', 'input_lra', 'input_thresh', 'target_offset')):
        raise ValueError('Silent or unmeasurable recording')
    return facts


def reserve(root, requested=SOURCE_LIMIT):
    if shutil.disk_usage(root).free < RESERVE + requested:
        raise ValueError('Intake must leave at least 1 GiB free')


def inspect_mp3(file, game_root):
    module = (game_root / 'game/mp3.mjs').resolve().as_uri()
    code = ("import{readFile}from'node:fs/promises';"
            f"import{{inspectMP3}}from{json.dumps(module)};"
            "console.log(JSON.stringify(await inspectMP3(new Blob([await readFile(process.argv[1])],{type:'audio/mpeg'}))));")
    return json.loads(command(['node', '--input-type=module', '-e', code, str(file)]).stdout)


def prepare(manifest, output, game_root):
    manifest_bytes = manifest.read_bytes()
    rows = validate_manifest(json.loads(manifest_bytes))['tracks']
    if output.exists():
        raise ValueError('Choose a fresh output directory; never overwrite evidence')
    reserve(output.parent)
    output.mkdir()
    for name in ('objects', 'originals', 'evidence'):
        (output / name).mkdir()
    receipt = {'format': 'revealline-core-intake-receipt.v1', 'sourceManifestSha256': digest(manifest_bytes),
               'checkedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'runnerRevision': os.environ.get('GITHUB_SHA'), 'runnerRun': os.environ.get('GITHUB_RUN_ID'),
               'ffmpeg': command(['ffmpeg', '-version']).stdout.splitlines()[0],
               'gameInspectorRevision': '71a0ffeaeb5079ac6e87a7d80327c6b34948aaa3',
               'listeningApproval': False, 'tracks': [], 'failures': []}
    known = json.loads(Path('preview-catalogue.json').read_text())['tracks']
    known_hashes = {track['sha256'] for track in known}
    known_titles = {re.sub(r'[^a-z0-9]', '', track['title'].lower()) for track in known}
    pages = {}
    for row in rows:
        try:
            reserve(output)
            if row['source'] not in pages:
                body, final = fetch(row['source'], 2 * 1024 ** 2)
                source_hash = digest(body)
                (output / 'evidence' / (source_hash + '.html')).write_bytes(body)
                pages[row['source']] = (body, source_hash, final)
            source_body, source_hash, source_final = pages[row['source']]
            normalized = unquote(html.unescape(source_body.decode('utf8')))
            if unquote(row['download']) not in normalized:
                raise ValueError('Exact download is not linked by the reviewed creator page')
            if row['licenseURL'].removeprefix('https://') not in normalized:
                raise ValueError('Expected licence link is absent from creator snapshot')
            body, final = fetch(row['download'], SOURCE_LIMIT)
            source_sha = digest(body)
            if source_sha in known_hashes or re.sub(r'[^a-z0-9]', '', row['title'].lower()) in known_titles:
                raise ValueError('Recording already exists in the admitted collection')
            suffix = Path(urlparse(final).path).suffix
            original = output / 'originals' / (source_sha + suffix)
            original.write_bytes(body)
            del body
            probe = json.loads(command(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                                        '-show_entries', 'format=duration:stream=sample_rate,channels',
                                        '-of', 'json', str(original)]).stdout)
            duration = float(probe['format']['duration'])
            if not 60 <= duration <= 720:
                raise ValueError('Recording is outside the 1–12 minute candidate envelope')
            command(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(original), '-map', '0:a:0', '-f', 'null', '-'])
            measured = loudness(original)
            normalized_path = output / 'candidate.mp3'
            measured_output = None
            for peak in (-1.5, -2.0, -2.5):
                filter_value = (f'loudnorm=I=-16:TP={peak}:LRA=11:measured_I={measured["input_i"]}'
                                f':measured_TP={measured["input_tp"]}:measured_LRA={measured["input_lra"]}'
                                f':measured_thresh={measured["input_thresh"]}:offset={measured["target_offset"]}'
                                ':linear=true:print_format=json')
                command(['ffmpeg', '-v', 'error', '-y', '-nostdin', '-i', str(original), '-map', '0:a:0',
                         '-map_metadata', '-1', '-vn', '-af', filter_value, '-ar', '44100', '-ac', '2',
                         '-c:a', 'libmp3lame', '-b:a', '256k', '-id3v2_version', '3', str(normalized_path)])
                command(['ffmpeg', '-v', 'error', '-xerror', '-nostdin', '-i', str(normalized_path), '-f', 'null', '-'])
                measured_output = loudness(normalized_path)
                if -17 <= float(measured_output['input_i']) <= -15 and float(measured_output['input_tp']) <= -1:
                    break
            else:
                raise ValueError('Encoded loudness or true peak misses target')
            data = normalized_path.read_bytes()
            audio_hash = digest(data)
            if audio_hash in known_hashes:
                raise ValueError('Duplicate encoded recording')
            known_hashes.add(audio_hash)
            facts = inspect_mp3(normalized_path, game_root)
            destination = output / 'objects' / (audio_hash + '.mp3')
            normalized_path.rename(destination)
            receipt['tracks'].append({**row, 'sourceSnapshot': {'path': 'evidence/' + source_hash + '.html', 'sha256': source_hash, 'url': source_final},
                'original': {'path': str(original.relative_to(output)), 'sha256': source_sha, 'bytes': original.stat().st_size, 'url': final},
                'delivery': {'path': str(destination.relative_to(output)), 'sha256': audio_hash, 'bytes': len(data)},
                'asset': facts, 'durationSeconds': duration, 'sourceLoudness': measured, 'encodedLoudness': measured_output,
                'completeDecode': True, 'listeningApproval': False,
                'changes': 'Converted to 256 kbps stereo MP3 at 44.1 kHz with two-pass loudness normalization; native source retained unchanged.'})
            print(f'Prepared {row["id"]}: {duration:.1f}s, {measured_output["input_i"]} LUFS, {measured_output["input_tp"]} dBTP', flush=True)
        except Exception as error:
            receipt['failures'].append({'id': row['id'], 'error': str(error)})
            print(f'FAILED {row["id"]}: {error}', flush=True)
        write_json(output / 'receipt.json', receipt)
        if sum(file.stat().st_size for file in output.rglob('*') if file.is_file()) > TOTAL_LIMIT:
            raise ValueError('Active production storage exceeds 650 MiB')
    write_json(output / 'review.json', {'status': 'pending', 'tracks': [{'id': r['id'], 'sha256': r['delivery']['sha256'], 'fullTrackListening': False, 'transitions': False, 'warningAudibility': False} for r in receipt['tracks']]})
    if receipt['failures']:
        raise SystemExit('Partial intake retained; review receipt failures')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--game-root', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.manifest, args.output, args.game_root)
