import pytest
import os
import sys
from typing import Any, List, Tuple
from ast import parse
from ..x86.eval_x86 import interp_x86 # type: ignore
from ..compiler import Language, CompilerConfig
from .. import LvarConfig
from ..interp import INTERPRETERS
from ..type   import TYPE_CHECKERS

TEST_BASE = os.path.join(os.getcwd(), 'src/iup/tests')


compiler_test_configs: List[Tuple[CompilerConfig, str]] = [
    (LvarConfig, os.path.join(TEST_BASE, 'var')),
]

def check_pass(lang: Language, res: Any, test_dir: str, test: str) -> bool:
    input_file  = os.path.join(test_dir, test + ".in")
    output_file = os.path.join(test_dir, test + ".out")
    stdin = sys.stdin
    stdout = sys.stdout
    sys.stdin = open(input_file, 'r')
    sys.stdout = open(output_file, 'w')
    if INTERPRETERS.get(lang) is not None:
        INTERPRETERS[lang].interp(res)
    else:
        interp_x86(res)
    sys.stdin = stdin
    sys.stdout = stdout
    return os.system('diff' + ' -b ' + output_file + ' ' + os.path.join(test_dir, test + '.golden')) == 0


def get_tests(test_dir: str) -> List[str]:
    return [f[:-3] for f in os.listdir(test_dir) if f.endswith(".py")]


def get_test_items(config: CompilerConfig, test_dir: str) -> List[Tuple[str, str, CompilerConfig]]:
    return [(test, test_dir, config) for test in get_tests(test_dir)]


empty: List[Tuple[str, str, CompilerConfig]] = []
test_items: List[Tuple[str, str, CompilerConfig]] = sum(
    [get_test_items(config, test_dir) for config, test_dir in compiler_test_configs], empty 
)

@pytest.mark.parametrize('test, test_dir, config', test_items)
def test(test: str, test_dir: str, config: CompilerConfig):
    lang: Language
    file_name = os.path.join(test_dir, test + ".py")
    
    with open(file_name) as source:
        program = parse(source.read())
        
    for pass_ in config:
        lang = pass_.source
        if TYPE_CHECKERS.get(lang) is not None:
            TYPE_CHECKERS[lang].type_check(program)
        program = pass_.transform(program)
        assert check_pass(pass_.target, program, test_dir, test)
            
            
if __name__ == '__main__':
    pytest.main(['-v', '-s', __file__])