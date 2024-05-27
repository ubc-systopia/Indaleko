from abc import ABC, abstractmethod
import typing


class IReader(ABC):
    @abstractmethod
    def run(self):
        raise NotImplementedError("Needs to be implemebted")


class IWriter(ABC):
    @abstractmethod
    def write(self, data):
        raise NotImplementedError("Needs to be implemebted")


class IOperator(ABC):
    @abstractmethod
    def execute(self, input, **args):
        raise NotImplementedError("Needs to be implemebted")
