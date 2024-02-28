from ..compiler import Language
from typing import Dict
from .type_check import TypeChecker
from .type_check_Lvar import TypeCheckLvar
from .type_check_Lif import TypeCheckLif
from .type_check_Cif import TypeCheckCif
from .type_check_Lwhile import TypeCheckLwhile

        
TYPE_CHECKERS: Dict[str, TypeChecker] = {
    "Lvar": TypeCheckLvar(),
    "Lif": TypeCheckLif(),
    "Lwhile": TypeCheckLwhile(),
}

