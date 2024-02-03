import pytest
import os
import sys
from typing import Any, Callable, List, Tuple
from ast import parse
from ..x86.eval_x86 import interp_x86 # type: ignore
from ..compiler import Language, LifAnalyses, LifTransforms, PassManager, Program, LvarAnalyses, LvarTransforms
from ..interp import INTERPRETERS
from ..type   import TYPE_CHECKERS

TEST_BASE = os.path.join(os.getcwd(), 'src/iup/tests')

class TestPassManager(PassManager):

    test: str
    test_dir: str

    def run(self, prog: Program, manager: 'PassManager') -> Program:
        self.prog = prog
        TYPE_CHECKERS[self.lang].type_check(self.prog) #type: ignore
        
        for trans in self.transforms:
            self.prog = trans.run(self.prog, self)
            check_pass(trans.target, self.prog, self.test_dir, self.test, False)
        
        self.cache = {}
        return self.prog
    
LifTestManager = TestPassManager(LifTransforms, LifAnalyses, lang='Lif')
    
compiler_test_configs: List[Tuple[TestPassManager, str]] = [
    (LifTestManager, os.path.join(TEST_BASE, 'var')),
    (LifTestManager, os.path.join(TEST_BASE, 'if')),
]


def check_pass(lang: Language, res: Any, test_dir: str, test: str, emulate: bool) -> bool:
    input_file  = os.path.join(test_dir, test + ".in")
    output_file = os.path.join(test_dir, test + ".out")
    
    def run_with_io(command: Callable[[],None]) -> None:
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = open(input_file, 'r')
        sys.stdout = open(output_file, 'w')
        command()
        sys.stdin = stdin
        sys.stdout = stdout

    if INTERPRETERS.get(lang) is not None:
        run_with_io(lambda: INTERPRETERS[lang].interp(res))
    else:
        if emulate:
            run_with_io(lambda: interp_x86(res))
        else:
            with open(f'{test_dir}/{test}.s', 'w') as file:
                file.write(str(res))
            os.system(f'gcc runtime.o {test_dir}/{test}.s -o {test_dir}/{test}')
            run_with_io(lambda: os.system(f'{test_dir}/{test}')) #type: ignore

    return os.system('diff --strip-trailing-cr' + ' -b ' + output_file + ' ' + os.path.join(test_dir, test + '.golden')) == 0


def get_tests(test_dir: str) -> List[str]:
    return [f[:-3] for f in os.listdir(test_dir) if f.endswith(".py")]


def get_test_items(manager: TestPassManager, test_dir: str) -> List[Tuple[str, str, TestPassManager]]:
    return [(test, test_dir, manager) for test in get_tests(test_dir)]


empty: List[Tuple[str, str, TestPassManager]] = []
test_items: List[Tuple[str, str, TestPassManager]] = sum(
    [get_test_items(manager, test_dir) for manager, test_dir in compiler_test_configs], empty 
)

@pytest.mark.parametrize('test, test_dir, manager', test_items)
def test(test: str, test_dir: str, manager: TestPassManager):
    file_name = os.path.join(test_dir, test + ".py")
    
    with open(file_name) as source:
        program = parse(source.read())
        
    manager.test = test
    manager.test_dir = test_dir
    manager.run(program, None) #type: ignore
            
            
if __name__ == '__main__':
    pytest.main(['-v', '-s', __file__])