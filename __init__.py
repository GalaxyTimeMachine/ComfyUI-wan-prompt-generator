"""
ComfyUI Wan2.2提示词生成插件
作者：CodeBuddy
版本：1.0
描述：基于Wan2.2黄金顺序模板的智能提示词生成插件
"""

import os
import sys
import traceback

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"[Wan2.2提示词生成插件] 当前插件目录: {current_dir}")

# 将当前目录添加到Python路径中
if current_dir not in sys.path:
    sys.path.append(current_dir)
    print(f"[Wan2.2提示词生成插件] 已将目录添加到系统路径: {current_dir}")

# 节点类映射字典
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

try:
    # 导入提示词预设生成节点
    print("[Wan2.2提示词生成插件] 开始导入Wan22PromptGenerator节点...")
    
    # 尝试多种导入方式以确保兼容性
    try:
        # 首先尝试相对导入
        from .nodes import Wan22PromptGenerator
        print("[Wan2.2提示词生成插件] 使用相对导入成功")
    except ImportError:
        # 如果相对导入失败，尝试绝对导入
        import nodes
        Wan22PromptGenerator = nodes.Wan22PromptGenerator
        print("[Wan2.2提示词生成插件] 使用绝对导入成功")

    # 注册节点类
    NODE_CLASS_MAPPINGS["Wan22PromptGenerator"] = Wan22PromptGenerator

    NODE_DISPLAY_NAME_MAPPINGS["Wan22PromptGenerator"] = "Wan2.2提示词预设生成器"

    print(f"[Wan2.2提示词生成插件] 成功注册节点数量: {len(NODE_CLASS_MAPPINGS)}")
    for node_name, display_name in NODE_DISPLAY_NAME_MAPPINGS.items():
        print(f"[Wan2.2提示词生成插件] 注册节点: {node_name} -> {display_name}")

except ImportError as e:
    print(f"[Wan2.2提示词生成插件] 导入错误: {str(e)}")
    print(f"[Wan2.2提示词生成插件] 错误详情: {traceback.format_exc()}")
    
    # 尝试最后的备用方案
    try:
        print("[Wan2.2提示词生成插件] 尝试备用导入方案...")
        import sys
        import importlib.util
        
        nodes_path = os.path.join(current_dir, "nodes.py")
        spec = importlib.util.spec_from_file_location("nodes", nodes_path)
        nodes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nodes_module)
        
        NODE_CLASS_MAPPINGS["Wan22PromptGenerator"] = nodes_module.Wan22PromptGenerator

        
        NODE_DISPLAY_NAME_MAPPINGS["Wan22PromptGenerator"] = "Wan2.2提示词预设生成器"
        
        print("[Wan2.2提示词生成插件] 备用导入方案成功")
        
    except Exception as backup_e:
        print(f"[Wan2.2提示词生成插件] 备用导入也失败: {str(backup_e)}")

except Exception as e:
    print(f"[Wan2.2提示词生成插件] 未知错误: {str(e)}")
    print(f"[Wan2.2提示词生成插件] 错误详情: {traceback.format_exc()}")

# 导出给ComfyUI使用的关键变量
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("[Wan2.2提示词生成插件] __init__.py 加载完成!")