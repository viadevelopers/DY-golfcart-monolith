"""Domain exceptions for DDD implementation."""


class DomainException(Exception):
    """Base exception for domain logic violations."""
    
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class InvalidValueException(DomainException):
    """Exception for invalid value object creation."""
    pass


class BusinessRuleViolation(DomainException):
    """Exception for business rule violations."""
    pass


class EntityNotFound(DomainException):
    """Exception for entity not found scenarios."""
    pass