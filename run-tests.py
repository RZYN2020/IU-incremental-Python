import os
import compiler
import interp.interp_Lvar
import type.type_check_Lvar
from utils.utils import run_tests, run_one_test
from x86.eval_x86 import interp_x86
import logging

logging.basicConfig(format='%(message)s', level=logging.DEBUG)

compiler = compiler.Compiler()

typecheck_Lvar = type.type_check_Lvar.TypeCheckLvar().type_check

typecheck_dict = {
    'source': typecheck_Lvar,
    'remove_complex_operands': typecheck_Lvar,
}
interpLvar = interp.interp_Lvar.InterpLvar().interp
interp_dict = {
    'remove_complex_operands': interpLvar,
    'select_instructions': interp_x86,
    'assign_homes': interp_x86,
    'patch_instructions': interp_x86,
}

if True:
    run_one_test(os.getcwd() + '/tests/var/careless.py',
                 'var',
                 compiler,
                 'var',
                 typecheck_dict,
                 interp_dict)
else:
    run_tests('var', compiler, 'var',
              typecheck_dict,
              interp_dict)

