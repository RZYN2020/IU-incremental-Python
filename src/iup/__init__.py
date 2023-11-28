from .compiler import PassManager, ALL_PASSES, LvarManager #type: ignore
from .interp import INTERPRETERS # type: ignore
from .type import TYPE_CHECKERS # type: ignore
from .x86.eval_x86 import interp_x86 # type: ignore
from ast import parse
import os
    

def compile(source: str, target: str, manager: PassManager, emulate_x86: bool = False) -> None:
    
    with open(source, 'r') as file:
        program = parse(file.read())
        
    assert manager.target == 'X86'
    TYPE_CHECKERS[manager.source].type_check(program)
    
    program = manager.run(program, None) #type: ignore

    if emulate_x86:
        interp_x86(program)
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f'{target}.s', 'w') as file:
            file.write(str(program))
        os.system(f'gcc -c -g -std=c99 {script_dir}/runtime.c -o {script_dir}/runtime.o')
        os.system(f'gcc {script_dir}/runtime.o {target}.s -o {target}')
