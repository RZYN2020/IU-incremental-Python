from .compiler import CompilerConfig, Pass
from .compiler.compiler_register_allocator import Compiler
from .interp import INTERPRETERS # type: ignore
from .type import TYPE_CHECKERS # type: ignore
from .x86.eval_x86 import interp_x86 # type: ignore
from ast import parse
import os

compiler_: Compiler = Compiler()


# maybe i should differentiate between the analysis and the transformation pass like llvm...
LvarConfig: CompilerConfig = [
    Pass('remove_complex_operands', 'Lvar', 'Lvar', compiler_.remove_complex_operands),
    Pass('select_instructions', 'Lvar', 'X86var', compiler_.select_instructions),
    Pass('allocate_registers', 'X86var', 'X86var', compiler_.allocate_registers),
    Pass('patch_instructions', 'X86', 'X86', compiler_.patch_instructions),
    Pass('prelude_and_conclusion', 'X86', 'X86', compiler_.prelude_and_conclusion)
]

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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        with open(f'{target}.s', 'w') as file:
            file.write(str(program))
        os.system(f'gcc -c -g -std=c99 {script_dir}/runtime.c -o {script_dir}/runtime.o')
        os.system(f'gcc {script_dir}/runtime.o {target}.s -o {target}')
