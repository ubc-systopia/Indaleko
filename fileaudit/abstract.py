from abc import ABC, abstractmethod


class IReader(ABC):
    @abstractmethod
    def run(self):
        raise NotImplementedError("Needs to be implemebted")


class IWriter(ABC):
    @abstractmethod
    def write(self, arr: list):
        raise NotImplementedError("Needs to be implemebted")


class IOperator(ABC):
    @abstractmethod
    def execute(self, input, **args):
        raise NotImplementedError("Needs to be implemebted")
