"""Fail closed when Reckless publication generation changes an unexpected path."""

import argparse
from pathlib import PurePosixPath
import subprocess


EXACT_PATHS = {
    'batches.json',
    'catalogue.json',
    'deployment-manifest.json',
}
PREFIXES = (
    'batches/metal-reckless2-audition-20260925/',
    'intake/archive/metal-reckless2-audition-20260925/',
)


def validate_paths(paths):
    normalized = set(paths)
    if not normalized:
        raise ValueError('Publication produced no changed paths')
    for path in normalized:
        canonical = PurePosixPath(path).as_posix()
        if canonical != path or path.startswith('../') or path.startswith('/'):
            raise ValueError(f'Non-canonical publication path: {path!r}')
        if path not in EXACT_PATHS and not any(path.startswith(prefix) for prefix in PREFIXES):
            raise ValueError(f'Unexpected publication path: {path}')
    missing = EXACT_PATHS - normalized
    if missing:
        raise ValueError('Missing required publication paths: ' + ', '.join(sorted(missing)))
    for prefix in PREFIXES:
        if not any(path.startswith(prefix) for path in normalized):
            raise ValueError(f'Missing generated publication tree: {prefix}')
    return normalized


def git_paths(mode):
    command = ['git', 'diff']
    if mode == 'cached':
        command.append('--cached')
    command.extend(['--name-only', '-z', 'HEAD'])
    tracked = subprocess.check_output(command).decode().split('\0')
    if mode == 'worktree':
        untracked = subprocess.check_output(
            ['git', 'ls-files', '--others', '--exclude-standard', '-z']
        ).decode().split('\0')
    else:
        untracked = []
    return [path for path in tracked + untracked if path]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=('worktree', 'cached'))
    args = parser.parse_args()
    paths = validate_paths(git_paths(args.mode))
    print(f'Validated {len(paths)} {args.mode} publication paths')


if __name__ == '__main__':
    main()
