#!/usr/bin/env python3
"""
Enhanced Logging Configuration for KC New Restaurants

Provides centralized logging setup with:
- Rotating file handlers to prevent log bloat
- Enhanced crash diagnostics and context logging
- Support for structured logging with request/CSV context
- Python faulthandler integration for segfault debugging
"""

import logging;
import logging.handlers;
import os;
import sys;
import traceback;
import faulthandler;
from datetime import datetime;
from typing import Optional, Dict, Any;

# Enable Python faulthandler for SIGSEGV debugging
faulthandler.enable();

class ContextualFormatter( logging.Formatter ):
    """Enhanced formatter that includes contextual information like CSV row number, request details, etc."""
    
    def __init__( self, fmt=None, datefmt=None ):
        super().__init__( fmt, datefmt );
        self.context = {};
    
    def set_context( self, **kwargs ):
        """Set contextual information for logging"""
        self.context.update( kwargs );
    
    def clear_context( self ):
        """Clear contextual information"""
        self.context.clear();
    
    def format( self, record ):
        """Format log record with contextual information"""
        if self.context:
            context_str = " | ".join( f"{k}={v}" for k, v in self.context.items() );
            record.msg = f"[{context_str}] {record.msg}";
        return super().format( record );

class CrashAwareLogger:
    """Logger wrapper that provides crash diagnostics and structured logging"""
    
    def __init__( self, name: str, log_file: str = "kc_new_restaurants_enhanced.log", max_bytes: int = 10_485_760, backup_count: int = 10 ):
        self.name = name;
        self.log_file = log_file;
        self.max_bytes = max_bytes;
        self.backup_count = backup_count;
        self.context = {};
        
        # Set up the logger
        self.logger = logging.getLogger( name );
        self.logger.setLevel( logging.DEBUG );
        
        # Clear any existing handlers
        self.logger.handlers.clear();
        
        # Create rotating file handler
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding='utf-8'
            );
            
            # Create console handler
            console_handler = logging.StreamHandler( sys.stdout );
            
            # Create enhanced formatter
            self.formatter = ContextualFormatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            );
            
            file_handler.setFormatter( self.formatter );
            console_handler.setFormatter( self.formatter );
            
            self.logger.addHandler( file_handler );
            self.logger.addHandler( console_handler );
            
            # Prevent duplicate logging
            self.logger.propagate = False;
            
            self.logger.info( f"Enhanced logging initialized - File: {log_file}, Max: {max_bytes//1024//1024}MB, Backups: {backup_count}" );
            
        except Exception as e:
            # Fallback to basic logging if file handler fails
            basic_handler = logging.StreamHandler( sys.stdout );
            basic_handler.setFormatter( logging.Formatter( '%(asctime)s - %(levelname)s - %(message)s' ) );
            self.logger.addHandler( basic_handler );
            self.logger.error( f"Failed to set up rotating file handler: {e}" );
    
    def set_context( self, **kwargs ):
        """Set contextual information for all future log messages"""
        self.context.update( kwargs );
        self.formatter.set_context( **self.context );
        self.debug( f"Context updated: {kwargs}" );
    
    def clear_context( self ):
        """Clear contextual information"""
        self.context.clear();
        self.formatter.clear_context();
        self.debug( "Context cleared" );
    
    def log_csv_context( self, row_number: int, row_data: Optional[list] = None ):
        """Log CSV processing context"""
        context = {"csv_row": row_number};
        if row_data and len( row_data ) > 0:
            # Log first few fields for context, but safely
            try:
                context["business_name"] = str( row_data[0] )[:50] if row_data[0] else "None";
                if len( row_data ) > 2:
                    context["address"] = str( row_data[2] )[:50] if row_data[2] else "None";
            except ( IndexError, TypeError ) as e:
                context["row_parse_error"] = str( e );
        self.set_context( **context );
    
    def log_request_context( self, url: str, method: str = "GET", payload_size: Optional[int] = None ):
        """Log HTTP request context"""
        context = {"url": url, "method": method};
        if payload_size is not None:
            context["payload_size"] = f"{payload_size}B";
        self.set_context( **context );
    
    def log_crash( self, exc_info: tuple = None, additional_context: Dict[str, Any] = None ):
        """Enhanced crash logging with full context and stack trace"""
        self.error( "="*80 );
        self.error( "🚨 CRASH DETECTED 🚨" );
        self.error( f"Timestamp: {datetime.now().isoformat()}" );
        self.error( f"Python Version: {sys.version}" );
        
        if additional_context:
            for key, value in additional_context.items():
                self.error( f"{key}: {value}" );
        
        if exc_info or sys.exc_info()[0] is not None:
            exc_info = exc_info or sys.exc_info();
            self.error( f"Exception Type: {exc_info[0].__name__ if exc_info[0] else 'Unknown'}" );
            self.error( f"Exception Message: {str( exc_info[1] ) if exc_info[1] else 'No message'}" );
            self.error( "Full Traceback:" );
            if exc_info[2]:
                for line in traceback.format_tb( exc_info[2] ):
                    self.error( f"  {line.rstrip()}" );
        
        # Log current context
        if self.context:
            self.error( "Current Context:" );
            for key, value in self.context.items():
                self.error( f"  {key}: {value}" );
        
        self.error( "="*80 );
    
    def safe_call( self, func, *args, **kwargs ):
        """Execute function with crash logging"""
        try:
            return func( *args, **kwargs );
        except Exception as e:
            self.log_crash( additional_context={
                "function": func.__name__ if hasattr( func, '__name__' ) else str( func ),
                "args": str( args )[:200],
                "kwargs": str( kwargs )[:200]
            } );
            raise;
    
    # Standard logging methods
    def debug( self, msg, *args, **kwargs ):
        self.logger.debug( msg, *args, **kwargs );
    
    def info( self, msg, *args, **kwargs ):
        self.logger.info( msg, *args, **kwargs );
    
    def warning( self, msg, *args, **kwargs ):
        self.logger.warning( msg, *args, **kwargs );
    
    def error( self, msg, *args, **kwargs ):
        self.logger.error( msg, *args, **kwargs );
    
    def critical( self, msg, *args, **kwargs ):
        self.logger.critical( msg, *args, **kwargs );

# Global logger instance
_global_logger = None;

def get_logger( name: str = "kc_restaurants" ) -> CrashAwareLogger:
    """Get or create the global enhanced logger"""
    global _global_logger;
    if _global_logger is None:
        _global_logger = CrashAwareLogger( name );
    return _global_logger;

def setup_crash_handlers():
    """Set up system-level crash handlers"""
    import signal;
    
    def signal_handler( signum, frame ):
        logger = get_logger();
        logger.critical( f"Received signal {signum}" );
        if signum == signal.SIGSEGV:
            logger.critical( "SIGSEGV (Segmentation Fault) detected!" );
        elif signum == signal.SIGBUS:
            logger.critical( "SIGBUS (Bus Error) detected!" );
        elif signum == signal.SIGFPE:
            logger.critical( "SIGFPE (Floating Point Exception) detected!" );
        
        logger.log_crash( additional_context={
            "signal": signum,
            "signal_name": signal.Signals( signum ).name if hasattr( signal, 'Signals' ) else f"Signal_{signum}",
            "frame": f"{frame.f_code.co_filename}:{frame.f_lineno}" if frame else "No frame"
        } );
        
        # Try to exit gracefully
        sys.exit( 128 + signum );
    
    # Register signal handlers for common crash signals
    try:
        signal.signal( signal.SIGSEGV, signal_handler );
        signal.signal( signal.SIGBUS, signal_handler );
        signal.signal( signal.SIGFPE, signal_handler );
        get_logger().info( "Crash signal handlers registered" );
    except Exception as e:
        get_logger().warning( f"Could not register signal handlers: {e}" );

# Set up crash handlers when module is imported
setup_crash_handlers();

if __name__ == "__main__":
    # Test the logging system
    logger = get_logger( "test" );
    logger.info( "Testing enhanced logging system" );
    logger.set_context( test_mode=True, version="1.0" );
    logger.info( "Context test message" );
    logger.clear_context();
    logger.info( "Context cleared test message" );