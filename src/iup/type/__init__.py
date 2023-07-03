from iup import Language
from typing import Dict
import ast


class TypeChecker:
    def typecheck(self, p: ast.Module):
        ...
        
TYPE_CHECKERS: Dict[Language, TypeChecker] = {
}

