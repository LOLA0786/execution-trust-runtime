"""
core/memory package initialization.
Exports VectorMemory and ReflectionEngine for gbrain-style persistent memory + reflection.
"""
from .vector_memory import VectorMemory, memory
from .reflection import ReflectionEngine, reflection

__all__ = ["VectorMemory", "memory", "ReflectionEngine", "reflection"]
