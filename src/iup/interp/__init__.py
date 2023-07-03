from iup import Language 
from typing import Dict
import ast

class Intepreter:
    def interp(self, p: ast.Module):
        ...
                
INTERPRETERS: Dict[Language, Intepreter] = {
    
}