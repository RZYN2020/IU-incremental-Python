import os
import argparse
from . import CompilerConfig, TYPE_CHECKERS, interp_x86
from ast import parse


def compile(source: str, target: str, config: CompilerConfig, emulate_x86 = False) -> None:
    
    with open(source, 'r') as file:
        program = parse(file.read())
        
    assert len(config) > 0
    assert config[-1].target == 'X86'
    TYPE_CHECKERS[config[0].source].type_check(program)
    
    for pass_ in config:
        program = pass_.transform(program)
        
    if emulate_x86:
        interp_x86(program)
    else:
        with open(f'{target}.s', 'w') as file:
            file.write(str(program))
        os.system(f'gcc runtime.o {target}.s -o {target}')

        
parser = argparse.ArgumentParser()

if __name__ == "__main__":
    args = parser.parse_args()
    ...