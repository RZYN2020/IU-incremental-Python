from iup.config import Language
from typing import Dict
from iup.type.type_check import TypeChecker
from iup.type.type_check_Lvar import TypeCheckLvar

        
TYPE_CHECKERS: Dict[Language, TypeChecker] = {
    "Lvar": TypeCheckLvar(),
}

