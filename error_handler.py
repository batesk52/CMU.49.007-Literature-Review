"""
Enhanced Error Handling and Logging Module

This module provides centralized error handling, logging configuration,
and monitoring capabilities for the knowledge base system.
"""

import os
import sys
import logging
import traceback
import functools
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Union
import json

# Load environment variables from .env file if available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class KnowledgeBaseLogger:
    """
    Centralized logging configuration for the knowledge base system.
    """
    
    def __init__(self, 
                 log_level: str = "INFO",
                 log_dir: str = "logs",
                 enable_file_logging: bool = True,
                 enable_error_tracking: bool = True):
        """
        Initialize the logging system.
        
        Args:
            log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_dir (str): Directory for log files
            enable_file_logging (bool): Whether to write logs to files
            enable_error_tracking (bool): Whether to track errors separately
        """
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)
        self.log_dir = Path(log_dir)
        self.enable_file_logging = enable_file_logging
        self.enable_error_tracking = enable_error_tracking
        
        # Error tracking
        self.error_count = 0
        self.errors = []
        
        # Setup logging
        self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging configuration."""
        # Create logs directory if needed
        if self.enable_file_logging:
            self.log_dir.mkdir(exist_ok=True)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove existing handlers to avoid duplicates
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
        
        if self.enable_file_logging:
            # Main log file
            main_log_file = self.log_dir / "knowledge_base.log"
            file_handler = logging.FileHandler(main_log_file)
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # Error-only log file
            if self.enable_error_tracking:
                error_log_file = self.log_dir / "errors.log"
                error_handler = logging.FileHandler(error_log_file)
                error_handler.setLevel(logging.ERROR)
                error_handler.setFormatter(formatter)
                root_logger.addHandler(error_handler)
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """
        Track an error with additional context.
        
        Args:
            error (Exception): The error that occurred
            context (Dict[str, Any], optional): Additional context about the error
        """
        if not self.enable_error_tracking:
            return
        
        self.error_count += 1
        
        error_info = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        
        self.errors.append(error_info)
        
        # Log the error
        logger = logging.getLogger(__name__)
        logger.error(f"Error tracked: {error_info['error_type']}: {error_info['error_message']}")
        
        # Keep only last 100 errors to prevent memory issues
        if len(self.errors) > 100:
            self.errors = self.errors[-100:]
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get a summary of tracked errors.
        
        Returns:
            Dict[str, Any]: Error summary statistics
        """
        if not self.enable_error_tracking:
            return {"error_tracking": "disabled"}
        
        error_types = {}
        for error in self.errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1
        
        return {
            "total_errors": self.error_count,
            "recent_errors": len(self.errors),
            "error_types": error_types,
            "last_error": self.errors[-1] if self.errors else None
        }
    
    def save_error_report(self, filename: Optional[str] = None) -> str:
        """
        Save a detailed error report to a file.
        
        Args:
            filename (str, optional): Custom filename for the report
            
        Returns:
            str: Path to the saved report
        """
        if not self.enable_error_tracking:
            return ""
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_report_{timestamp}.json"
        
        report_path = self.log_dir / filename
        
        report = {
            "generated_at": datetime.now().isoformat(),
            "summary": self.get_error_summary(),
            "detailed_errors": self.errors
        }
        
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        return str(report_path)


# Global logger instance
_global_logger = None


def setup_logging(log_level: str = "INFO", 
                 log_dir: str = "logs",
                 enable_file_logging: bool = True,
                 enable_error_tracking: bool = True) -> KnowledgeBaseLogger:
    """
    Setup global logging for the knowledge base system.
    
    Args:
        log_level (str): Logging level
        log_dir (str): Directory for log files
        enable_file_logging (bool): Whether to write logs to files
        enable_error_tracking (bool): Whether to track errors separately
        
    Returns:
        KnowledgeBaseLogger: The configured logger instance
    """
    global _global_logger
    _global_logger = KnowledgeBaseLogger(
        log_level=log_level,
        log_dir=log_dir,
        enable_file_logging=enable_file_logging,
        enable_error_tracking=enable_error_tracking
    )
    return _global_logger


def get_logger() -> Optional[KnowledgeBaseLogger]:
    """Get the global logger instance."""
    return _global_logger


def error_handler(func: Callable) -> Callable:
    """
    Decorator for comprehensive error handling with logging and tracking.
    
    Args:
        func (Callable): Function to wrap with error handling
        
    Returns:
        Callable: Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = logging.getLogger(func.__module__)
        
        try:
            result = func(*args, **kwargs)
            return result
            
        except KeyboardInterrupt:
            logger.info(f"Function {func.__name__} interrupted by user")
            raise
            
        except Exception as e:
            # Prepare error context
            context = {
                "function": func.__name__,
                "module": func.__module__,
                "args_count": len(args),
                "kwargs_keys": list(kwargs.keys()) if kwargs else []
            }
            
            # Track error if global logger is available
            if _global_logger:
                _global_logger.track_error(e, context)
            
            # Log the error
            logger.error(f"Error in {func.__name__}: {e}")
            logger.debug(f"Full traceback: {traceback.format_exc()}")
            
            # Re-raise the exception
            raise
    
    return wrapper


def safe_execute(func: Callable, 
                default_return: Any = None,
                log_errors: bool = True,
                context: Dict[str, Any] = None) -> Any:
    """
    Safely execute a function with error handling.
    
    Args:
        func (Callable): Function to execute
        default_return (Any): Value to return if function fails
        log_errors (bool): Whether to log errors
        context (Dict[str, Any]): Additional context for error tracking
        
    Returns:
        Any: Function result or default_return if function fails
    """
    logger = logging.getLogger(__name__)
    
    try:
        return func()
    except Exception as e:
        if log_errors:
            error_context = {
                "function": getattr(func, '__name__', 'unknown'),
                "default_return": str(default_return),
                **(context or {})
            }
            
            if _global_logger:
                _global_logger.track_error(e, error_context)
            
            logger.error(f"Safe execution failed: {e}")
        
        return default_return


def validate_environment() -> Dict[str, Any]:
    """
    Validate the environment configuration for the knowledge base system.
    
    Returns:
        Dict[str, Any]: Validation results
    """
    logger = logging.getLogger(__name__)
    
    validation_results = {
        "valid": True,
        "warnings": [],
        "errors": [],
        "environment_variables": {},
        "directories": {},
        "dependencies": {}
    }
    
    # Check required environment variables
    required_env_vars = ["OPENAI_API_KEY"]
    optional_env_vars = ["NOTION_TOKEN", "NOTION_DATABASE_ID", "ZOTERO_API_KEY"]
    
    for var in required_env_vars:
        value = os.getenv(var)
        validation_results["environment_variables"][var] = {
            "present": value is not None,
            "required": True
        }
        if not value:
            validation_results["errors"].append(f"Required environment variable missing: {var}")
            validation_results["valid"] = False
    
    for var in optional_env_vars:
        value = os.getenv(var)
        validation_results["environment_variables"][var] = {
            "present": value is not None,
            "required": False
        }
        if not value:
            validation_results["warnings"].append(f"Optional environment variable missing: {var}")
    
    # Check directories
    important_dirs = ["data", "logs"]
    for dir_name in important_dirs:
        dir_path = Path(dir_name)
        validation_results["directories"][dir_name] = {
            "exists": dir_path.exists(),
            "writable": dir_path.exists() and os.access(dir_path, os.W_OK)
        }
        
        if not dir_path.exists():
            validation_results["warnings"].append(f"Directory does not exist: {dir_name}")
    
    # Check Python dependencies
    required_packages = ["requests", "numpy", "pathlib"]
    for package in required_packages:
        try:
            __import__(package)
            validation_results["dependencies"][package] = {"available": True}
        except ImportError:
            validation_results["dependencies"][package] = {"available": False}
            validation_results["errors"].append(f"Required package missing: {package}")
            validation_results["valid"] = False
    
    # Log validation results
    if validation_results["valid"]:
        logger.info("Environment validation passed")
    else:
        logger.error("Environment validation failed")
    
    for warning in validation_results["warnings"]:
        logger.warning(warning)
    
    for error in validation_results["errors"]:
        logger.error(error)
    
    return validation_results


def main():
    """
    Command-line interface for error handling and logging utilities.
    """
    import argparse
    
    parser = argparse.ArgumentParser(description="Knowledge Base Error Handling and Logging Utilities")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Setup logging command
    setup_parser = subparsers.add_parser("setup-logging", help="Setup logging configuration")
    setup_parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                             help="Logging level")
    setup_parser.add_argument("--log-dir", default="logs", help="Log directory")
    setup_parser.add_argument("--no-file-logging", action="store_true",
                             help="Disable file logging")
    setup_parser.add_argument("--no-error-tracking", action="store_true",
                             help="Disable error tracking")
    
    # Validate environment command
    validate_parser = subparsers.add_parser("validate", help="Validate environment configuration")
    
    # Error report command
    report_parser = subparsers.add_parser("error-report", help="Generate error report")
    report_parser.add_argument("--output", help="Output filename for error report")
    
    args = parser.parse_args()
    
    if args.command == "setup-logging":
        logger_instance = setup_logging(
            log_level=args.log_level,
            log_dir=args.log_dir,
            enable_file_logging=not args.no_file_logging,
            enable_error_tracking=not args.no_error_tracking
        )
        print(f"✅ Logging setup complete")
        print(f"   Log level: {args.log_level}")
        print(f"   Log directory: {args.log_dir}")
        print(f"   File logging: {'enabled' if not args.no_file_logging else 'disabled'}")
        print(f"   Error tracking: {'enabled' if not args.no_error_tracking else 'disabled'}")
        
    elif args.command == "validate":
        results = validate_environment()
        
        print("🔍 Environment Validation Results")
        print("=" * 40)
        print(f"Overall status: {'✅ VALID' if results['valid'] else '❌ INVALID'}")
        
        if results['errors']:
            print(f"\n❌ Errors ({len(results['errors'])}):")
            for error in results['errors']:
                print(f"   • {error}")
        
        if results['warnings']:
            print(f"\n⚠️  Warnings ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"   • {warning}")
        
        print(f"\n📊 Environment Variables:")
        for var, info in results['environment_variables'].items():
            status = "✅" if info['present'] else ("❌" if info['required'] else "⚠️")
            print(f"   {status} {var}: {'present' if info['present'] else 'missing'}")
        
    elif args.command == "error-report":
        if not _global_logger:
            print("❌ No global logger available. Setup logging first.")
            return 1
        
        report_path = _global_logger.save_error_report(args.output)
        print(f"📄 Error report saved to: {report_path}")
        
        summary = _global_logger.get_error_summary()
        print(f"   Total errors tracked: {summary.get('total_errors', 0)}")
        print(f"   Recent errors: {summary.get('recent_errors', 0)}")
        
    else:
        parser.print_help()


if __name__ == "__main__":
    main()