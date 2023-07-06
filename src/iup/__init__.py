from .x86.eval_x86 import interp_x86
from .compiler import Compiler, CompilerConfig, Pass
from .interp import INTERPRETERS
from .type import TYPE_CHECKERS

compiler_: Compiler = Compiler.get_instance()

LvarConfig: CompilerConfig = [
    Pass('remove_complex_operands', 'Lvar', 'Lvar', compiler_.remove_complex_operands),
]
