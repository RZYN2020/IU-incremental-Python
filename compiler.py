import ast
from ast import *
from utils.utils import *
from x86.x86_ast import *
import os
from typing import List, Tuple, Set, Dict, Union

Binding = Tuple[Name, expr]
Temporaries = List[Binding]

def ea_to_stmts(stmts: List[Expr | Assign]) -> List[stmt]:
    return [s if isinstance(s, stmt) else Expr(value=s.value) for s in stmts]

def a_to_stmts(stmts: List[Assign]) -> List[stmt]:
    return [s if isinstance(s, stmt) else Expr(value=s.value) for s in stmts]

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
        
        
    def rco_stmt(self, s: stmt) -> List[stmt]:
        match s:
            case Assign([Name(id)], value):
                new_value, temps = self.rco_exp(value, False)
                stmts = [Assign([name], exp) for (name, exp) in temps] + [Assign([Name(id)], new_value)]
                return a_to_stmts(stmts)
            case Expr(Call(Name('print'), [arg], keywords)):
                new_arg, temps = self.rco_exp(arg, True)
                stmts = [Assign([name], exp) for (name, exp) in temps] + [Expr(Call(Name('print'), [new_arg], keywords))]
                return ea_to_stmts(stmts)
            case Expr(value):
                new_value, temps = self.rco_exp(value, False)
                stmts = [Assign([name], exp) for (name, exp) in temps] + [Expr(new_value)]
                return ea_to_stmts(stmts)
            case _:
                raise Exception('rco_stmt: unexpected ' + repr(s))
            
        

    def remove_complex_operands(self, p: Module) -> Module:
        match p:
            case Module(body):
                stmts = [stmt for s in body for stmt in self.rco_stmt(s)]
                return Module(stmts)
            case _:
                raise Exception('remove_complex_operands: unexpected ' + repr(p))

    ############################################################################
    # Select Instructions
    ############################################################################

    def select_arg(self, e: expr) -> arg:
        # YOUR CODE HERE
        ...        

    def select_stmt(self, s: stmt) -> List[instr]:
        # YOUR CODE HERE
        ...        

    def select_instructions(self, p: Module) -> X86Program:
        # YOUR CODE HERE
        ...        

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

