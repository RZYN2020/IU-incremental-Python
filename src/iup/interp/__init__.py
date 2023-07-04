from iup.config import Language
from typing import Dict
from iup.interp.interp import Intepreter
from iup.interp.interp_Lvar import InterpLvar

INTERPRETERS: Dict[Language, Intepreter] = {
    "Lvar": InterpLvar(),
}