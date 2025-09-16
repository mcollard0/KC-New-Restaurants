#!/usr/bin/env python3
"""
Safe Access Utilities for KC New Restaurants

Provides safe wrappers for dictionary/list access to prevent PyObject_getItem() crashes
and other common access-related segmentation faults in Python 3.13.
"""

import sys;
from typing import Any, Optional, Union, Dict, List, Callable;

# Import logging after it's available
try:
    from logging_config import get_logger;
    logger = get_logger( "safe_access" );
except ImportError:
    import logging;
    logger = logging.getLogger( "safe_access" );

def safe_get( mapping: Union[Dict, List], key: Union[str, int], default: Any = None, log_errors: bool = True ) -> Any:
    """
    Safely get item from dictionary or list, preventing PyObject_getItem() crashes.
    
    Args:
        mapping: Dictionary or list to access
        key: Key or index to retrieve
        default: Default value if key doesn't exist or access fails
        log_errors: Whether to log access errors
    
    Returns:
        Value at key/index, or default if not found/accessible
    """
    try:
        if mapping is None:
            if log_errors:
                logger.warning( f"safe_get: mapping is None for key '{key}'" );
            return default;
        
        if isinstance( mapping, dict ):
            return mapping.get( key, default );
        elif isinstance( mapping, list ):
            try:
                if isinstance( key, int ) and 0 <= key < len( mapping ):
                    return mapping[key];
                else:
                    if log_errors:
                        logger.warning( f"safe_get: list index {key} out of range for list of length {len(mapping)}" );
                    return default;
            except ( IndexError, TypeError ) as e:
                if log_errors:
                    logger.error( f"safe_get: list access error for key {key}: {e}" );
                return default;
        else:
            # Try generic item access for other types
            try:
                return mapping[key];
            except ( KeyError, IndexError, TypeError, AttributeError ) as e:
                if log_errors:
                    logger.error( f"safe_get: generic access error for key {key} on type {type(mapping)}: {e}" );
                return default;
            
    except Exception as e:
        if log_errors:
            logger.error( f"safe_get: unexpected error accessing key '{key}': {e}" );
        return default;

def safe_get_nested( mapping: Union[Dict, List], key_path: List[Union[str, int]], default: Any = None, log_errors: bool = True ) -> Any:
    """
    Safely get nested item from dictionary/list structure.
    
    Args:
        mapping: Root dictionary or list
        key_path: List of keys/indices to traverse (e.g., ['level1', 'level2', 0])
        default: Default value if any access fails
        log_errors: Whether to log access errors
    
    Returns:
        Value at nested path, or default if not accessible
    """
    try:
        current = mapping;
        path_str = ".".join( str( k ) for k in key_path );
        
        for i, key in enumerate( key_path ):
            current = safe_get( current, key, None, log_errors=False );
            if current is None:
                if log_errors:
                    partial_path = ".".join( str( k ) for k in key_path[:i+1] );
                    logger.warning( f"safe_get_nested: path '{partial_path}' not found in nested structure" );
                return default;
        
        return current;
        
    except Exception as e:
        if log_errors:
            path_str = ".".join( str( k ) for k in key_path );
            logger.error( f"safe_get_nested: unexpected error accessing path '{path_str}': {e}" );
        return default;

def safe_list_access( lst: Optional[List], index: int, default: Any = None, log_errors: bool = True ) -> Any:
    """
    Safely access list item by index with bounds checking.
    
    Args:
        lst: List to access (can be None)
        index: Index to retrieve
        default: Default value if access fails
        log_errors: Whether to log access errors
    
    Returns:
        Value at index, or default if not accessible
    """
    try:
        if lst is None:
            if log_errors:
                logger.warning( f"safe_list_access: list is None for index {index}" );
            return default;
            
        if not isinstance( lst, list ):
            if log_errors:
                logger.warning( f"safe_list_access: object is not a list (type: {type(lst)}) for index {index}" );
            return default;
        
        if 0 <= index < len( lst ):
            return lst[index];
        else:
            if log_errors:
                logger.warning( f"safe_list_access: index {index} out of range for list of length {len(lst)}" );
            return default;
            
    except Exception as e:
        if log_errors:
            logger.error( f"safe_list_access: unexpected error accessing index {index}: {e}" );
        return default;

def safe_dict_access( dct: Optional[Dict], key: str, default: Any = None, log_errors: bool = True ) -> Any:
    """
    Safely access dictionary value with proper error handling.
    
    Args:
        dct: Dictionary to access (can be None)
        key: Key to retrieve
        default: Default value if access fails
        log_errors: Whether to log access errors
    
    Returns:
        Value at key, or default if not accessible
    """
    try:
        if dct is None:
            if log_errors:
                logger.warning( f"safe_dict_access: dictionary is None for key '{key}'" );
            return default;
            
        if not isinstance( dct, dict ):
            if log_errors:
                logger.warning( f"safe_dict_access: object is not a dict (type: {type(dct)}) for key '{key}'" );
            return default;
        
        return dct.get( key, default );
            
    except Exception as e:
        if log_errors:
            logger.error( f"safe_dict_access: unexpected error accessing key '{key}': {e}" );
        return default;

def safe_csv_row_access( row: Optional[List], expected_columns: List[str], log_errors: bool = True ) -> Dict[str, Optional[str]]:
    """
    Safely parse CSV row into dictionary with expected column names.
    
    Args:
        row: CSV row as list of strings
        expected_columns: List of expected column names
        log_errors: Whether to log access errors
    
    Returns:
        Dictionary mapping column names to values (or None if not available)
    """
    result = {};
    
    try:
        if row is None:
            if log_errors:
                logger.warning( "safe_csv_row_access: row is None" );
            return { col: None for col in expected_columns };
        
        if not isinstance( row, list ):
            if log_errors:
                logger.warning( f"safe_csv_row_access: row is not a list (type: {type(row)})" );
            return { col: None for col in expected_columns };
        
        for i, column_name in enumerate( expected_columns ):
            value = safe_list_access( row, i, None, log_errors=False );
            # Clean up the value
            if value is not None:
                try:
                    value = str( value ).strip().strip( '"' );
                    if value == '':
                        value = None;
                except Exception as e:
                    if log_errors:
                        logger.warning( f"safe_csv_row_access: error cleaning value for column '{column_name}': {e}" );
                    value = None;
            result[column_name] = value;
        
        return result;
        
    except Exception as e:
        if log_errors:
            logger.error( f"safe_csv_row_access: unexpected error parsing CSV row: {e}" );
        return { col: None for col in expected_columns };

def safe_call_with_fallback( primary_func: Callable, fallback_func: Callable, *args, log_errors: bool = True, **kwargs ) -> Any:
    """
    Call primary function, falling back to fallback_func if primary fails.
    
    Args:
        primary_func: Primary function to call
        fallback_func: Fallback function if primary fails
        *args: Arguments to pass to both functions
        log_errors: Whether to log errors from primary function
        **kwargs: Keyword arguments to pass to both functions
    
    Returns:
        Result from primary_func, or fallback_func if primary fails
    """
    try:
        return primary_func( *args, **kwargs );
    except Exception as e:
        if log_errors:
            primary_name = getattr( primary_func, '__name__', str( primary_func ) );
            fallback_name = getattr( fallback_func, '__name__', str( fallback_func ) );
            logger.warning( f"safe_call_with_fallback: {primary_name} failed ({e}), using {fallback_name}" );
        try:
            return fallback_func( *args, **kwargs );
        except Exception as fallback_error:
            if log_errors:
                logger.error( f"safe_call_with_fallback: both primary and fallback functions failed: {fallback_error}" );
            raise;

def safe_string_operations( value: Any, operations: List[str], default: str = "", log_errors: bool = True ) -> str:
    """
    Safely apply string operations (strip, lower, etc.) to a value.
    
    Args:
        value: Value to process
        operations: List of string method names to apply (e.g., ['strip', 'lower'])
        default: Default value if processing fails
        log_errors: Whether to log errors
    
    Returns:
        Processed string or default if processing fails
    """
    try:
        if value is None:
            return default;
        
        result = str( value );
        
        for operation in operations:
            try:
                if hasattr( result, operation ):
                    method = getattr( result, operation );
                    if callable( method ):
                        result = method();
                    else:
                        if log_errors:
                            logger.warning( f"safe_string_operations: {operation} is not callable" );
                else:
                    if log_errors:
                        logger.warning( f"safe_string_operations: string has no method '{operation}'" );
                        
            except Exception as e:
                if log_errors:
                    logger.warning( f"safe_string_operations: error applying operation '{operation}': {e}" );
        
        return result;
        
    except Exception as e:
        if log_errors:
            logger.error( f"safe_string_operations: unexpected error processing value: {e}" );
        return default;

def safe_type_check( value: Any, expected_type: type, default: Any = None, log_errors: bool = True ) -> Any:
    """
    Safely check if value is of expected type, return default if not.
    
    Args:
        value: Value to check
        expected_type: Expected type
        default: Default value if type check fails
        log_errors: Whether to log type mismatches
    
    Returns:
        Original value if type matches, default otherwise
    """
    try:
        if isinstance( value, expected_type ):
            return value;
        else:
            if log_errors:
                logger.debug( f"safe_type_check: expected {expected_type.__name__}, got {type(value).__name__}" );
            return default;
    except Exception as e:
        if log_errors:
            logger.error( f"safe_type_check: error during type checking: {e}" );
        return default;

if __name__ == "__main__":
    # Test the safe access utilities
    print( "Testing safe access utilities..." );
    
    # Test safe_get with dictionary
    test_dict = { "key1": "value1", "key2": { "nested": "nested_value" } };
    print( f"safe_get dict: {safe_get( test_dict, 'key1' )}" );
    print( f"safe_get dict missing: {safe_get( test_dict, 'missing', 'default' )}" );
    
    # Test safe_get with list
    test_list = [ "item0", "item1", "item2" ];
    print( f"safe_get list: {safe_get( test_list, 1 )}" );
    print( f"safe_get list out of bounds: {safe_get( test_list, 10, 'default' )}" );
    
    # Test safe_csv_row_access
    csv_row = [ "Business Name", "DBA Name", "Address", "Type", "2025" ];
    columns = [ "business_name", "dba_name", "address", "business_type", "valid_license_for" ];
    parsed = safe_csv_row_access( csv_row, columns );
    print( f"CSV parsing: {parsed}" );
    
    print( "All tests completed." );