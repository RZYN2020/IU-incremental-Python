from ..utils.graph import UndirectedAdjList
from ..utils.priority_queue import PriorityQueue
from .compiler import Compiler as CompilerBase
from ..utils.utils import align
from typing import Tuple, Set, Dict
from ast import *
from iup.x86.x86_ast import *
from typing import Set, Dict, Tuple


class TwoWayDict(dict):
    def __setitem__(self, key, value):
        # Remove any previous connections with these values
        if key in self:
            del self[key]
        if value in self:
            del self[value]
        dict.__setitem__(self, key, value)
        dict.__setitem__(self, value, key)

    def __delitem__(self, key):
        dict.__delitem__(self, self[key])
        dict.__delitem__(self, key)

    def __len__(self):
        """Returns the number of connections"""
        return dict.__len__(self) // 2

reg_map = TwoWayDict({
    0: Reg('rcx'),
    1: Reg('rdx'),
    2: Reg('rsi'),
    3: Reg('rdi'),
    4: Reg('r8'),
    5: Reg('r9'),
    6: Reg('r10'),
    7: Reg('rbx'),
    8: Reg('r12'),
    9: Reg('r13'),
    10: Reg('r14'),
    -1: Reg('rax'),
    -2: Reg('rsp'),
    -3: Reg('rbp'),
    -4: Reg('r11'),
    -5: Reg('r15'),
})



class Compiler(CompilerBase):
    callee_saved = [Reg('rbx'), Reg('r12'), Reg('r13'), Reg('r14'), Reg('r15')]
    

    ###########################################################################
    # Uncover Live
    ###########################################################################

    # decidebale version of liveness analysis
    
    def read_vars(self, i: instr) -> Set[location]:
        match i:
            case Instr(_, [Reg(_) | Variable(_) as a, _]): # binary op
                return {a}
            case Instr(_, [a]): # unary op
                return {a}
            case Callq(_, _):
                # suppose arity of func 1 (we just have print_int currently)
                return {Reg('rdi')}
            case _:
                return set()
            
    # location must be Variable or Register
    def write_vars(self, i: instr) -> Set[location]:
        match i:
            case Instr(_, [_, b]): # binary op
                return {b}
            case Instr(_, [a]): # unary op
                return {a}
            case Callq(_, _):
                # all caller-saved registers
                return {
                    Reg("rax"),
                    Reg("rcx"),
                    Reg("rdx"),
                    Reg("rsi"),
                    Reg("rdi"),
                    Reg("r8"),
                    Reg("r9"),
                    Reg("r10"),
                    Reg("r11"),
                }
            case _:
                return set()

    def uncover_live(self, p: X86Program) -> Dict[instr, Set[location]]:
        live_vars = {}
        cur_live = set()
        for i in reversed(p.body):
            live_vars[i] = cur_live
            reads = self.read_vars(i)
            writes = self.write_vars(i)
            cur_live = cur_live.difference(writes).union(reads)
        return live_vars
        
    ############################################################################
    # Build Interference
    ############################################################################

    def build_interference(self, p: X86Program,
                           live_after: Dict[instr, Set[location]]) -> UndirectedAdjList:
        graph = UndirectedAdjList()
        # simple O(n^2) implementation
        # for i in p.body:
        #     for a in live_after[i]:
        #         for b in live_after[i]:
        #             if a != b:
        #                 graph.add_edge(a, b)
        
        # O(n) implementation
        for i in p.body:
            match i:
                case Instr('movq', [Reg(_) | Variable(_) as a, Reg(_) | Variable(_) as b]):
                    lives = live_after[i]
                    for l in lives:
                        if a != l and b != l:
                            if not graph.has_edge(a, l):
                                graph.add_edge(a, l)
                case _:
                    writes = self.write_vars(i)
                    lives = live_after[i]       
                    for a in writes:    
                        for b in lives:
                            if a != b:
                                if not graph.has_edge(a, b):
                                    graph.add_edge(a, b)

        return graph

    ############################################################################
    # Allocate Registers
    ############################################################################

    # Returns the coloring and the set of spilled variables.
    def color_graph(self, graph: UndirectedAdjList,
                    variables: Set[location]) -> Tuple[Dict[location, int], Set[location]]:
                
        colors = dict({v: k for k, v in reg_map.items()})
        spilled = set()

        def saturation(x):
            return len([p for p in graph.out[x.key] if p in colors])
        
        worklist = PriorityQueue(lambda x, y: saturation(x) < saturation(y))
        for p in variables:
            worklist.push(p)
        
        while not worklist.empty():
            p = worklist.pop()
            adjs = [colors[adj] for adj in graph.out[p] if adj in colors]
            allocp = 0

            # we can use Move Biasing here to remove more move operations
            while allocp in adjs:
                allocp += 1
            colors[p] = allocp
            if allocp >= 11:
                spilled.add(p)
        
        return colors, spilled
        

    def allocate_registers(self, p: X86Program) -> X86Program:
        graph = self.build_interference(p, self.uncover_live(p))
        vars =  set([item for sublist in [self.write_vars(i) for i in p.body] for item in sublist if isinstance(item, Variable)])
        for v in vars:
            graph.add_vertex(v)
        colors, spilled = self.color_graph(graph, vars)
        
        def alloc_reg(a):
            if a in spilled:
                return Deref('rbp', - 8 * (colors[a] - 11))
            elif a in colors:
                return reg_map[colors[a]]
            else:
                return a
        
        instrs = []
        for i in p.body:
            match i:
                case Instr(op, [a, b]):
                    instrs.append(Instr(op, [alloc_reg(a), alloc_reg(b)]))
                case Instr(op, [a]):
                    instrs.append(Instr(op, [alloc_reg(a)]))
                case _:
                    instrs.append(i)
        
        regs = set()
        for i in instrs:
            match i:
                case Instr(_, [Reg(_) as a, *_]):
                    regs.add(a)
                case Instr(_, [_, Reg(_) as a]):
                    regs.add(a)
                case _:
                    pass
        
        used_callee = [r for r in regs if r in self.callee_saved]
        return X86Program(instrs, (len(spilled) + len(used_callee)) * 8, used_callee)
        

    ############################################################################
    # Assign Homes
    ############################################################################

    def assign_homes(self, pseudo_x86: X86Program) -> X86Program:
        return pseudo_x86

    ###########################################################################
    # Patch Instructions
    ###########################################################################

    def patch_instructions(self, p: X86Program) -> X86Program:
        p = super().patch_instructions(p)
        instrs = []
        for i in p.body:
            match i:
                case Instr('movq', [a, b]):
                    if a != b:
                        instrs.append(i)
                case _:
                    instrs.append(i)
        return X86Program(instrs, p.stack_space, p.used_callee)

    ###########################################################################
    # Prelude & Conclusion
    ###########################################################################

    def prelude_and_conclusion(self, p: X86Program) -> X86Program:
        sp = p.stack_space
        offset = align(sp, 16) - 8 * len(p.used_callee)
        prelude = [
            Instr('pushq', [Reg('rbp')]),
            Instr('movq', [Reg('rsp'),Reg('rbp')])] \
        + [ Instr['pushq', [r]] for r in p.used_callee]
        
        if offset > 0:
            prelude += [ Instr('subq', [Immediate(offset), Reg('rsp')])]
            conlusion= [Instr('addq', [Immediate(offset), Reg('rsp')])]
        else:
            conlusion = []
            
        conlusion += \
          [ Instr('popq', [r]) for r in reversed(p.used_callee)] \
        + [ Instr('popq', [Reg('rbp')]),
            Instr('retq', [])
        ]
        return X86Program(prelude + p.body + conlusion, sp)




