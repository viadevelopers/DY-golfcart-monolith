"""
Transaction management decorators for clean transaction handling.
"""

from functools import wraps
from typing import Callable, Any
import logging

logger = logging.getLogger(__name__)


def transactional(func: Callable) -> Callable:
    """
    Decorator for automatic transaction management.
    
    Ensures that the decorated method runs within a transaction.
    Commits on success, rolls back on failure.
    
    Usage:
        @transactional
        async def my_method(self, ...):
            # Your transactional code here
            pass
    
    Note: The decorated class must have a 'db' attribute (SQLAlchemy session).
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        """Wrapper function that manages the transaction."""
        if not hasattr(self, 'db'):
            raise AttributeError(
                f"Class {self.__class__.__name__} must have a 'db' attribute "
                "to use @transactional decorator"
            )
        
        try:
            # Execute the wrapped function
            result = await func(self, *args, **kwargs)
            
            # Commit on success
            self.db.commit()
            logger.debug(f"Transaction committed for {func.__name__}")
            
            return result
            
        except Exception as e:
            # Rollback on any exception
            self.db.rollback()
            logger.error(
                f"Transaction rolled back for {func.__name__}: {str(e)}"
            )
            raise
    
    return wrapper


def with_savepoint(func: Callable) -> Callable:
    """
    Decorator that creates a savepoint for nested transactions.
    
    Useful for operations that might fail but shouldn't affect
    the parent transaction.
    
    Usage:
        @with_savepoint
        async def risky_operation(self, ...):
            # Code that might fail
            pass
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        """Wrapper function that manages the savepoint."""
        if not hasattr(self, 'db'):
            raise AttributeError(
                f"Class {self.__class__.__name__} must have a 'db' attribute "
                "to use @with_savepoint decorator"
            )
        
        # Create a savepoint
        savepoint = self.db.begin_nested()
        
        try:
            # Execute the wrapped function
            result = await func(self, *args, **kwargs)
            
            # Commit the savepoint
            savepoint.commit()
            logger.debug(f"Savepoint committed for {func.__name__}")
            
            return result
            
        except Exception as e:
            # Rollback to savepoint on exception
            savepoint.rollback()
            logger.warning(
                f"Rolled back to savepoint for {func.__name__}: {str(e)}"
            )
            raise
    
    return wrapper


def read_only(func: Callable) -> Callable:
    """
    Decorator for read-only operations.
    
    Ensures no commits are made and rolls back any accidental changes.
    
    Usage:
        @read_only
        async def get_data(self, ...):
            # Read-only operations
            pass
    """
    @wraps(func)
    async def wrapper(self, *args, **kwargs):
        """Wrapper function for read-only operations."""
        if not hasattr(self, 'db'):
            raise AttributeError(
                f"Class {self.__class__.__name__} must have a 'db' attribute "
                "to use @read_only decorator"
            )
        
        try:
            # Execute the wrapped function
            result = await func(self, *args, **kwargs)
            
            # Always rollback to ensure no changes are persisted
            self.db.rollback()
            
            return result
            
        except Exception:
            # Rollback on exception as well
            self.db.rollback()
            raise
    
    return wrapper


def retry_on_deadlock(max_retries: int = 3, delay: float = 0.1):
    """
    Decorator that retries operations on database deadlock.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Delay between retries in seconds
    
    Usage:
        @retry_on_deadlock(max_retries=5)
        async def concurrent_operation(self, ...):
            # Code that might encounter deadlocks
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            """Wrapper function that handles retries."""
            import asyncio
            from sqlalchemy.exc import OperationalError
            
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return await func(self, *args, **kwargs)
                    
                except OperationalError as e:
                    # Check if it's a deadlock error
                    if 'deadlock' in str(e).lower():
                        last_exception = e
                        logger.warning(
                            f"Deadlock detected in {func.__name__}, "
                            f"attempt {attempt + 1}/{max_retries}"
                        )
                        
                        if attempt < max_retries - 1:
                            # Wait before retry
                            await asyncio.sleep(delay * (attempt + 1))
                            
                            # Rollback the failed transaction
                            if hasattr(self, 'db'):
                                self.db.rollback()
                        else:
                            # Max retries reached
                            logger.error(
                                f"Max retries reached for {func.__name__}"
                            )
                            raise
                    else:
                        # Not a deadlock, re-raise immediately
                        raise
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    
    return decorator