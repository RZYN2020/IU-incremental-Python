from abc import ABC, abstractmethod
import ast

class Intepreter(ABC):
    @abstractmethod
    def interp(self, p: ast.Module):
        ...
                