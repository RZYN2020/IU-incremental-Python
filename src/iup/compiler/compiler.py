import select
from typing import List, Dict, Tuple

from pytest import mark
from iup.utils import generate_name, align, Begin
from iup.utils.utils import Allocate, Collect, GlobalValue, Goto, label_name, CProgram
import iup.x86.x86_ast as x86
import ast
from iup.compiler.pass_manager import TransformPass, PassManager

Binding = Tuple[ast.Name, ast.expr]
Temporaries = List[Binding]

############################################################################
# Shrink Pass (convert and/or to if)
############################################################################
class ShrinkPass(TransformPass):

    name = 'shrink'
    source = 'Py'
    target = 'Py'
    
    def shrink_exp(self, e: ast.expr) -> ast.expr:
        match e:
            case ast.Name(_):
                return e
            case ast.BinOp(left, op, right):
                new_left = self.shrink_exp(left)
                new_right = self.shrink_exp(right)
                return ast.BinOp(new_left, op, new_right)
            case ast.BoolOp(ast.And(), [left, right]):
                new_left = self.shrink_exp(left)
                new_right = self.shrink_exp(right)
                return ast.IfExp(new_left, new_right, ast.Constant(False))
            case ast.BoolOp(ast.Or(), [left, right]):
                new_left = self.shrink_exp(left)
                new_right = self.shrink_exp(right)
                return ast.IfExp(new_left, ast.Constant(True), new_right)
            case ast.UnaryOp(ast.USub(), v):
                return ast.UnaryOp(ast.USub(), self.shrink_exp(v))
            case ast.Constant(_) | ast.Call(ast.Name('input_int'), [], _) | ast.IfExp(_,_,_):
                return e
            case ast.Compare(left, [op], [right]):
                return e
            case _:
                raise Exception('error in shrink_exp, unexpected ' + repr(e))
    
    def shrink_stmt(self, s: ast.stmt) -> ast.stmt:
        
        match s:
            case ast.Assign([ast.Name(id)], value):
                return ast.Assign([ast.Name(id)], self.shrink_exp(value))
            case ast.Expr(ast.Call(ast.Name('print'), [arg], keywords)):
                return ast.Expr(ast.Call(ast.Name('print'), [self.shrink_exp(arg)], keywords))
            case ast.Expr(value):  # may have side effects in production
                return ast.Expr(self.shrink_exp(value))
            # tail of the basic block
            case ast.If(test, body, orelse):
                new_test = self.shrink_exp(test)
                new_body = [self.shrink_stmt(stmt) for stmt in body]
                new_orelse = [self.shrink_stmt(stmt) for stmt in orelse]
                return ast.If(new_test, new_body, new_orelse)
            case ast.While(test, body, []):
                new_test = self.shrink_exp(test)
                new_body = [self.shrink_stmt(stmt) for stmt in body]
                return ast.While(new_test, new_body, [])
            case _:
                raise Exception('rco_stmt: unexpected ' + repr(s))
    
    # assume just one block currenctly
    def run(self, prog: ast.Module, manager: PassManager) -> ast.Module:
        stmts = [self.shrink_stmt(stmt) for stmt in prog.body]
        return ast.Module(stmts)
            

############################################################################
# Expose Allocation Pass
############################################################################
class ExposeAllocationPass(TransformPass):
    
    def expose_exp(self, e: ast.expr) -> ast.expr:
        match e:
            case ast.Name(id):
                return ast.Name(id)
            case ast.BinOp(left, op, right):
                new_left = self.expose_exp(left)
                new_right = self.expose_exp(right)
                return ast.BinOp(new_left, op, new_right)
            case ast.UnaryOp(ast.USub(), v):
                return ast.UnaryOp(ast.USub(), self.expose_exp(v))
            case ast.Constant(value):
                return ast.Constant(value)
            case ast.Call(ast.Name('input_int'), [], keywords):
                return ast.Call(ast.Name('input_int'), [], keywords)
            case ast.IfExp(test, body, orelse):
                new_test = self.expose_exp(test)
                new_body = self.expose_exp(body) 
                new_orelse = self.expose_exp(orelse) 
                return ast.IfExp(new_test, new_body, new_orelse)
            case ast.Compare(left, [op], [right]):
                new_left= self.expose_exp(left)
                new_right = self.expose_exp(right)
                return ast.Compare(new_left, [op], [new_right])
            case ast.Tuple(es, ast.Load()):
                inits = []
                xs = []
                len_ = len(es)
                bytes_ = len_ * 8 + 8
                
                for e in es:
                    x = ast.Name(generate_name('init.'))
                    xs.append(x)
                    inits.append(ast.Assign([x], self.expose_exp(e)))
                
                v = ast.Name(generate_name('alloc.'))
                inits.extend([
                        ast.If(ast.Compare(
                            ast.BinOp(GlobalValue("free_ptr"), ast.Add(), ast.Constant(bytes_)),
                            [ast.Lt()], 
                            [GlobalValue("fromspace_end")]
                            ),[],[Collect(bytes_)]),
                        ast.Assign([v], Allocate(len_, e.has_type)) #type: ignore
                ])    
                
                for i, x in enumerate(xs):
                    inits.append(
                        ast.Assign(
                            [ast.Subscript(v, ast.Constant(i))], x
                            )
                        )
                    
                return Begin(inits, v)
            case ast.Subscript(tup, index, ast.Load()):
                return ast.Subscript(tup, index, ast.Load())
            case ast.Call(ast.Name('len'), [tup]):
                return ast.Call(ast.Name('len'), [tup])
            case _:
                raise Exception('error in interp_exp, unexpected ' + repr(e))

    
    def expose_stmt(self, s: ast.stmt) -> ast.stmt:
        match s:
            case ast.Assign([ast.Name(id)], value):
                return ast.Assign([ast.Name(id)], self.expose_exp(value))
            case ast.Expr(ast.Call(ast.Name('print'), [arg], keywords)):
                return ast.Expr(ast.Call(ast.Name('print'), [self.expose_exp(arg)], keywords))
            case ast.Expr(value):
                return ast.Expr(self.expose_exp(value))
            case ast.If(test, body, orelse):
                new_test = self.expose_exp(test)
                new_body = [self.expose_stmt(s) for s in body ]
                new_orelse = [self.expose_stmt(s) for s in orelse]
                return ast.If(new_test, new_body, new_orelse)
            case ast.While(test, body, []):
                new_test= self.expose_exp(test)
                new_body = [self.expose_stmt(s) for s in body]
                return ast.While(new_test, new_body, [])
            case _:
                raise Exception('rco_stmt: unexpected ' + repr(s))

    def run(self, prog: ast.Module, manager: PassManager) -> ast.Module: #type: ignore
        stmts = [self.expose_stmt(s) for s in prog.body]
        return ast.Module(stmts)
 
############################################################################
# Remove Complex Operands
############################################################################
class RCOPass(TransformPass):

    name = 'remove_complex_operands'
    source = 'Py'
    target = 'Py'
    
    '''
    Flatten Expression.
    Parameters:	
        need_atomic: if return expr should be one of [const, name], determined by the corresponding x86 instr
    '''

    def rco_exp(self, e: ast.expr, need_atomic: bool) -> Tuple[ast.expr, Temporaries]:
        match e:
            case ast.Name(id):
                return (ast.Name(id), [])
            case ast.BinOp(left, op, right):
                new_left, left_temps = self.rco_exp(left, True)
                new_right, right_temps = self.rco_exp(right, True)
                if need_atomic:
                    temp = ast.Name(generate_name("_t"))
                    return (temp, left_temps + right_temps + [(temp, ast.BinOp(new_left, op, new_right))])
                return (ast.BinOp(new_left, op, new_right), left_temps + right_temps)
            case ast.UnaryOp(ast.USub(), v):
                new_v, temps = self.rco_exp(v, True)
                if need_atomic:
                    temp = ast.Name(generate_name("_t"))
                    return (temp, temps + [(temp, ast.UnaryOp(ast.USub(), new_v))])
                return (ast.UnaryOp(ast.USub(), new_v), temps)
            case ast.Constant(value):
                return (ast.Constant(value), [])
            case ast.Call(ast.Name('input_int'), [], keywords):
                if need_atomic:
                    temp = ast.Name(generate_name("_t"))
                    return (temp, [(temp, ast.Call(ast.Name('input_int'), [], keywords))])
                return (ast.Call(ast.Name('input_int'), [], keywords), [])
            case ast.IfExp(test, body, orelse):
                new_test, temps1 = self.rco_exp(test, False)
                test_init: list[ast.stmt] = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                if len(test_init) != 0:
                    new_test = Begin(test_init, new_test)
                else:
                    new_test = new_test
                
                new_body, temps2 = self.rco_exp(body, False) 
                body_stmts: list[ast.stmt] = [ast.Assign([name], exp)
                                for (name, exp) in temps2]
                if len(body_stmts) != 0:
                    new_body = Begin(body_stmts, new_body)
                else:
                    new_body = new_body
                
                new_orelse, temps3 = self.rco_exp(orelse, False) 
                orelse_stmts: list[ast.stmt] = [ast.Assign([name], exp)
                                for (name, exp) in temps3]
                if len(orelse_stmts) != 0:
                    new_orelse = Begin(orelse_stmts, new_orelse)
                else:
                    new_orelse = new_orelse
                
                if need_atomic:
                    temp = ast.Name(generate_name("_t"))
                    return (temp, [(temp, ast.IfExp(new_test, new_body, new_orelse))])
                
                return ast.IfExp(new_test, new_body, new_orelse), []
            case ast.Compare(left, [op], [right]):
                new_left, left_temps = self.rco_exp(left, True)
                new_right, right_temps = self.rco_exp(right, True)
                if need_atomic:
                    temp = ast.Name(generate_name("_t"))
                    return (temp, left_temps + right_temps + [(temp, ast.Compare(new_left, [op], [new_right]))])
                return (ast.Compare(new_left, [op], [new_right]), left_temps + right_temps)
            case Begin(inits, val):
                new_inits = [stmt for s in inits for stmt in self.rco_stmt(s)]
                new_val, temps = self.rco_exp(val, False)
                return (Begin(new_inits, new_val), temps)
            case Allocate(len_, type):
                return (Allocate(len_, type), [])
            case GlobalValue(name):
                return (GlobalValue(name), [])
            case ast.Call(ast.Name('len'), [tup]):
                new_tup, temps = self.rco_exp(tup, True)
                return (ast.Call(ast.Name('len'), [new_tup]), temps)
            case ast.Subscript(tup, idx, ast.Load()):
                new_tup, temps1 = self.rco_exp(tup, True)
                new_idx, temps2 = self.rco_exp(idx, True)
                return (ast.Subscript(new_tup, new_idx, ast.Load()), temps1 + temps2)
            case _:
                raise Exception('error in interp_exp, unexpected ' + repr(e))

    '''
    Convert to 3AC actually...
    '''

    def rco_stmt(self, s: ast.stmt) -> list[ast.stmt]:
        stmts: list[ast.stmt]
        temp_assigns: list[ast.stmt]
        match s:
            case ast.Assign([ast.Name(id)], value):
                new_value, temps1 = self.rco_exp(value, False)
                temp_assigns = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                stmts = temp_assigns + [ast.Assign([ast.Name(id)], new_value)]
            case ast.Expr(ast.Call(ast.Name('print'), [arg], keywords)):
                new_arg, temps1 = self.rco_exp(arg, True)
                temp_assigns = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                stmts = temp_assigns + \
                    [ast.Expr(ast.Call(ast.Name('print'), [new_arg], keywords))]
            case ast.Expr(value):  # may have side effects in production
                new_value, temps1 = self.rco_exp(value, False)
                temp_assigns = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                stmts = temp_assigns + [ast.Expr(new_value)]
            case ast.If(test, body, orelse):
                new_test, temps1 = self.rco_exp(test, False)
                temp_assigns = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                new_body = [stmt for s in body for stmt in self.rco_stmt(s)]
                new_orelse = [stmt for s in orelse for stmt in self.rco_stmt(s)]
                stmts = temp_assigns + [ast.If(new_test, new_body, new_orelse)]
            case ast.While(test, body, []):
                new_test, temps1 = self.rco_exp(test, False)
                temp_assigns = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                new_body = [stmt for s in body for stmt in self.rco_stmt(s)]
                stmts = temp_assigns + [ast.While(new_test, new_body, [])]
            case Collect(bytes_):
                stmts = [Collect(bytes_)]
            case ast.Assign([ast.Subscript(tup, idx, ast.Load())], value):
                new_tup, temps1 = self.rco_exp(tup, True)
                temp_assigns = [ast.Assign([name], exp)
                                for (name, exp) in temps1]
                new_idx, temps2 = self.rco_exp(idx, True)
                temp_assigns += [ast.Assign([name], exp)
                                for (name, exp) in temps2]
                new_val, temps3 = self.rco_exp(value, True)
                temp_assigns += [ast.Assign([name], exp)
                                for (name, exp) in temps3]
                stmts = temp_assigns + [ast.Assign([ast.Subscript(new_tup, new_idx, ast.Load())], new_val)]
            case _:
                raise Exception('rco_stmt: unexpected ' + repr(s))
        return stmts

    def run(self, prog: ast.Module, manager: PassManager) -> ast.Module: #type: ignore
        stmts = [stmt for s in prog.body for stmt in self.rco_stmt(s)]
        return ast.Module(stmts)



############################################################################
# Explicate Control (Lif)
############################################################################

'''
Change Ifs to Gotos
(And make every if corresponding to a compare)
'''
class ExplicateControlPass(TransformPass):
    name = 'explicate_control'
    source = 'Py'
    target = 'CLike'
    
    def create_block(self, stmts: list[ast.stmt], basick_blocks: dict[str, list[ast.stmt]]) -> list[ast.stmt]: 
        match stmts:
            case [Goto(_)]:
                return stmts
            case _:
                label = label_name(generate_name('block'))
                basick_blocks[label] = stmts
                return [Goto(label)]
    
    def explicate_effect(self, e, cont, basic_blocks) -> list[ast.stmt]:
        match e:
            case ast.IfExp(test, body, orelse):
                curr = self.create_block(cont, basic_blocks)
                new_body = self.explicate_effect(body, curr, basic_blocks) # new block
                new_orelse = self.explicate_effect(orelse, curr, basic_blocks)
                return self.explicate_pred(test, new_body, new_orelse, basic_blocks)
            case ast.Call(func, args):
                return [ast.Expr(e)] + cont
            case Begin(body, result):
                for s in reversed(body):
                    cont = self.explicate_stmt(s, cont, basic_blocks)
                return cont
            case Allocate(len_, type):
                return [ast.Expr(e)] + cont
            case _:
                return cont
                
    def explicate_assign(self, rhs, lhs, cont, basic_blocks) -> list[ast.stmt]:
        match rhs:
            case ast.IfExp(test, body, orelse):
                curr = self.create_block(cont, basic_blocks)
                # holly shit, so smart, not explicate_effect but explicate_assign! don't deconstruct but translate!
                new_body = self.explicate_assign(body, lhs, curr, basic_blocks)
                new_orelse = self.explicate_assign(orelse, lhs, curr, basic_blocks)
                return self.explicate_pred(test, new_body, new_orelse, basic_blocks)
            case Begin(body, result):
                cont = [ast.Assign([lhs], result)] + cont
                for s in reversed(body):
                    cont = self.explicate_stmt(s, cont, basic_blocks)
                return cont
            case _:
                return [ast.Assign([lhs], rhs)] + cont
        

    def explicate_pred(self, cnd, thn, els, basic_blocks) -> list[ast.stmt]:
        match cnd:
            case ast.Compare(left, [op], [right]):
                goto_thn = self.create_block(thn, basic_blocks)
                goto_els = self.create_block(els, basic_blocks)
                return [ast.If(cnd, goto_thn, goto_els)]
            case ast.Constant(True):
                return thn
            case ast.Constant(False):
                return els
            case ast.UnaryOp(ast.Not(), operand):
                goto_thn = self.create_block(thn, basic_blocks)
                goto_els = self.create_block(els, basic_blocks)
                return [ast.If(cnd, goto_thn, goto_els)]
            case ast.IfExp(test, body, orelse):
                # holly recursion
                goto_thn = self.explicate_pred(body, thn, els, basic_blocks)
                goto_els = self.explicate_pred(orelse, thn, els, basic_blocks)
                return self.explicate_pred(test, goto_thn, goto_els, basic_blocks)
            case Begin(body, result):
                cont = self.explicate_pred(result, thn, els, basic_blocks)
                for s in reversed(body):
                    cont = self.explicate_stmt(s, cont, basic_blocks)
                return cont
            case _:
                return [ast.If(ast.Compare(cnd, [ast.Eq()], [ast.Constant(False)]),
                    self.create_block(els, basic_blocks),
                    self.create_block(thn, basic_blocks))]
                

    def explicate_stmt(self, s, cont, basic_blocks) -> list[ast.stmt]:
        match s:
            case ast.Assign([lhs], rhs):
                return self.explicate_assign(rhs, lhs, cont, basic_blocks)
            case ast.Expr(value):
                return self.explicate_effect(value, cont, basic_blocks)
            case ast.If(test, body, orelse):
                curr = self.create_block(cont, basic_blocks)
                
                new_body = curr
                for s in reversed(body):
                    new_body = self.explicate_stmt(s, new_body, basic_blocks)

                new_orelse = curr
                for s in reversed(orelse):
                    new_orelse = self.explicate_stmt(s, new_orelse, basic_blocks)
                    
                return self.explicate_pred(test, new_body, new_orelse, basic_blocks)
            case ast.While(test, body, []):
                curr = self.create_block(cont, basic_blocks)
                
                new_body = []
                for s in reversed(body):
                    new_body = self.explicate_stmt(s, new_body, basic_blocks)
                
                new_body_label = self.create_block(new_body, basic_blocks)
                
                loop_head = self.explicate_pred(test, new_body_label, curr, basic_blocks)
                loop_head = self.create_block(loop_head, basic_blocks)
                
                # a liitle hack
                new_body.extend(loop_head)
                
                return loop_head
                
                
            case _:
                raise Exception('error in explicate_stmt, unexpected ' + repr(s))

        
    # generate backward...
    def run(self, p: ast.Module, manager: PassManager) -> CProgram: #type: ignore
        match p:
            case ast.Module(body):
                new_body = [ast.Return(ast.Constant(0))]
                basic_blocks = {}
                for s in reversed(body):
                    new_body = self.explicate_stmt(s, new_body, basic_blocks)
                basic_blocks[label_name('start')] = new_body
                return CProgram(basic_blocks)


############################################################################
# Select Instructions
############################################################################
class SelectInstrPass(TransformPass): 

    name = 'select_instructions'
    source = 'Py'
    target = 'X86'
    
    
    def select_arg(self, e: ast.expr) -> x86.arg:
        match e:
            case ast.Constant(True):
                return x86.Immediate(1)
            case ast.Constant(False):
                return x86.Immediate(0)
            case ast.Constant(value):
                return x86.Immediate(value)
            case ast.Name(id):
                return x86.Variable(id)
            case _:
                raise Exception('select_stmt: unexpected ' + repr(e))

    def get_cc(self, cmp) -> str:
        match cmp:
            case ast.Eq():
                return 'e'
            case ast.Lt():
                return 'l'
            case ast.LtE():
                return 'le'
            case ast.Gt():
                return 'g'
            case ast.GtE():
                return 'ge'
            case _:
                raise Exception("unknow" + repr(cmp))

    def select_stmt(self, s: ast.stmt) -> List[x86.instr]:
        match s:
            # Assign
            ## Special Cases
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
            case ast.Assign([ast.Name(id1)], ast.UnaryOp(ast.Not(), ast.Name(id2))) if id1 == id2:
                return [x86.Instr('xorq', [x86.Immediate(1), x86.Variable(id1)])]
            ## Common Cases
            case ast.Assign([ast.Name(id)], ast.UnaryOp(ast.USub(), arg)):
                return [x86.Instr('movq', [self.select_arg(arg), x86.Variable(id)]),
                        x86.Instr('negq', [x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.Constant(_) | ast.Name(_)):
                return [x86.Instr('movq', [self.select_arg(s.value), x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.Call(ast.Name('input_int'), [], _)):
                return [x86.Callq('read_int', 1),
                        x86.Instr('movq', [x86.Reg('rax'), x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.Compare(left,[cmp],[right])):
                return [x86.Instr('cmpq', [self.select_arg(right), self.select_arg(left)]),
                        x86.Instr('set' + self.get_cc(cmp), [x86.Reg('al')]),
                        x86.Instr('movzq', [x86.Reg('al'), x86.Variable(id)])]
            case ast.Assign([ast.Name(id)], ast.UnaryOp(ast.Not(), arg)):
                return [x86.Instr('movq', [self.select_arg(arg), x86.Variable(id)]),
                        x86.Instr('xorq', [x86.Immediate(1), x86.Variable(id)])]
            # Expr
            case ast.Expr(ast.Call(ast.Name('print'), [arg], _)):
                return [x86.Instr('movq', [self.select_arg(arg), x86.Reg('rdi')]),
                        x86.Callq('print_int', 1)]
            case ast.Expr(ast.Call(ast.Name('input_int'), [arg], _)):
                return [x86.Callq('read_int', 1)]
            case ast.Expr(_):
                return []
            # Tail
            case Goto(label):
                return [x86.Jump(label)]
            case ast.If(ast.Compare(left,[cmp],[right]), [Goto(label1)], [Goto(label2)]):
                return [x86.Instr('cmpq', [self.select_arg(right), self.select_arg(left)]),
                        x86.JumpIf(self.get_cc(cmp), label1),
                        x86.Jump(label2)]
            case ast.Return(v):
                return [x86.Jump('conclusion')]
            case _:
                raise Exception('select_stmt: unexpected ' + repr(s))

    def run(self, p: CProgram, manager: PassManager) -> x86.X86Program: #type: ignore
        body = {}
        for bk, ss in p.body.items():
            body[bk] = [stmt for s in ss for stmt in self.select_stmt(s)]
        return x86.X86Program(body)



############################################################################
# Assign Homes
############################################################################
class AssignHomePass(TransformPass):

    name = 'assign_homes'
    source = 'X86'
    target = 'X86'
    
    def assign_homes_arg(self, a: x86.arg, home: Dict[x86.Variable, x86.arg]) -> x86.arg:
        match a:
            case x86.Variable(_):
                if not a in home:
                    self.stack_space += 8
                    home[a] = x86.Deref('rbp', -self.stack_space)
                return home[a]
            case x86.Reg(_) | x86.Immediate(_) as ri:
                return ri
            case _:
                raise Exception('assign_homes_arg: unexpected ' + repr(a))

    def assign_homes_instr(self, i: x86.instr,
                           home: Dict[x86.Variable, x86.arg]) -> x86.instr:
        match i:
            case x86.Instr(op, [left, right]):
                left = self.assign_homes_arg(left, home)
                right = self.assign_homes_arg(right, home)
                return x86.Instr(op, [left, right])
            case x86.Instr(op, [arg]):
                arg = self.assign_homes_arg(arg, home)
                return x86.Instr(op, [arg])
            case x86.Callq(_, _) as call:
                return call
            # case x86.Instr('pushq', [arg]):
            #     ...
            # case x86.Instr('popq', [arg]):
            #     ...
            # case x86.Instr('label', id):
            #     ...
            case _:
                raise Exception('assign_homes_instr: unexpected ' + repr(i))

    def assign_homes_instrs(self, inss: List[x86.instr],
                            home: Dict[x86.Variable, x86.arg]) -> List[x86.instr]:
        instrs: List[x86.instr] = []
        for i in inss:
            instrs.append(self.assign_homes_instr(i, home))
        return instrs

    def run(self, p: x86.X86Program, manager: PassManager) -> x86.X86Program: #type: ignore
        self.stack_space = 0
        instrs = self.assign_homes_instrs(p.body, {}) #type: ignore
        return x86.X86Program(instrs, self.stack_space)



############################################################################
# Patch Instructions
############################################################################
class PatchInsPass(TransformPass):

    name = 'patch_instructions'
    source = 'X86'
    target = 'X86'
    
    def patch_instr(self, i: x86.instr) -> List[x86.instr]:
        match i:
            case x86.Instr(op, [x86.Deref(_, _) as m1, x86.Deref(_, _) as m2]):
                return [
                    x86.Instr('movq', [m1, x86.Reg('rax')]),
                    x86.Instr(op, [x86.Reg('rax'), m2]),
                ]
            case x86.Instr(op, [x86.Immediate(imm), x86.Deref(_, _) as m2]) if imm > (1 << 16):
                return [
                    x86.Instr('movq', [x86.Immediate(imm), x86.Reg('rax')]),
                    x86.Instr(op, [x86.Reg('rax'), m2]),
                ]
            case x86.Instr(op, [x86.Deref(_, _) as m1, x86.Immediate(imm)]) if imm > (1 << 16):
                return [
                    x86.Instr('movq', [x86.Immediate(imm), x86.Reg('rax')]),
                    x86.Instr(op, [m1, x86.Reg('rax')]),
                ]
            case x86.Instr('cmpq', [m1, x86.Immediate(imm)]):
                return [
                    x86.Instr('movq', [x86.Immediate(imm), x86.Reg('rax')]),
                    x86.Instr('cmpq', [m1, x86.Reg('rax')]),
                ]
            case _:
                return [i]

    def patch_instrs(self, ss: List[x86.instr]) -> List[x86.instr]:
        return [instr for s in ss for instr in self.patch_instr(s)]

    def run(self, p: x86.X86Program, manager: PassManager) -> x86.X86Program: #type: ignore
        
        body = {}
        for lb, bk in p.body.items(): #type: ignore
            body[lb] = [stmt for stmt in self.patch_instrs(bk)] #type: ignore
        
        for lb, bk in body.items():
            pbk = []
            for i in bk:
                match i:
                    case x86.Instr('movq', [a, b]):
                        if a != b:
                            pbk.append(i)
                    case _:
                        pbk.append(i)
            body[lb] = pbk
                    
        prog = x86.X86Program(body)
        prog.stack_space = p.stack_space
        prog.used_callee = []
        return prog



############################################################################
# Prelude & Conclusion
############################################################################
class PreConPass(TransformPass):
    
    name = 'prelude_and_conclusion'
    source = 'X86'
    target = 'X86'
    
    def run(self, p: x86.X86Program, manager: PassManager) -> x86.X86Program: #type: ignore
        sp = p.stack_space
        offset = align(sp, 16) - 8 * len(p.used_callee)
        prelude = [
            x86.Instr('pushq', [x86.Reg('rbp')]),
            x86.Instr('movq', [x86.Reg('rsp'), x86.Reg('rbp')])] \
            + [x86.Instr('pushq', [r]) for r in p.used_callee]

        if offset > 0:
            prelude += [x86.Instr('subq', [x86.Immediate(offset), x86.Reg('rsp')])]
            conlusion = [x86.Instr('addq', [x86.Immediate(offset), x86.Reg('rsp')])]
        else:
            conlusion = []

        prelude += [x86.Jump('start')]
        
        conlusion += \
            [x86.Instr('popq', [r]) for r in reversed(p.used_callee)] \
            + [x86.Instr('popq', [x86.Reg('rbp')]),
               x86.Instr('retq', [])
               ]
            
        p.body['main'] = prelude #type: ignore
        p.body['conclusion'] = conlusion #type: ignore
        return p


