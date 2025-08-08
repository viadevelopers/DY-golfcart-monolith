"""Shared domain kernel for DDD implementation."""

from .base_entity import Entity
from .base_value_object import ValueObject
from .domain_event import DomainEvent
from .exceptions import DomainException

__all__ = [
    "Entity",
    "ValueObject", 
    "DomainEvent",
    "DomainException"
]