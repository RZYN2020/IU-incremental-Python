from typing import List, Tuple, Dict
from utils import generate_name
from x86.x86_ast import (
    instr, X86Program, Variable
)

from ast import (
    Name, BinOp, UnaryOp, USub, Constant, Call, Module, Assign, Expr, 
    stmt, expr, arg, expr
)

Binding = Tuple[Name, expr]
Temporaries = List[Binding]

class Compiler:

    ############################################################################
    # Remove Complex Operands
    ############################################################################

    def rco_exp(self, e: expr, need_atomic: bool) -> Tuple[expr, Temporaries]:
        match e:
            case Name(id):
                return (Name(id), [])
            case BinOp(left, op, right):
                new_left, left_temps = self.rco_exp(left, True)
                new_right, right_temps = self.rco_exp(right, True)
                if need_atomic:
                    temp = Name(generate_name("temp"))
                    return (temp, left_temps + right_temps + [(temp, BinOp(new_left, op, new_right))])
                return (BinOp(new_left, op, new_right), left_temps + right_temps)
            case UnaryOp(USub(), v):
                new_v, temps = self.rco_exp(v, True)
                if need_atomic:
                    temp = Name(generate_name("temp"))
                    return (temp, temps + [(temp, UnaryOp(USub(), new_v))])
                return (UnaryOp(USub(), new_v), temps)
            case Constant(value):
                return (Constant(value), [])
            case Call(Name('input_int'), [], keywords):
                if need_atomic:
                    temp = Name(generate_name("temp"))
                    return (temp, [(temp, Call(Name('input_int'), [], keywords))])
                return (Call(Name('input_int'), [], keywords), [])
            case _:
                raise Exception('error in interp_exp, unexpected ' + repr(e))

    def rco_stmt(self, s: stmt) -> list[stmt]:
        stmts: list[stmt]
        temp_assigns: list[stmt]
        match s:
            case Assign([Name(id)], value):
                new_value, temps = self.rco_exp(value, False)
                temp_assigns = [Assign([name], exp) for (name, exp) in temps]
                stmts =  temp_assigns + [Assign([Name(id)], new_value)]
            case Expr(Call(Name('print'), [arg], keywords)):
                new_arg, temps = self.rco_exp(arg, True)
                temp_assigns = [Assign([name], exp) for (name, exp) in temps]
                stmts = temp_assigns + [Expr(Call(Name('print'), [new_arg], keywords))]
            case Expr(value):
                new_value, temps = self.rco_exp(value, False)
                temp_assigns = [Assign([name], exp) for (name, exp) in temps]
                stmts = temp_assigns + [Expr(new_value)]
            case _:
                raise Exception('rco_stmt: unexpected ' + repr(s))
        return stmts

    def remove_complex_operands(self, p: Module) -> Module:
        match p:
            case Module(body):
                stmts = [stmt for s in body for stmt in self.rco_stmt(s)]
                return Module(stmts)
            case _:
                raise Exception(
                    'remove_complex_operands: unexpected ' + repr(p))

    ############################################################################
    # Select Instructions
    ############################################################################

    def select_arg(self, e: expr) -> arg:
        # YOUR CODE HERE
        ...

    def select_stmt(self, s: stmt) -> List[instr]:
        match s:
            case Assign([Name(id)], value):
                ...
            case Expr(Call(Name('print'), [arg], keywords)):
                ...
            case Expr(value):
                ...
            case _:
                raise Exception('select_stmt: unexpected ' + repr(s))
        return []

    def select_instructions(self, p: Module) -> X86Program:
        match p:
            case Module(body):
                stmts = [stmt for s in body for stmt in self.select_stmt(s)]
                return X86Program(stmts)
            case _:
                raise Exception('select_instructions: unexpected ' + repr(p))

    ############################################################################
    # Assign Homes
    ############################################################################

    def assign_homes_arg(self, a: arg, home: Dict[Variable, arg]) -> arg:
        # YOUR CODE HERE
        ...

    def assign_homes_instr(self, i: instr,
                           home: Dict[Variable, arg]) -> instr:
        # YOUR CODE HERE
        ...

    def assign_homes_instrs(self, ss: List[instr],
                            home: Dict[Variable, arg]) -> List[instr]:
        # YOUR CODE HERE
        ...

    def assign_homes(self, p: X86Program) -> X86Program:
        # YOUR CODE HERE
        ...

    ############################################################################
    # Patch Instructions
    ############################################################################

    def patch_instr(self, i: instr) -> List[instr]:
        # YOUR CODE HERE
        ...

    def patch_instrs(self, ss: List[instr]) -> List[instr]:
        # YOUR CODE HERE
        ...

    def patch_instructions(self, p: X86Program) -> X86Program:
        # YOUR CODE HERE
        ...

    ############################################################################
    # Prelude & Conclusion
    ############################################################################

    def prelude_and_conclusion(self, p: X86Program) -> X86Program:
        # YOUR CODE HERE
        ...
