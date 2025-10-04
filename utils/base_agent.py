"""
Base Agent Class for Marketing Intake System
"""
from abc import ABC, abstractmethod

class BaseAgent(ABC):
    def __init__(self, config):
        self.config = config

    @abstractmethod
    async def execute(self, input_data):
        pass

    @abstractmethod
    def get_dependencies(self):
        pass
