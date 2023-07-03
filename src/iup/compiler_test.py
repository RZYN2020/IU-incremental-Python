import os
import compiler
import interp.interp_Lvar
import type.type_check_Lvar
from tests.test import run_one_test, run_tests
from x86.eval_x86 import interp_x86
import logging
import pytest

logging.basicConfig(filename='test_var.log', filemode='w', format='%(message)s', level=logging.INFO)
compiler = compiler.Compiler()

def test_var(one_test=True, file_name='/tests/var/careless.py'):
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
    if one_test:
        run_one_test(os.getcwd() + file_name,
                     'var',
                     compiler,
                     'var',
                     typecheck_dict,
                     interp_dict)
    else:
        run_tests('var', compiler, 'var',
                  typecheck_dict,
                  interp_dict)
    
    
def call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except Exception as e:
        logging.info(e)

if __name__ == '__main__':
    call(test_var, file_name='/tests/var/cpxx.py')
    call(test_var, file_name='/tests/var/careless.py')
    call(test_var, file_name='/tests/var/cpx.py')
    call(test_var, file_name='/tests/var/input.py')
    call(test_var, file_name='/tests/var/zero.py')