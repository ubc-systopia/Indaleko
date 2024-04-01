from abc import ABC, abstractmethod


class IReader(ABC):
    @abstractmethod
    def run(self):
        raise NotImplementedError("Implementation needed")


class IOperator(ABC):
    @abstractmethod
    def execute(self, input, **args):
        raise NotImplementedError("Implementation needed")
