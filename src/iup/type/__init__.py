from ..compiler import Language
from typing import Dict
from .type_check import TypeChecker
from .type_check_Lvar import TypeCheckLvar

        
TYPE_CHECKERS: Dict[str, TypeChecker] = {
    "Lvar": TypeCheckLvar(),
}

