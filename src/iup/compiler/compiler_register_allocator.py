from optparse import Option
from ..utils.graph import DirectedAdjList, UndirectedAdjList, topological_sort, transpose
from ..utils.priority_queue import PriorityQueue
from ..utils.dict import TwoWayDict
from typing import Any, Optional, Tuple, Set, Dict, List
import iup.x86.x86_ast as x86
from typing import Set, Dict, Tuple
from .pass_manager import AnalysisPass, TransformPass, PassManager


reg_map = TwoWayDict({
    0:  x86.Reg('rcx'),
    1:  x86.Reg('rdx'),
    2:  x86.Reg('rsi'),
    3:  x86.Reg('rdi'),
    4:  x86.Reg('r8'),
    5:  x86.Reg('r9'),
    6:  x86.Reg('r10'),
    7:  x86.Reg('rbx'),
    8:  x86.Reg('r12'),
    9:  x86.Reg('r13'),
    10: x86.Reg('r14'),
    -1: x86.Reg('rax'),
    -2: x86.Reg('rsp'),
    -3: x86.Reg('rbp'),
    -4: x86.Reg('r11'),
    -5: x86.Reg('r15'),
})

callee_saved = [x86.Reg('rbx'), x86.Reg('r12'), x86.Reg('r13'), x86.Reg('r14'), x86.Reg('r15')]

###########################################################################
# Uncover Live
###########################################################################
class UncoverLivePass(AnalysisPass):
    
    name = "uncover_live"

    # decidebale version of liveness analysis

    @staticmethod
    def read_vars(i: x86.instr) -> Set[x86.location]:
        match i:
            case x86.Instr(_, [x86.Reg(_) | x86.Variable(_) as a, _]):  # binary op
                return {a}
            case x86.Instr(_, [a]):  # unary op
                return {a} #type: ignore
            case x86.Callq(_, _):
                # suppose arity of func 1 (we just have print_int currently)
                return {x86.Reg('rdi')}
            case _:
                return set()

    # location must be Variable or Register
    @staticmethod
    def write_vars(i: x86.instr) -> Set[x86.location]:
        match i:
            case x86.Instr(_, [_, b]):  # binary op
                return {b} #type: ignore
            case x86.Instr(_, [a]):  # unary op
                return {a} #type: ignore
            case x86.Callq(_, _):
                # all caller-saved registers
                return {
                    x86.Reg("rax"),
                    x86.Reg("rcx"),
                    x86.Reg("rdx"),
                    x86.Reg("rsi"),
                    x86.Reg("rdi"),
                    x86.Reg("r8"),
                    x86.Reg("r9"),
                    x86.Reg("r10"),
                    x86.Reg("r11"),
                }
            case _:
                return set()

    def run(self, p: x86.X86Program, manager: PassManager) -> Dict[str, Dict[x86.instr, Set[x86.location]]]: #type: ignore
        res : Dict[str, Dict[x86.instr, Set[x86.location]]] = {}
        
        def get_target(bk: List[x86.instr]) -> List[str]:
            match reversed(bk):
                case [x86.Jump(label), *_]:
                    return [label]
                case [x86.Jump(label2), x86.JumpIf(_, label1), x86.Instr('cmpq', _), *_]:
                    return [label1, label2]
                case _:
                    return []
        
        cfg = DirectedAdjList()
        for lb, bk in p.body.items(): #type: ignore
            cfg.add_vertex(lb)
            for tg in get_target(bk):
                cfg.add_vertex(tg)
                cfg.add_edge(lb, tg)
                
        vs = topological_sort(transpose(cfg))
        
        live_before_block: Dict[str, Set[x86.location]] = {}
        for v in vs:
            live_vars: Dict[x86.instr, Set[x86.location]] = {}
            cur_live: Set[x86.location] = set()
            for e in cfg.in_edges(v):
                cur_live = cur_live.union(live_before_block[e.source])
                
            for i in reversed(p.body[v]): #type: ignore
                i : x86.instr 
                live_vars[i] = cur_live
                reads = self.read_vars(i)
                writes = self.write_vars(i)
                cur_live = cur_live.difference(writes).union(reads)
                
            live_before_block[v] = cur_live
            res[v] = live_vars
            
        return res


############################################################################
# Build Interference
############################################################################
class BuildInterferencePass(AnalysisPass):
    
    name = "build_interference"
    
    def run(self, p: x86.X86Program, manager: PassManager) -> UndirectedAdjList: #type: ignore
        
        live_after: Dict[str, Dict[x86.instr, Set[x86.location]]] = manager.get_result("uncover_live")
        
        graph = UndirectedAdjList()
        # simple O(n^2) implementation
        # for i in p.body:
        #     for a in live_after[i]:
        #         for b in live_after[i]:
        #             if a != b:
        #                 graph.add_edge(a, b)

        # O(n) implementation
        for lb, bk in p.body.items(): #type: ignore
            for i in bk:
                match i:
                    case x86.Instr('movq' | 'movzbq', [x86.Reg(_) | x86.Variable(_) as a, x86.Reg(_) | x86.Variable(_) as b]):
                        lives = live_after[lb][i]
                        for l in lives:
                            if a != l and b != l: # As long as no write to a/b, a and b don't inference each other.
                                if not graph.has_edge(a, l): #type: ignore
                                    graph.add_edge(a, l) #type: ignore
                    case _:
                        writes = UncoverLivePass.write_vars(i) #type: ignore
                        lives = live_after[lb][i]
                        for a in writes:
                            for b in lives:
                                if a != b:
                                    if not graph.has_edge(a, b): #type: ignore
                                        graph.add_edge(a, b) #type: ignore

        return graph

############################################################################
# Allocate Registers
############################################################################
class AllocateRegPass(TransformPass):
    
    name = 'allocate_registers'
    source = 'X86'
    target = 'X86' 
    
    
    # Returns the coloring and the set of spilled variables.
    def color_graph(self, graph: UndirectedAdjList,
                    variables: Set[x86.location]) -> Tuple[Dict[x86.location, int], Set[x86.location]]:

        colors: Dict[x86.location, int] = dict({v: k for k, v in reg_map.items()}) #type: ignore
        spilled: Set[x86.location] = set()

        def saturation(x): #type: ignore
            return len([p for p in graph.out[x.key] if p in colors]) #type: ignore

        worklist = PriorityQueue(lambda x, y: saturation(x) < saturation(y)) #type: ignore
        for p in variables:
            worklist.push(p) #type: ignore

        while not worklist.empty():
            p = worklist.pop()  #type: ignore
            adjs = [colors[adj] for adj in graph.out[p] if adj in colors] #type: ignore
            allocp = 0

            # we can use Move Biasing here to remove more move operations
            while allocp in adjs:
                allocp += 1
            colors[p] = allocp  #type: ignore
            if allocp >= 11:
                spilled.add(p)  #type: ignore

        return colors, spilled

    def run(self, p: x86.X86Program, manager: PassManager) -> x86.X86Program: #type: ignore
        graph = manager.get_result('build_interference')
        vars = set()
        for bk in p.body.values(): #type: ignore
            for i in bk:
                for v in UncoverLivePass.write_vars(i):
                    if isinstance(v, x86.Variable):
                        vars.add(v)

        for v in vars:
            graph.add_vertex(v)
        colors, spilled = self.color_graph(graph, vars) #type: ignore

        def alloc_reg(a: Any) -> x86.Reg | x86.Deref:
            if a in spilled:
                return x86.Deref('rbp', - 8 * (colors[a] - 11))
            elif a in colors:
                return reg_map[colors[a]] #type: ignore
            else:
                return a

        body: Dict[str, List[x86.instr]] = {}
        for lb, bk in p.body.items(): #type: ignore
            body[lb] = []
            for i in bk:
                match i:
                    case x86.Instr(op, [a, b]):
                        body[lb].append(x86.Instr(op, [alloc_reg(a), alloc_reg(b)]))
                    case x86.Instr(op, [a]):
                        body[lb].append(x86.Instr(op, [alloc_reg(a)]))
                    case _:
                        body[lb].append(i)  #type: ignore

        regs: Set[x86.Reg] = set()
        for bk in body.values(): #type: ignore
            for i in bk:
                match i:
                    case x86.Instr(_, [x86.Reg(_) as a, *_]):
                        regs.add(a)
                    case x86.Instr(_, [_, x86.Reg(_) as a]):
                        regs.add(a)
                    case _:
                        pass

        used_callee = [r for r in regs if r in callee_saved]
        prog = x86.X86Program(body)
        prog.stack_space = (len(spilled) + len(used_callee)) * 8
        prog.used_callee = used_callee
        return prog


