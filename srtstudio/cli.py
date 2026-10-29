"""Optional headless batch mode: python -m srtstudio.cli ..."""

import argparse
import sys
from pathlib import Path
from srtstudio.core import Options, convert_batch


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description='Convert .srt subtitles to UTF-8 without BOM.')
    parser.add_argument('sources', nargs='+', type=Path, help='Input SRT files and/or folders')
    parser.add_argument('-o', '--output', type=Path, help='Custom output directory (default: adjacent utf8)')
    parser.add_argument('--flat', action='store_true', help='Do not preserve subfolder paths')
    parser.add_argument('--no-recursive', action='store_true', help='Only immediate folder contents')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing output files')
    args = parser.parse_args(argv)
    options = Options(tuple(args.sources), args.output, not args.no_recursive, not args.flat, args.overwrite)
    results = convert_batch(options)
    if not results:
        print('No SRT files found.', file=sys.stderr)
        return 2
    for r in results:
        print(f'[{r.status.upper():7}] {r.source.name} ({r.encoding}) -> {r.destination} | {r.message}')
    failed = sum(r.status == 'failed' for r in results)
    print(f'Processed {len(results)} file(s); failed: {failed}.')
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
