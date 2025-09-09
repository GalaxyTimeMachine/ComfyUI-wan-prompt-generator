"""
ComfyUI Wan2.2 Prompt Generation Plugin - Utility Functions
"""

import logging
import os
import json
from datetime import datetime
from functools import wraps

class Wan22Logger:
    """Wan2.2 Plugin Dedicated Logger"""
    
    def __init__(self, name="Wan22Plugin"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # Avoid adding handlers repeatedly
        if not self.logger.handlers:
            self.setup_logger()
    
    def setup_logger(self):
        """Set up the logger"""
        try:
            # Create the logs directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(current_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # Create file handler
            log_file = os.path.join(log_dir, f"wan22_plugin_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # Create console handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # Create formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # Add handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"[Wan22Logger] Failed to set up logger: {str(e)}")
    
    def info(self, message):
        """Log informational message"""
        self.logger.info(message)
    
    def error(self, message):
        """Log error message"""
        self.logger.error(message)
    
    def warning(self, message):
        """Log warning message"""
        self.logger.warning(message)
    
    def debug(self, message):
        """Log debug message"""
        self.logger.debug(message)

# Global logger instance
logger = Wan22Logger()

def log_function_call(func):
    """Decorator: Log function calls"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        class_name = args[0].__class__.__name__ if args else "Unknown"
        
        logger.info(f"[{class_name}] Starting execution of {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"[{class_name}] {func_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"[{class_name}] {func_name} failed to execute: {str(e)}")
            raise
    
    return wrapper

def safe_json_load(file_path, default_value=None):
    """Safely load a JSON file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON file not found: {file_path}")
        return default_value
    except json.JSONDecodeError as e:
        logger.error(f"JSON file format error: {file_path}, Error: {str(e)}")
        return default_value
    except Exception as e:
        logger.error(f"Failed to load JSON file: {file_path}, Error: {str(e)}")
        return default_value

def validate_api_key(api_key, model_type="openai"):
    """Validate API key format"""
    if not api_key or not isinstance(api_key, str):
        return False, "API key cannot be empty"
    
    api_key = api_key.strip()
    
    if model_type.lower() == "openai":
        if not api_key.startswith("sk-"):
            return False, "OpenAI API key format is incorrect, it should start with 'sk-'"
        if len(api_key) < 20:
            return False, "OpenAI API key is too short"
    elif model_type.lower() == "claude":
        if not api_key.startswith("sk-ant-"):
            return False, "Claude API key format is incorrect, it should start with 'sk-ant-'"
        if len(api_key) < 30:
            return False, "Claude API key is too short"
    
    return True, "API key format is correct"

def handle_api_error(error, api_type="LLM"):
    """Handle common API errors"""
    error_msg = str(error)
    
    # Handle common error types
    if "401" in error_msg or "Unauthorized" in error_msg:
        return f"{api_type} API key is invalid or has expired"
    elif "429" in error_msg or "rate limit" in error_msg.lower():
        return f"{api_type} API request rate limit exceeded, please try again later"
    elif "timeout" in error_msg.lower():
        return f"{api_type} API request timed out, please check your network connection"
    elif "connection" in error_msg.lower():
        return f"{api_type} API connection failed, please check network or service status"
    elif "quota" in error_msg.lower():
        return f"{api_type} API quota is insufficient, please check your account balance"
    else:
        return f"{api_type} API call failed: {error_msg}"

class ErrorHandler:
    """Error Handler"""
    
    @staticmethod
    def handle_node_error(node_name, function_name, error, return_error_string=True):
        """Handle node errors"""
        error_msg = f"[{node_name}] {function_name} failed to execute: {str(error)}"
        logger.error(error_msg)
        
        if return_error_string:
            return (f"Error: {str(error)}",)
        else:
            raise error
    
    @staticmethod
    def validate_inputs(**inputs):
        """Validate input parameters"""
        errors = []
        
        for key, value in inputs.items():
            if value is None:
                errors.append(f"Parameter {key} cannot be None")
            elif isinstance(value, str) and not value.strip():
                errors.append(f"Parameter {key} cannot be an empty string")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return True

def create_backup_file(file_path):
    """Create a file backup"""
    try:
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup file created: {backup_path}")
            return backup_path
    except Exception as e:
        logger.warning(f"Failed to create backup file: {str(e)}")
    return None

def cleanup_old_logs(log_dir, keep_days=7):
    """Clean up old log files"""
    try:
        if not os.path.exists(log_dir):
            return
        
        import time
        current_time = time.time()
        cutoff_time = current_time - (keep_days * 24 * 60 * 60)
        
        for filename in os.listdir(log_dir):
            if filename.endswith('.log'):
                file_path = os.path.join(log_dir, filename)
                if os.path.getctime(file_path) < cutoff_time:
                    os.remove(file_path)
                    logger.info(f"Cleaned up old log file: {filename}")
    
    except Exception as e:
        logger.warning(f"Failed to clean up old log files: {str(e)}")

# Clean up old logs when the module is loaded
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(current_dir, "logs")
    cleanup_old_logs(log_dir)
except:
    pass
