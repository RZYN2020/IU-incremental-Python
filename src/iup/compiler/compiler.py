from typing import List, Dict, Tuple, ClassVar, Optional
from iup.utils import generate_name
import iup.x86.x86_ast as x86
import iup.x86.x86exp as x86exp
import ast

Binding = Tuple[ast.Name, ast.expr]
Temporaries = List[Binding]

class Compiler:
    
    __instance: ClassVar[Optional['Compiler']] = None

    def __init__(self):
        if Compiler.__instance is not None:
            raise Exception("Compiler instance already exists")
        else:
            Compiler.__instance = self

    @staticmethod
    def get_instance() -> 'Compiler':
        if Compiler.__instance is None:
            Compiler.__instance = Compiler()
        return Compiler.__instance

    ############################################################################
    # Remove Complex Operands
    ############################################################################

    def rco_exp(self, e: ast.expr, need_atomic: bool) -> Tuple[ast.expr, Temporaries]:
        match e:
            case ast.Name(id):
                return (ast.Name(id), [])
            case ast.BinOp(left, op, right):
                new_left, left_temps = self.rco_exp(left, True)
                new_right, right_temps = self.rco_exp(right, True)
                if need_atomic:
                    temp = ast.Name(generate_name("temp"))
                    return (temp, left_temps + right_temps + [(temp, ast.BinOp(new_left, op, new_right))])
                return (ast.BinOp(new_left, op, new_right), left_temps + right_temps)
            case ast.UnaryOp(ast.USub(), v):
                new_v, temps = self.rco_exp(v, True)
                if need_atomic:
                    temp = ast.Name(generate_name("temp"))
                    return (temp, temps + [(temp, ast.UnaryOp(ast.USub(), new_v))])
                return (ast.UnaryOp(ast.USub(), new_v), temps)
            case ast.Constant(value):
                return (ast.Constant(value), [])
            case ast.Call(ast.Name('input_int'), [], keywords):
                if need_atomic:
                    temp = ast.Name(generate_name("temp"))
                    return (temp, [(temp, ast.Call(ast.Name('input_int'), [], keywords))])
                return (ast.Call(ast.Name('input_int'), [], keywords), [])
            case _:
                raise Exception('error in interp_exp, unexpected ' + repr(e))

    def rco_stmt(self, s: ast.stmt) -> list[ast.stmt]:
        stmts: list[ast.stmt]
        temp_assigns: list[ast.stmt]
        match s:
            case ast.Assign([ast.Name(id)], value):
                new_value, temps = self.rco_exp(value, False)
                temp_assigns = [ast.Assign([name], exp) for (name, exp) in temps]
                stmts =  temp_assigns + [ast.Assign([ast.Name(id)], new_value)]
            case ast.Expr(ast.Call(ast.Name('print'), [arg], keywords)):
                new_arg, temps = self.rco_exp(arg, True)
                temp_assigns = [ast.Assign([name], exp) for (name, exp) in temps]
                stmts = temp_assigns + [ast.Expr(ast.Call(ast.Name('print'), [new_arg], keywords))]
            case ast.Expr(value):
                new_value, temps = self.rco_exp(value, False)
                temp_assigns = [ast.Assign([name], exp) for (name, exp) in temps]
                stmts = temp_assigns + [ast.Expr(new_value)]
            case _:
                raise Exception('rco_stmt: unexpected ' + repr(s))
        return stmts

    def remove_complex_operands(self, p: ast.Module) -> ast.Module:
        stmts = [stmt for s in p.body for stmt in self.rco_stmt(s)]
        return ast.Module(stmts)

    ############################################################################
    # Select Instructions
    ############################################################################

    def select_arg(self, e: ast.expr) -> x86.arg:
        match e:
            case ast.Constant(value):
                return x86.Immediate(value)
            case ast.Name(id):
                return x86.Variable(id)
            case _:
                raise Exception('select_stmt: unexpected ' + repr(e))

    def select_stmt(self, s: ast.stmt) -> List[x86.instr]:
        match s:
            case ast.Assign([ast.Name(id1)], ast.BinOp(ast.Name(id2), ast.Add(), right)) if id1 == id2:
                return [x86.Instr('addq', [self.select_arg(right), x86.Variable(id1)])]
            case ast.Assign([ast.Name(id)], ast.BinOp(left, ast.Add(), right)):
                return [x86.Instr('movq', [self.select_arg(right), x86.Variable(id)]),
                        x86.Instr('addq', [self.select_arg(left), x86.Variable(id)])]
            case ast.Assign([ast.Name(id1)], ast.BinOp(ast.Name(id2), ast.Sub(), right)) if id1 == id2:
                return [x86.Instr('subq', [self.select_arg(right), x86.Variable(id1)])]
            case ast.Assign([ast.Name(id)], ast.BinOp(left, ast.Sub(), right)):
                return [x86.Instr('movq', [self.select_arg(left), x86.Variable(id)]),
                        x86.Instr('subq', [self.select_arg(right), x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.UnaryOp(ast.USub(), arg)):
                return [x86.Instr('movq', [self.select_arg(arg), x86.Variable(id)]),
                        x86.Instr('negq', [x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.Constant(_) | ast.Name(_)):
                return [x86.Instr('movq', [self.select_arg(s.value), x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.Call(ast.Name('input_int'), [], _)):
                return [x86.Callq('read_int', 1),
                        x86.Instr('movq', [x86.Reg('rax'), x86.Variable(id)])]
            case ast.Expr(ast.Call(ast.Name('print'), [arg], _)):
                return [x86.Instr('movq', [self.select_arg(arg), x86.Reg('rdi')]),
                        x86.Callq('print_int', 1)]
            case ast.Expr(ast.Call(ast.Name('input_int'), [arg], _)):
                return [x86.Callq('read_int', 1)]
            case ast.Expr(ast.Constant | ast.Name):
                return []
            case ast.Expr(ast.BinOp(ast.Constant | ast.Name, _ , ast.Constant | ast.Name)):
                return []
            case ast.Expr(ast.UnaryOp(ast.USub(), ast.Constant | ast.Name)):
                return []
            case _:
                raise Exception('select_stmt: unexpected ' + repr(s))

    def select_instructions(self, p: ast.Module) -> x86.X86Program:
        stmts = [stmt for s in p.body for stmt in self.select_stmt(s)]
        return x86.X86Program(stmts)

    ############################################################################
    # Assign Homes
    ############################################################################

    def assign_homes_arg(self, a: x86.arg, home: Dict[x86.Variable, x86.arg]) -> x86.arg:
        # YOUR CODE HERE
        ...

    def assign_homes_instr(self, i: x86.instr,
                           home: Dict[x86.Variable, x86.arg]) -> x86.instr:
        # YOUR CODE HERE
        ...

    def assign_homes_instrs(self, ss: List[x86.instr],
                            home: Dict[x86.Variable, x86.arg]) -> List[x86.instr]:
        # YOUR CODE HERE
        ...

    def assign_homes(self, p: x86.X86Program) -> x86.X86Program:
        # YOUR CODE HERE
        ...

    ############################################################################
    # Patch Instructions
    ############################################################################

    def patch_instr(self, i: x86.instr) -> List[x86.instr]:
        # YOUR CODE HERE
        ...

    def patch_instrs(self, ss: List[x86.instr]) -> List[x86.instr]:
        # YOUR CODE HERE
        ...

    def patch_instructions(self, p: x86.X86Program) -> x86.X86Program:
        # YOUR CODE HERE
        ...

    ############################################################################
    # Prelude & Conclusion
    ############################################################################

    def prelude_and_conclusion(self, p: x86.X86Program) -> x86.X86Program:
        # YOUR CODE HERE
        ...
