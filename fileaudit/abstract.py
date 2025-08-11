from abc import ABC, abstractmethod
from typing import Never


class IReader(ABC):
    @abstractmethod
    def run(self) -> Never:
        raise NotImplementedError("Needs to be implemebted")


class IWriter(ABC):
    @abstractmethod
    def write(self, arr: list) -> Never:
        raise NotImplementedError("Needs to be implemebted")


class IOperator(ABC):
    @abstractmethod
    def execute(self, input, **args) -> Never:
        raise NotImplementedError("Needs to be implemebted")
