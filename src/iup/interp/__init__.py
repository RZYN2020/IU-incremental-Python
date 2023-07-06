from ..compiler import Language
from typing import Dict
from .interp import Intepreter
from .interp_Lvar import InterpLvar

INTERPRETERS: Dict[Language, Intepreter] = {
    "Lvar": InterpLvar(),
}