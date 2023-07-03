from typing import List, Dict, Any, Union, Optional, Callable, Tuple, Literal
from dataclasses import dataclass

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

Language = Literal['var', 'cps', 'exp', 'imp', 'x86']

@dataclass
class Pass:
    name: PassName
    source: Language
    target: Language
    transform: Callable[[Any], Any]


compiler: Dict[PassName, Pass] = {
    'shrink': Pass('shrink', 'var', 'var', lambda x: x),
}


CompilerConfig = List[PassName]