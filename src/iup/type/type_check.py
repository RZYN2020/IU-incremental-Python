from abc import ABC, abstractmethod
import ast

class TypeChecker(ABC):
    @abstractmethod
    def type_check(self, p: ast.Module):
        ...
    