from typing import List, Any, Callable, Literal
from dataclasses import dataclass
from .compiler import Compiler # type: ignore

PassName = Literal[ 'shrink', 'uniquify', 'reveal_functions', 'resolve', 'erase_types', 'cast_insert',
                'lower_casts', 'differentiate_proxies', 'reveal_casts', 'convert_assignments',
                'convert_to_closures', 'limit_functions', 'expose_allocation', 'remove_complex_operands',
                'explicate_control',
                # below are passes that must be included in the compiler
                'select_instructions',
                'assign_homes',
                'patch_instructions',
                'prelude_and_conclusion',
              ]

Language = Literal['Lint', 'Lvar', 'X86var']

@dataclass
class Pass:
    name: PassName
    source: Language
    target: Language
    transform: Callable[[Any], Any]


CompilerConfig = List[Pass]
