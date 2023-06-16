import os
import logging
import sys
from utils.utils import is_python_extension
from sys import platform
from ast import parse, Module
from dataclasses import dataclass


# Given the `ast` output of a pass and a test program (root) name,
# runs the interpreter on the program and compares the output to the
# expected "golden" output.
def test_pass(passname, interp_dict, program_root, ast,
              compiler_name) -> bool:
    if passname in interp_dict.keys():
        input_file = program_root + '.in'
        output_file = program_root + '.out'
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = open(input_file, 'r')
        sys.stdout = open(output_file, 'w')
        interp_dict[passname](ast)
        sys.stdin = stdin
        sys.stdout = stdout
        result = os.system('diff' + ' -b ' + output_file +
                           ' ' + program_root + '.golden')
        if result == 0:
            logging.info('compiler ' + compiler_name + ' success on pass ' + passname
                          + ' on test\n' + program_root + '\n')
            return True
        else:
            logging.info('compiler ' + compiler_name + ' failed pass ' + passname
                  + ' on test\n' + program_root + '\n')
            return False
    else:
        logging.debug('compiler ' + compiler_name + ' skip test on pass ' +
                      passname + ' on test\n' + program_root + '\n')
        return False



def compile_and_test(compiler,
                     compiler_name,
                     type_check_dict,
                     interp_dict,
                     program_filename):
    total_passes = 0
    successful_passes = 0
    from x86.eval_x86 import interp_x86

    program_root = os.path.splitext(program_filename)[0]
    with open(program_filename) as source:
        program = parse(source.read())

    logging.info('\n#source program: ' +
                  os.path.basename(program_root) + '\n')
    logging.info(program)

    if 'source' in type_check_dict.keys():
        logging.debug('\n# type checking source program\n')
        type_check_dict['source'](program)

    def run_pass(passname: str):
        nonlocal total_passes, successful_passes, program
        if hasattr(compiler, passname):
            total_passes += 1
            logging.info('\n# ' + passname + '\n')
            program = getattr(compiler, passname)(program)
            if isinstance(program, Module):
                logging.info(program)
            else:
                logging.info(program)
            if passname in type_check_dict.keys():
                type_check_dict[passname](program)
                logging.info('    type checking passed\n')
            else:
                logging.debug('no type checking for ' + passname)
            succeed = test_pass(passname, interp_dict,
                                program_root, program, compiler_name)
            if succeed:
                successful_passes += 1
        else:
            logging.debug(f"\n# no {passname} pass!")

    passes = ['shrink', 'uniquify', 'reveal_functions', 'resolve', 'erase_types', 'cast_insert',
              'lower_casts', 'differentiate_proxies', 'reveal_casts', 'convert_assignments',
              'convert_to_closures', 'limit_functions', 'expose_allocation', 'remove_complex_operands',
              'explicate_control',
              # below are passes that must be included in the compiler
              'select_instructions',
              'assign_homes',
              'patch_instructions',
              'prelude_and_conclusion',
              ]
    for pass_ in passes:
        run_pass(pass_)

    x86_filename = program_root + ".s"
    with open(x86_filename, "w") as dest:
        dest.write(str(program))

    total_passes += 1

    # Run the final x86 program
    emulate_x86 = False
    if emulate_x86:
        stdin = sys.stdin
        stdout = sys.stdout
        sys.stdin = open(program_root + '.in', 'r')
        sys.stdout = open(program_root + '.out', 'w')
        interp_x86(program)
        sys.stdin = stdin
        sys.stdout = stdout
    else:
        if platform == 'darwin':
            os.system('gcc -arch x86_64 runtime.o ' + x86_filename)
        else:
            os.system('gcc runtime.o ' + x86_filename)
        input_file = program_root + '.in'
        output_file = program_root + '.out'
        os.system('./a.out < ' + input_file + ' > ' + output_file)

    result = os.system('diff' + ' -b ' + program_root + '.out '
                       + program_root + '.golden')
    if result == 0:
        successful_passes += 1
        return (successful_passes, total_passes, 1)
    else:
        print('compiler ' + compiler_name + ', executable failed'
              + ' on test ' + program_root)
        return (successful_passes, total_passes, 0)


# checker and interpreter for the language, and an interpeter for the
# C intermediate language, run all the passes in the compiler,
# checking that the resulting programs produce output that matches the
# golden file.
def run_one_test(test: str, lang: str, compiler, compiler_name: str,
                 type_check_dict: dict, interp_dict: dict):
    test_root = os.path.splitext(test)[0]
    test_name = os.path.basename(test_root)
    
    logging.info('\n\n\n\n\n\n\n')
    logging.info('========================================================')
    logging.info(
        f'running test {test_name} for compiler {compiler_name} of {lang}')
    logging.info('========================================================')
    
    res = compile_and_test(compiler,
                            compiler_name,
                            type_check_dict,
                            interp_dict,
                            test)

    logging.info('========================================================')
    return res


# Given the name of a language, a compiler, the compiler's name, a
# type checker and interpreter for the language, and an interpreter
# for the C intermediate language, test the compiler on all the tests
# in the directory of for the given language, i.e., all the
# python files in ./tests/<language>.
def run_tests(lang, compiler, compiler_name, type_check_dict, interp_dict):
    # Collect all the test programs for this language.
    homedir = os.getcwd()
    directory = homedir + '/tests/' + lang + '/'
    if not os.path.isdir(directory):
        raise Exception('missing directory for test programs: '
                        + directory)
    tests = []
    for (dirpath, _, filenames) in os.walk(directory):
        tests = filter(is_python_extension, filenames)
        tests = [dirpath + t for t in tests]
        break
    # Compile and run each test program, comparing output to the golden file.
    successful_passes = 0
    total_passes = 0
    successful_tests = 0
    total_tests = 0
    for test in tests:
        (succ_passes, tot_passes, succ_test) = \
            run_one_test(test, lang, compiler, compiler_name,
                         type_check_dict, interp_dict)
        successful_passes += succ_passes
        total_passes += tot_passes
        successful_tests += succ_test
        total_tests += 1

    # Report the pass/fails
    print(f'compiler: {compiler_name} on language {lang}:')
    print(f'tests: ${successful_tests} / ${total_tests}')
    print(f'passes: ${successful_passes} / ${total_passes}')
    
