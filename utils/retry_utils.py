#!/usr/bin/env python3
"""
Robust Error Handling and Retry Utilities
Provides decorators and utilities for handling network errors, API failures, and rate limiting
"""

import time;
import random;
import logging;
import functools;
from typing import Dict, List, Optional, Any, Callable, Type, Union;
from dataclasses import dataclass;
from enum import Enum;

logger = logging.getLogger( __name__ );

class ErrorCategory( Enum ):
    """Categories of errors for different handling strategies."""
    NETWORK = "network"
    QUOTA_EXCEEDED = "quota_exceeded"
    RATE_LIMITED = "rate_limited"
    NOT_FOUND = "not_found"
    AUTHENTICATION = "authentication"
    PERMISSION_DENIED = "permission_denied"
    TEMPORARY = "temporary"
    PERMANENT = "permanent"
    UNKNOWN = "unknown"

@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    attempts: int = 3;
    base_delay: float = 1.0;
    max_delay: float = 60.0;
    exponential_base: float = 2.0;
    jitter: bool = True;
    jitter_range: float = 0.1;
    
class RateLimiter:
    """Rate limiter for API calls."""
    
    def __init__( self, calls_per_second: float = 1.0 ):
        self.calls_per_second = calls_per_second;
        self.min_interval = 1.0 / calls_per_second;
        self.last_call_time = 0.0;
        
    def wait_if_needed( self ):
        """Wait if needed to respect rate limit."""
        current_time = time.time();
        time_since_last = current_time - self.last_call_time;
        
        if time_since_last < self.min_interval:
            sleep_time = self.min_interval - time_since_last;
            logger.debug( f"Rate limiting: sleeping {sleep_time:.3f}s" );
            time.sleep( sleep_time );
            
        self.last_call_time = time.time();

def categorize_error( exception: Exception ) -> ErrorCategory:
    """Categorize an exception for appropriate handling."""
    error_msg = str( exception ).lower();
    error_type = type( exception ).__name__.lower();
    
    # Network related errors
    if any( term in error_msg for term in [ 'connection', 'timeout', 'network', 'dns' ] ):
        return ErrorCategory.NETWORK;
    if any( term in error_type for term in [ 'connectionerror', 'timeout', 'httperror' ] ):
        return ErrorCategory.NETWORK;
        
    # Quota and rate limiting
    if any( term in error_msg for term in [ 'quota', 'limit exceeded', 'too many requests' ] ):
        return ErrorCategory.QUOTA_EXCEEDED;
    if 'rate limit' in error_msg or '429' in error_msg:
        return ErrorCategory.RATE_LIMITED;
        
    # Authentication and permissions
    if any( term in error_msg for term in [ 'unauthorized', 'authentication', '401' ] ):
        return ErrorCategory.AUTHENTICATION;
    if any( term in error_msg for term in [ 'permission denied', 'forbidden', '403' ] ):
        return ErrorCategory.PERMISSION_DENIED;
    if 'request_denied' in error_msg:
        return ErrorCategory.PERMISSION_DENIED;
        
    # Not found errors
    if any( term in error_msg for term in [ 'not found', '404', 'no results' ] ):
        return ErrorCategory.NOT_FOUND;
        
    # Temporary vs permanent
    if any( term in error_msg for term in [ 'temporary', 'service unavailable', '503', '502', '500' ] ):
        return ErrorCategory.TEMPORARY;
        
    # Default to unknown
    return ErrorCategory.UNKNOWN;

def should_retry( exception: Exception, attempt: int, max_attempts: int ) -> bool:
    """Determine if an operation should be retried based on the exception."""
    if attempt >= max_attempts:
        return False;
        
    category = categorize_error( exception );
    
    # Always retry these categories
    retry_categories = {
        ErrorCategory.NETWORK,
        ErrorCategory.RATE_LIMITED,
        ErrorCategory.TEMPORARY,
        ErrorCategory.QUOTA_EXCEEDED
    };
    
    # Never retry these categories
    no_retry_categories = {
        ErrorCategory.AUTHENTICATION,
        ErrorCategory.PERMISSION_DENIED,
        ErrorCategory.NOT_FOUND,
        ErrorCategory.PERMANENT
    };
    
    if category in retry_categories:
        return True;
    elif category in no_retry_categories:
        return False;
    else:
        # For unknown errors, retry but with fewer attempts
        return attempt < min( max_attempts, 2 );

def calculate_delay( attempt: int, config: RetryConfig, exception: Exception = None ) -> float:
    """Calculate delay before next retry attempt."""
    category = categorize_error( exception ) if exception else ErrorCategory.UNKNOWN;
    
    # Base delay with exponential backoff
    delay = config.base_delay * ( config.exponential_base ** ( attempt - 1 ) );
    
    # Category-specific adjustments
    if category == ErrorCategory.RATE_LIMITED:
        delay = max( delay, 30.0 );  # Minimum 30s for rate limit
    elif category == ErrorCategory.QUOTA_EXCEEDED:
        delay = max( delay, 60.0 );  # Minimum 1min for quota
    elif category == ErrorCategory.NETWORK:
        delay = min( delay, 10.0 );  # Cap network delays
        
    # Apply maximum delay cap
    delay = min( delay, config.max_delay );
    
    # Add jitter if enabled
    if config.jitter:
        jitter_amount = delay * config.jitter_range;
        jitter = random.uniform( -jitter_amount, jitter_amount );
        delay += jitter;
        
    return max( delay, 0.1 );  # Minimum 100ms delay

def retry( attempts: int = 3, 
          base_delay: float = 1.0,
          max_delay: float = 60.0, 
          exponential_base: float = 2.0,
          jitter: bool = True,
          jitter_range: float = 0.1,
          exceptions: tuple = ( Exception, ) ):
    """
    Decorator that retries a function call with exponential backoff and jitter.
    
    Args:
        attempts: Maximum number of attempts (default: 3)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 60.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter (default: True)
        jitter_range: Range for jitter as fraction of delay (default: 0.1)
        exceptions: Tuple of exceptions to catch and retry (default: Exception)
    """
    def decorator( func: Callable ) -> Callable:
        @functools.wraps( func )
        def wrapper( *args, **kwargs ):
            config = RetryConfig(
                attempts=attempts,
                base_delay=base_delay,
                max_delay=max_delay,
                exponential_base=exponential_base,
                jitter=jitter,
                jitter_range=jitter_range
            );
            
            last_exception = None;
            
            for attempt in range( 1, attempts + 1 ):
                try:
                    result = func( *args, **kwargs );
                    if attempt > 1:
                        logger.info( f"{func.__name__} succeeded on attempt {attempt}" );
                    return result;
                    
                except exceptions as e:
                    last_exception = e;
                    category = categorize_error( e );
                    
                    logger.warning( 
                        f"{func.__name__} failed on attempt {attempt}/{attempts}: "
                        f"{type( e ).__name__}: {e} (category: {category.value})"
                    );
                    
                    if not should_retry( e, attempt, attempts ):
                        logger.error( f"Not retrying {func.__name__} due to error category: {category.value}" );
                        break;
                        
                    if attempt < attempts:
                        delay = calculate_delay( attempt, config, e );
                        logger.info( f"Retrying {func.__name__} in {delay:.2f} seconds..." );
                        time.sleep( delay );
                        
            # All retries exhausted
            logger.error( f"{func.__name__} failed after {attempts} attempts" );
            raise last_exception;
            
        return wrapper;
    return decorator;

def rate_limited( per_second: float = 1.0 ):
    """
    Decorator that rate limits function calls.
    
    Args:
        per_second: Maximum calls per second (default: 1.0)
    """
    limiter = RateLimiter( per_second );
    
    def decorator( func: Callable ) -> Callable:
        @functools.wraps( func )
        def wrapper( *args, **kwargs ):
            limiter.wait_if_needed();
            return func( *args, **kwargs );
        return wrapper;
    return decorator;

class ErrorHandler:
    """Centralized error handling with logging and metrics."""
    
    def __init__( self, service_name: str = "unknown" ):
        self.service_name = service_name;
        self.error_counts = {};
        
    def handle_error( self, exception: Exception, context: str = "" ) -> ErrorCategory:
        """Handle an error and return its category."""
        category = categorize_error( exception );
        
        # Count errors by category
        if category not in self.error_counts:
            self.error_counts[ category ] = 0;
        self.error_counts[ category ] += 1;
        
        # Log error with context
        context_msg = f" in {context}" if context else "";
        logger.error( 
            f"{self.service_name} error{context_msg}: "
            f"{type( exception ).__name__}: {exception} "
            f"(category: {category.value})"
        );
        
        return category;
        
    def get_error_summary( self ) -> Dict[ str, int ]:
        """Get summary of error counts by category."""
        return { cat.value: count for cat, count in self.error_counts.items() };

# Combined decorator for common use case
def robust_api_call( attempts: int = 5, 
                    rate_per_second: float = 8.0,
                    base_delay: float = 1.0,
                    max_delay: float = 300.0,
                    jitter: bool = True ):
    """
    Combined decorator for robust API calls with retry and rate limiting.
    
    Args:
        attempts: Maximum retry attempts (default: 5)
        rate_per_second: Rate limit in calls per second (default: 8.0)
        base_delay: Base delay for retries in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 300.0 = 5min)
        jitter: Whether to add jitter (default: True)
    """
    def decorator( func: Callable ) -> Callable:
        # Apply rate limiting first, then retry
        rate_limited_func = rate_limited( rate_per_second )( func );
        retry_func = retry( 
            attempts=attempts,
            base_delay=base_delay,
            max_delay=max_delay,
            jitter=jitter
        )( rate_limited_func );
        
        return retry_func;
    return decorator;

# Context manager for error handling
class error_context:
    """Context manager for handling errors in a block of code."""
    
    def __init__( self, handler: ErrorHandler, context: str = "", 
                 reraise: bool = True, default_return = None ):
        self.handler = handler;
        self.context = context;
        self.reraise = reraise;
        self.default_return = default_return;
        self.category = None;
        
    def __enter__( self ):
        return self;
        
    def __exit__( self, exc_type, exc_val, exc_tb ):
        if exc_type is not None:
            self.category = self.handler.handle_error( exc_val, self.context );
            if not self.reraise:
                return True;  # Suppress exception
        return False;  # Let exception propagate

# Example usage and testing
if __name__ == "__main__":
    logging.basicConfig( level=logging.INFO );
    
    # Test retry decorator
    @retry( attempts=3, base_delay=0.5, jitter=True )
    def flaky_function( success_rate: float = 0.3 ):
        if random.random() > success_rate:
            raise ConnectionError( "Network timeout" );
        return "Success!";
        
    # Test rate limiting
    @rate_limited( per_second=2.0 )
    def api_call( data: str ):
        print( f"API call with: {data}" );
        return f"Response for {data}";
        
    # Test combined decorator
    @robust_api_call( attempts=3, rate_per_second=1.0 )
    def google_places_call( query: str ):
        # Simulate API call
        if random.random() > 0.7:
            raise Exception( "REQUEST_DENIED" );
        return f"Places result for {query}";
        
    # Test error handler
    handler = ErrorHandler( "test_service" );
    
    print( "Testing retry mechanism..." );
    try:
        result = flaky_function( 0.8 );
        print( f"Retry test result: {result}" );
    except Exception as e:
        print( f"Retry test failed: {e}" );
        
    print( "\nTesting rate limiting..." );
    start_time = time.time();
    for i in range( 3 ):
        api_call( f"request_{i}" );
    elapsed = time.time() - start_time;
    print( f"Rate limiting test took {elapsed:.2f}s (should be ~1s for 2 req/s)" );
    
    print( "\nTesting error categorization..." );
    test_errors = [
        ConnectionError( "Network timeout" ),
        Exception( "REQUEST_DENIED" ),
        ValueError( "Not found" ),
        RuntimeError( "Quota exceeded" )
    ];
    
    for error in test_errors:
        category = handler.handle_error( error, "test" );
        print( f"{type( error ).__name__}: {error} -> {category.value}" );
        
    print( f"\nError summary: {handler.get_error_summary()}" );
