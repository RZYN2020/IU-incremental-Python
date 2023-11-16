import argparse
from src.iup import LvarConfig, compile

parser = argparse.ArgumentParser()
parser.add_argument('source', type=str, help='source file')
parser.add_argument('-o', '--output', type=str, help='output file', default='a.out')
parser.add_argument('-e', '--emulate', action='store_true', help='emulate the target assembly code')
parser.add_argument('-p', '--passes', type=str, help='passes to run', nargs='+', default=['all'])

if __name__ == "__main__":
    args = parser.parse_args()
    if args.passes == ['all']:
        config = LvarConfig
    else:
        config = [pass_ for pass_ in LvarConfig if pass_.name in args.passes]
    if args.output:
        target = args.output
    else:
        target = args.source.split('.')[0]
    compile(args.source, target, config, args.emulate)