from .compiler import Compiler
from iup.x86.eval_x86 import interp_x86
from iup.type import TYPE_CHECKERS
from iup.config import CompilerConfig, Pass
from ast import parse
import os

compiler = Compiler.get_instance()

LvarConfig: CompilerConfig = [
    Pass('remove_complex_operands', 'Lvar', 'Lvar', compiler.remove_complex_operands),
]

def compile(source: str, target: str, config: CompilerConfig, emulate_x86 = False) -> None:
    
    with open(source, 'r') as file:
        program = parse(file.read())
        
    assert len(config) > 0
    assert config[-1].target == 'X86'
    TYPE_CHECKERS[config[0].source].typecheck(source)
    
    for pass_ in config:
        program = pass_.transform(program)
        
    if emulate_x86:
        interp_x86(program)
    else:
        with open(f'{target}.s', 'w') as file:
            file.write(str(program))
        os.system(f'gcc runtime.o {target}.s -o {target}')