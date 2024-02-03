from abc import abstractmethod
import ast
from typing import List, Any,Literal, TypeAlias, Dict
from abc import ABC
from iup.utils.utils import CProgram

import iup.x86.x86_ast as x86

PassName: TypeAlias = str
Language = Literal['Py', 'X86', 'CLike']
Program = ast.Module | x86.X86Program | CProgram


class Pass(ABC):

    name: PassName

    @abstractmethod
    def run(self, prog: Program, manager: 'PassManager') -> Any: ...
    
    @abstractmethod
    def pure(self) -> bool: ...

class TransformPass(Pass):
    source: Language
    target: Language
    @abstractmethod
    def run(self, prog: Program, manager: 'PassManager') -> Program: ...
    
    def pure(self) -> bool:
        return False


class AnalysisPass(Pass):
    @abstractmethod
    def run(self, prog: Program, manager: 'PassManager') -> Any: ...
    
    def pure(self) -> bool:
        return True


class PassManager(TransformPass):
    transforms: List[TransformPass]
    analyses: Dict[PassName, AnalysisPass]
    cache: Dict[PassName, Any]
    prog: Program
    lang: str
    
    def __init__(self, transforms: List[TransformPass], analyses: List[AnalysisPass], lang='Lvar') -> None:
        self.transforms = transforms
        self.source = transforms[0].source
        self.target = transforms[-1].target
        self.analyses = {}
        for p in analyses:
            self.analyses[p.name] = p
        self.cache = {}
        self.lang = lang

    
    def invalidate(self, passes: List[PassName]):
        for p in passes:
            if p in self.cache:
                self.cache[p] = None
                
    def get_result(self, name: PassName):
        if not name in self.cache:
            self.cache[name] = self.analyses[name].run(self.prog, self)
        return self.cache[name]
    
    def run_analysis(self, name: PassName):
        self.cache[name] = self.analyses[name].run(self.prog, self)

    def run(self, prog: Program, manager: 'PassManager') -> Program:
        self.prog = prog
        
        for trans in self.transforms:
            self.prog = trans.run(self.prog, self)
            print('after ' + trans.name + ' :\n')
            print(str(self.prog))
        
        self.cache = {}
        return self.prog
        


CompilerConfig = List[Pass]
