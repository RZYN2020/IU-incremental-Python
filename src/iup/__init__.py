from .compiler import Compiler, CompilerConfig, Pass
from .interp import INTERPRETERS # type: ignore
from .type import TYPE_CHECKERS # type: ignore

compiler_: Compiler = Compiler.get_instance()

LvarConfig: CompilerConfig = [
    Pass('remove_complex_operands', 'Lvar', 'Lvar', compiler_.remove_complex_operands),
    Pass('select_instructions', 'Lvar', 'X86var', compiler_.select_instructions),
]
