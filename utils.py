"""
ComfyUI Wan2.2提示词生成插件 - 工具函数
"""

import logging
import os
import json
from datetime import datetime
from functools import wraps

class Wan22Logger:
    """Wan2.2插件专用日志记录器"""
    
    def __init__(self, name="Wan22Plugin"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.INFO)
        
        # 避免重复添加handler
        if not self.logger.handlers:
            self.setup_logger()
    
    def setup_logger(self):
        """设置日志记录器"""
        try:
            # 创建logs目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            log_dir = os.path.join(current_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建文件handler
            log_file = os.path.join(log_dir, f"wan22_plugin_{datetime.now().strftime('%Y%m%d')}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            # 创建控制台handler
            console_handler = logging.StreamHandler()
            console_handler.setLevel(logging.INFO)
            
            # 创建formatter
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            
            file_handler.setFormatter(formatter)
            console_handler.setFormatter(formatter)
            
            # 添加handler
            self.logger.addHandler(file_handler)
            self.logger.addHandler(console_handler)
            
        except Exception as e:
            print(f"[Wan22Logger] 设置日志记录器失败: {str(e)}")
    
    def info(self, message):
        """记录信息日志"""
        self.logger.info(message)
    
    def error(self, message):
        """记录错误日志"""
        self.logger.error(message)
    
    def warning(self, message):
        """记录警告日志"""
        self.logger.warning(message)
    
    def debug(self, message):
        """记录调试日志"""
        self.logger.debug(message)

# 全局日志记录器实例
logger = Wan22Logger()

def log_function_call(func):
    """装饰器：记录函数调用日志"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        func_name = func.__name__
        class_name = args[0].__class__.__name__ if args else "Unknown"
        
        logger.info(f"[{class_name}] 开始执行 {func_name}")
        
        try:
            result = func(*args, **kwargs)
            logger.info(f"[{class_name}] {func_name} 执行成功")
            return result
        except Exception as e:
            logger.error(f"[{class_name}] {func_name} 执行失败: {str(e)}")
            raise
    
    return wrapper

def safe_json_load(file_path, default_value=None):
    """安全加载JSON文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        logger.warning(f"JSON文件不存在: {file_path}")
        return default_value
    except json.JSONDecodeError as e:
        logger.error(f"JSON文件格式错误: {file_path}, 错误: {str(e)}")
        return default_value
    except Exception as e:
        logger.error(f"加载JSON文件失败: {file_path}, 错误: {str(e)}")
        return default_value

def validate_api_key(api_key, model_type="openai"):
    """验证API密钥格式"""
    if not api_key or not isinstance(api_key, str):
        return False, "API密钥不能为空"
    
    api_key = api_key.strip()
    
    if model_type.lower() == "openai":
        if not api_key.startswith("sk-"):
            return False, "OpenAI API密钥格式错误，应以'sk-'开头"
        if len(api_key) < 20:
            return False, "OpenAI API密钥长度不足"
    elif model_type.lower() == "claude":
        if not api_key.startswith("sk-ant-"):
            return False, "Claude API密钥格式错误，应以'sk-ant-'开头"
        if len(api_key) < 30:
            return False, "Claude API密钥长度不足"
    
    return True, "API密钥格式正确"

def handle_api_error(error, api_type="LLM"):
    """统一处理API错误"""
    error_msg = str(error)
    
    # 常见错误类型处理
    if "401" in error_msg or "Unauthorized" in error_msg:
        return f"{api_type} API密钥无效或已过期"
    elif "429" in error_msg or "rate limit" in error_msg.lower():
        return f"{api_type} API请求频率超限，请稍后重试"
    elif "timeout" in error_msg.lower():
        return f"{api_type} API请求超时，请检查网络连接"
    elif "connection" in error_msg.lower():
        return f"{api_type} API连接失败，请检查网络或服务状态"
    elif "quota" in error_msg.lower():
        return f"{api_type} API配额不足，请检查账户余额"
    else:
        return f"{api_type} API调用失败: {error_msg}"

class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_node_error(node_name, function_name, error, return_error_string=True):
        """处理节点错误"""
        error_msg = f"[{node_name}] {function_name} 执行失败: {str(error)}"
        logger.error(error_msg)
        
        if return_error_string:
            return (f"错误: {str(error)}",)
        else:
            raise error
    
    @staticmethod
    def validate_inputs(**inputs):
        """验证输入参数"""
        errors = []
        
        for key, value in inputs.items():
            if value is None:
                errors.append(f"参数 {key} 不能为空")
            elif isinstance(value, str) and not value.strip():
                errors.append(f"参数 {key} 不能为空字符串")
        
        if errors:
            raise ValueError("; ".join(errors))
        
        return True

def create_backup_file(file_path):
    """创建文件备份"""
    try:
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"已创建备份文件: {backup_path}")
            return backup_path
    except Exception as e:
        logger.warning(f"创建备份文件失败: {str(e)}")
    return None

def cleanup_old_logs(log_dir, keep_days=7):
    """清理旧日志文件"""
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
                    logger.info(f"已清理旧日志文件: {filename}")
    
    except Exception as e:
        logger.warning(f"清理旧日志文件失败: {str(e)}")

# 在模块加载时清理旧日志
try:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    log_dir = os.path.join(current_dir, "logs")
    cleanup_old_logs(log_dir)
except:
    pass