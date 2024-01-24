import argparse
from typing import List
from iup.compiler import AnalysisPass, TransformPass, Pass, Program, LifManager
from iup import ALL_PASSES, compile, PassManager

class MainPassManager(PassManager):

    test: str
    test_dir: str

    def run(self, prog: Program, manager: 'PassManager') -> Program:
        self.prog = prog
        
        for trans in self.transforms:
            print(f"Run trans {trans.name}")
            self.prog = trans.run(self.prog, self)
            print(f"result:\n{self.prog}\n")
        
        self.cache = {}
        return self.prog
    
parser = argparse.ArgumentParser()
parser.add_argument('source', type=str, help='source file')
parser.add_argument('-o', '--output', type=str, help='output file')
parser.add_argument('-e', '--emulate', action='store_true', help='emulate the target assembly code')
parser.add_argument('-p', '--passes', type=str, help='passes to run', nargs='+', default=['all'])
parser.add_argument('-v', '--verbose', action="store_true")

if __name__ == "__main__":
    args = parser.parse_args()
    if args.passes == ['all']:
        if args.verbose:
            manager = MainPassManager(LifManager.transforms, list(LifManager.analyses.values()))
        else:
            manager = LifManager
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