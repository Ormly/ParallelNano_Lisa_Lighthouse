from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class Target(ABC):
    """
    Interface for a target component
    """
    @abstractmethod
    def get_data(self) -> Dict[Any, Any]:
        """
        Get the current state of the information fed into this component
        :return:
        """
        pass

    @abstractmethod
    def feed(self, data: Dict[Any, Any]):
        """
        Feed new information to this component
        :param data:
        :return:
        """
        pass


class Source(ABC):
    """
    Interface for an information source
    """
    @abstractmethod
    def get_message(self) -> Optional[Dict[Any, Any]]:
        """
        Get newly available information from this source element
        :return:
        """
        pass


class Adapter:
    """
    An adapter between a source and a target components
    """
    def __init__(self, name: str, source, target):
        self.name = name
        self.source = source
        self.target = target

    def update(self):
        """
        Get a message from the source and pass it to target
        :return:
        """
        msg = self.source.get_message()
        if msg:
            self.target.feed(msg)
