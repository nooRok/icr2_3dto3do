# coding: utf-8
from argparse import ArgumentParser, RawDescriptionHelpFormatter

from icr2model.model import Model
from icr2_3dto3do.converter import Converter

description = ('usage for track .3d file (generated by trk23d): \n'
               '  python 3d23do.py input.3d index output.3do --hash hash\n'
               'usage for object .3d file: \n'
               '  python 3d23do.py input.3d rootNameYouDefined output.3do')


def main():
    parser = ArgumentParser(description=description, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument('input', help='input *.3d file path')
    parser.add_argument('root', help='root object name in *.3d file')
    parser.add_argument('output', nargs='?', default='', help='output *.3do file path')
    parser.add_argument('--hash', default='', help='hash object name (for track)')
    parser.add_argument('--scale', default=1.0, type=float, help='scaling factor (default=1.0)')
    parser.add_argument('--no-opt', action='store_true', help='disable flavors optimization')
    parser.add_argument('--silent', action='store_true', help="silent mode (don't show output flavors)")
    parser.add_argument('--allow-dup', action='store_true', help='allow duplicate definition name '
                                                                 '(respect the most latter one)')
    args = parser.parse_args()
    # print(args)

    c = Converter.open_3d(args.input, args.allow_dup)
    fs = c.build_flavors(args.root, args.scale, track_hash=args.hash)
    m = Model()
    m.header.files = c.get_files()
    with m.body.flavors as flavors:
        flavors.update(fs)
    m.sort(not args.no_opt)
    if not args.silent:
        lines = (f'{o} {f.to_str()}'
                 for o, f in sorted(m.body.flavors.items()))
        print('\n'.join(lines))
    if args.output:
        with open(args.output, 'wb') as f:
            f.write(m.to_bytes())


if __name__ == '__main__':
    main()
