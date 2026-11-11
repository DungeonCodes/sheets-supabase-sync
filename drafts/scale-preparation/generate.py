"""Reproducible, streaming synthetic snapshots; no network or temporary files."""
from __future__ import annotations

import argparse
import csv
import os
import sys
from collections.abc import Iterator

SCENARIOS = ('initial', 'unchanged', 'incremental', 'insert', 'delete', 'restore', 'structural')


def rows(count: int, sheets: int, seed: int, scenario: str = 'initial', start: int = 0) -> Iterator[tuple]:
    """Emit synthetic snapshot rows; start resumes at a zero-based row boundary."""
    if count < 0 or sheets < 1 or start < 0 or start > count or scenario not in SCENARIOS:
        raise ValueError('invalid generator arguments')
    for index in range(start, count):
        value = (index * 1103515245 + seed) % 2147483648
        if scenario == 'incremental' and index % 10 == 0:
            value = (value + 1) % 2147483648
        # Compare against an initial snapshot with the same count: insert adds
        # new rows at the tail; delete/restore change a synthetic status field.
        status = 'deleted' if scenario == 'delete' and index % 10 == 0 else 'active'
        row = (index % sheets, index, value, status)
        yield (*row, 'extra') if scenario == 'structural' else row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--rows', type=int, required=True)
    parser.add_argument('--sheets', type=int, default=1)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--start', type=int, default=0)
    parser.add_argument('--scenario', choices=SCENARIOS, default='initial')
    args = parser.parse_args(argv)
    if args.rows < 0 or args.sheets < 1 or not 0 <= args.start <= args.rows:
        parser.error('rows, sheets or start outside valid range')
    writer = csv.writer(sys.stdout, lineterminator='\n')
    try:
        header = ('sheet', 'synthetic_id', 'synthetic_value', 'synthetic_status')
        writer.writerow((*header, 'synthetic_extra') if args.scenario == 'structural' else header)
        writer.writerows(rows(args.rows, args.sheets, args.seed, args.scenario, args.start))
        sys.stdout.flush()
    except BrokenPipeError:
        # Avoid a second flush of the broken pipe at interpreter shutdown.
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
        return 0
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
