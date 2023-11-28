import argparse
from typing import List
from iup.compiler.pass_manager import AnalysisPass, TransformPass, Pass
from src.iup import ALL_PASSES, compile, LvarManager, PassManager

parser = argparse.ArgumentParser()
parser.add_argument('source', type=str, help='source file')
parser.add_argument('-o', '--output', type=str, help='output file')
parser.add_argument('-e', '--emulate', action='store_true', help='emulate the target assembly code')
parser.add_argument('-p', '--passes', type=str, help='passes to run', nargs='+', default=['all'])

if __name__ == "__main__":
    args = parser.parse_args()
    if args.passes == ['all']:
        manager = LvarManager
    else:
        passes: List[Pass] = [ALL_PASSES[p] for p in args.passes if (p in ALL_PASSES)]
        transforms: List[TransformPass] = [p for p in passes if not p.pure()] #type: ignore
        analyses: List[AnalysisPass] = [p for p in passes if p.pure()] #type: ignore
        manager = PassManager(transforms, analyses)
    if args.output:
        target = args.output
    else:
        target = args.source.split('.')[0]
    compile(args.source, target, manager, args.emulate)