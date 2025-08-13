"""
ComfyUI Wan2.2提示词生成插件 - 核心节点类
"""

import json
import os
import traceback
import base64
from io import BytesIO

# 尝试导入PIL，如果失败则使用mock
try:
    from PIL import Image
except ImportError:
    Image = None

# 尝试导入requests
try:
    import requests
except ImportError:
    requests = None

# 尝试导入utils模块，如果失败则创建mock
try:
    from .utils import logger, log_function_call, safe_json_load, validate_api_key, handle_api_error, ErrorHandler
except ImportError:
    # 创建mock对象用于测试
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
    
    logger = MockLogger()
    
    def log_function_call(func):
        return func
    
    def safe_json_load(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def validate_api_key(key, provider):
        return True, "OK"
    
    def handle_api_error(error, provider):
        return f"{provider} API错误: {str(error)}"
    
    class ErrorHandler:
        @staticmethod
        def validate_inputs(**kwargs):
            pass
        
        @staticmethod
        def handle_node_error(node_name, method_name, error):
            return (f"节点 {node_name}.{method_name} 错误: {str(error)}",)

class Wan22PromptGenerator:
    """
    Wan2.2提示词预设生成节点
    根据用户选择的主体类型、运镜类型和光线类型生成完整的WAN2.2提示词
    """
    
    CATEGORY = "Wan2.2/提示词生成"
    FUNCTION = "generate_preset_prompt"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("生成的提示词",)
    
    def __init__(self):
        # 加载wan2.2模板配置
        self.templates = self.load_templates()
    
    def load_templates(self):
        """加载wan2.2模板配置文件"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "wan22_templates.json")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            
            # 加载人物动作预设
            character_actions_path = os.path.join(current_dir, "character_actions.json")
            if os.path.exists(character_actions_path):
                with open(character_actions_path, 'r', encoding='utf-8') as f:
                    character_actions = json.load(f)
                    # 将人物动作预设合并到模板中
                    if "人物动作预设" in character_actions:
                        actions = character_actions["人物动作预设"]["actions"]
                        action_options = [f"{k} - {v['name']}" for k, v in actions.items()]
                        action_options.insert(0, "无特定动作")
                        
                        # 更新参数选项
                        if "parameter_options" not in templates:
                            templates["parameter_options"] = {}
                        templates["parameter_options"]["人物动作"] = action_options
                        
                        # 添加人物动作预设库
                        templates["人物动作预设库"] = {
                            "presets": {f"{k} - {v['name']}": {"description": v['description']} for k, v in actions.items()}
                        }
            
            return templates
        except Exception as e:
            print(f"[Wan22PromptGenerator] 加载模板文件失败: {str(e)}")
            return self.get_default_templates()
    
    def get_default_templates(self):
        """获取默认模板配置"""
        return {
            "required": {
                "主体类型": (["人物", "物体"], {"default": "人物"}),
                "自定义主体": ("STRING", {"default": "女孩", "multiline": False}),
                "运镜类型": (["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"], {"default": "1"}),
                "光线类型": (["无光线效果", "柔和自然光", "顶部聚光", "霓虹渐变光", "晚霞余晖", "月光冷辉", "清晨薄雾光", "闪烁频闪光", "聚光扫射", "烛火暖光", "雷暴闪光"], {"default": "无光线效果"}),
            }
        }

    def resolve_preset_id(self, selection, presets):
        """将运镜选择解析为预设编号，兼容以下格式：
        - '编号 - 名称'，如 '1 - 固定构图'
        - 仅编号，如 '1'
        - 仅名称，如 '固定构图'
        - 直接为编号键
        """
        try:
            if not presets:
                return "1"
            
            print(f"[DEBUG] 解析预设选择: '{selection}'")
            print(f"[DEBUG] 可用预设键: {list(presets.keys())}")
            
            # 直接是键
            if selection in presets:
                print(f"[DEBUG] 直接匹配键: {selection}")
                return selection
            
            # '编号 - 名称' 形式
            if " - " in selection:
                preset_id = selection.split(" - ", 1)[0].strip()
                print(f"[DEBUG] 提取编号: {preset_id}")
                if preset_id in presets:
                    print(f"[DEBUG] 编号匹配成功: {preset_id}")
                    return preset_id
            
            # 仅编号
            if selection.isdigit() and selection in presets:
                print(f"[DEBUG] 数字编号匹配: {selection}")
                return selection
            
            # 通过名称反查
            for k, v in presets.items():
                if isinstance(v, dict) and v.get("name") == selection:
                    print(f"[DEBUG] 名称匹配成功: {k}")
                    return k
            
            # 回退为最小编号
            available_keys = list(presets.keys())
            if available_keys:
                fallback = sorted(available_keys, key=lambda x: int(x) if str(x).isdigit() else 999)[0]
                print(f"[DEBUG] 使用回退键: {fallback}")
                return fallback
            
            return "1"
        except Exception as e:
            print(f"[DEBUG] 预设解析异常: {e}")
            return "1"
    
    @classmethod
    def INPUT_TYPES(cls):
        """定义节点输入参数类型"""
        try:
            instance = cls()
            options = instance.templates.get("parameter_options", {})
            
            print(f"[DEBUG] 加载的参数选项: {list(options.keys())}")
            
            # 确保所有选项都有默认值
            default_options = {
                "主体类型": ["人物", "物体"],
                "人物运镜类型": ["1 - 固定构图"],
                "物体运镜类型": ["1 - 原地旋转（镜头环绕）"],
                "光线类型": ["无光线效果"],
                "人物动作": ["无特定动作"],
                "情绪表情": ["无特定情绪"]
            }
            
            # 合并选项，优先使用模板中的选项
            final_options = {}
            for key, default_value in default_options.items():
                final_options[key] = options.get(key, default_value)
                print(f"[DEBUG] {key}: {len(final_options[key])} 个选项")
            
            return {
                "required": {
                    "主体类型": (final_options["主体类型"], {"default": "人物"}),
                    "自定义主体": ("STRING", {"default": "女孩", "multiline": False}),
                },
                "optional": {
                    "人物运镜类型": (final_options["人物运镜类型"], {"default": final_options["人物运镜类型"][0]}),
                    "物体运镜类型": (final_options["物体运镜类型"], {"default": final_options["物体运镜类型"][0]}),
                    "光线类型": (final_options["光线类型"], {"default": "无光线效果"}),
                    "人物动作": (final_options["人物动作"], {"default": "无特定动作"}),
                    "情绪表情": (final_options["情绪表情"], {"default": "无特定情绪"}),
                }
            }
        except Exception as e:
            print(f"[ERROR] INPUT_TYPES加载失败: {e}")
            # 返回基本的默认配置
            return {
                "required": {
                    "主体类型": (["人物", "物体"], {"default": "人物"}),
                    "自定义主体": ("STRING", {"default": "女孩", "multiline": False}),
                },
                "optional": {
                    "人物运镜类型": (["1 - 固定构图"], {"default": "1 - 固定构图"}),
                    "物体运镜类型": (["1 - 原地旋转（镜头环绕）"], {"default": "1 - 原地旋转（镜头环绕）"}),
                    "光线类型": (["无光线效果"], {"default": "无光线效果"}),
                    "人物动作": (["无特定动作"], {"default": "无特定动作"}),
                    "情绪表情": (["无特定情绪"], {"default": "无特定情绪"}),
                }
            }
    
    @log_function_call
    def generate_preset_prompt(self, 主体类型, 自定义主体, 人物运镜类型=None, 物体运镜类型=None, 光线类型="无光线效果", 人物动作="无特定动作", 情绪表情="无特定情绪"):
        """生成wan2.2预设提示词"""
        try:
            # 验证输入参数
            ErrorHandler.validate_inputs(
                主体类型=主体类型, 自定义主体=自定义主体
            )
            
            logger.info(f"开始生成WAN2.2提示词 - 主体类型: {主体类型}, 主体: {自定义主体}")
            logger.info(f"运镜类型: {人物运镜类型 if 主体类型 == '人物' else 物体运镜类型}, 光线: {光线类型}")
            logger.info(f"人物动作: {人物动作}, 情绪表情: {情绪表情}")
            
            # 根据主体类型选择运镜模板 - 如果没有指定运镜类型，使用默认值
            if 主体类型 == "人物":
                if not 人物运镜类型:
                    人物运镜类型 = "1 - 固定构图"  # 使用默认值
                    print(f"[INFO] 人物主体未指定运镜类型，使用默认值: {人物运镜类型}")
                运镜类型 = 人物运镜类型
                运镜预设 = self.templates.get("人物运镜预设", {}).get("presets", {})
            else:  # 物体
                if not 物体运镜类型:
                    物体运镜类型 = "1 - 原地旋转（镜头环绕）"  # 使用默认值
                    print(f"[INFO] 物体主体未指定运镜类型，使用默认值: {物体运镜类型}")
                运镜类型 = 物体运镜类型
                运镜预设 = self.templates.get("物体运镜预设", {}).get("presets", {})
            
            # 解析运镜选择为预设编号
            预设编号 = self.resolve_preset_id(运镜类型, 运镜预设)
            print(f"[DEBUG] 最终使用的预设编号: {预设编号}")
            
            # 获取对应的运镜模板
            运镜模板 = 运镜预设.get(预设编号, {}).get("template", "")
            print(f"[DEBUG] 获取到的运镜模板: {运镜模板[:100] if 运镜模板 else 'None'}...")
            
            if not 运镜模板:
                print(f"[ERROR] 未找到预设编号 {预设编号} 的模板")
                print(f"[ERROR] 可用预设: {list(运镜预设.keys())}")
                return (f"错误：未找到运镜类型 {预设编号} 的模板。可用预设: {list(运镜预设.keys())}",)
            
            # 构建新的提示词结构：自定义主体 → 情绪表情 → 人物动作 → 运镜类型 → 光线效果
            prompt_parts = []
            
            # 1. 自定义主体描述
            if 主体类型 == "人物":
                主体描述 = f"{自定义主体}站在画面中央，身体自然挺直，表情平静，目光直视前方。"
            else:
                主体描述 = f"{自定义主体}位于画面中央，结构完整清晰，底部稳固接触地面。"
            prompt_parts.append(主体描述)
            
            # 2. 情绪表情（如果选择了情绪表情）
            if 情绪表情 != "无特定情绪":
                # 从情绪表情预设库中查找
                情绪表情预设库 = self.templates.get("情绪表情预设库", {}).get("presets", {})
                if 情绪表情 in 情绪表情预设库:
                    情绪描述 = 情绪表情预设库[情绪表情].get("description", "")
                    if 情绪描述:
                        prompt_parts.append(情绪描述)
                else:
                    # 从情绪表情预设中查找
                    情绪表情预设 = self.templates.get("情绪表情预设", {})
                    if 情绪表情 in 情绪表情预设:
                        情绪描述 = 情绪表情预设[情绪表情].get("描述", "")
                        if 情绪描述:
                            prompt_parts.append(情绪描述)
            
            # 3. 人物动作（如果选择了人物动作）
            if 人物动作 != "无特定动作":
                # 从人物动作预设库中查找
                人物动作预设库 = self.templates.get("人物动作预设库", {}).get("presets", {})
                if 人物动作 in 人物动作预设库:
                    动作描述 = 人物动作预设库[人物动作].get("description", "")
                    if 动作描述:
                        prompt_parts.append(动作描述)
                else:
                    # 从人物动作预设中查找（character_actions.json格式）
                    人物动作预设 = self.templates.get("人物动作预设", {}).get("actions", {})
                    动作描述 = None
                    
                    # 尝试多种匹配方式
                    for key, action in 人物动作预设.items():
                        action_option = f"{key} - {action['name']}"
                        # 匹配完整格式 "编号 - 名称"
                        if 人物动作 == action_option:
                            动作描述 = action['description']
                            break
                        # 匹配仅名称
                        elif 人物动作 == action['name']:
                            动作描述 = action['description']
                            break
                        # 匹配仅编号
                        elif 人物动作 == key:
                            动作描述 = action['description']
                            break
                        # 匹配带编号前缀的格式
                        elif 人物动作.startswith(f"{key} - "):
                            动作描述 = action['description']
                            break
                    
                    if 动作描述:
                        prompt_parts.append(动作描述)
            
            # 4. 运镜描述（替换模板中的主体词汇后提取运镜部分）
            运镜描述 = 运镜模板
            if 主体类型 == "人物":
                # 替换人物相关词汇
                运镜描述 = 运镜描述.replace("女孩", 自定义主体)
                运镜描述 = 运镜描述.replace("她", 自定义主体)
                运镜描述 = 运镜描述.replace("她的", f"{自定义主体}的")
                运镜描述 = 运镜描述.replace("角色", 自定义主体)
                运镜描述 = 运镜描述.replace("主体", 自定义主体)
                运镜描述 = 运镜描述.replace("主体背面", f"{自定义主体}背面")
                运镜描述 = 运镜描述.replace("主体的", f"{自定义主体}的")
                # 精确移除主体描述前缀，保留镜头描述
                prefixes_to_remove = [
                    f"{自定义主体}站在画面中央，身体自然挺直，双臂垂落，表情平静，目光直视前方。",
                    f"{自定义主体}站在画面中央，身体保持静止，表情冷静。",
                    f"{自定义主体}自然站立，正面朝向镜头，双臂下垂，发丝贴合脸颊。",
                    f"{自定义主体}位于画面中央，表情坚定，目光直视前方。",
                    f"{自定义主体}站在画面中央，身体自然挺直，头发垂落，表情平静。",
                    f"{自定义主体}站在画面中央，表情冷静，",
                    f"{自定义主体}站在画面中央，双臂自然下垂，表情平静。",
                    f"{自定义主体}站在画面中央，",
                    f"{自定义主体}面向镜头站立，表情冷静。",
                    f"{自定义主体}站在画面中央不动，表情坚定。",
                    f"{自定义主体}站立不动，",
                    f"{自定义主体}站在画面中央，镜头贴近{自定义主体}的正前方。",
                    f"{自定义主体}缓慢走向镜头，"
                ]
                for prefix in prefixes_to_remove:
                    if 运镜描述.startswith(prefix):
                        运镜描述 = 运镜描述[len(prefix):].strip()
                        break
            else:
                # 替换物体相关词汇
                运镜描述 = 运镜描述.replace("主体", 自定义主体)
                运镜描述 = 运镜描述.replace("主体背面", f"{自定义主体}背面")
                运镜描述 = 运镜描述.replace("主体的", f"{自定义主体}的")
                # 精确移除物体描述前缀，保留镜头描述
                prefixes_to_remove = [
                    f"{自定义主体}位于画面中央，结构完整清晰，底部稳固接触地面。",
                    f"{自定义主体}位于画面中央，整体完整可见。",
                    f"{自定义主体}位于画面中央，",
                ]
                for prefix in prefixes_to_remove:
                    if 运镜描述.startswith(prefix):
                        运镜描述 = 运镜描述[len(prefix):].strip()
                        break
            
            prompt_parts.append(运镜描述)
            
            # 5. 光线效果（如果选择了光线类型）- 放在最后
            光线效果库 = self.templates.get("光线效果库", {}).get("effects", {})
            if 光线类型 != "无光线效果" and 光线类型 in 光线效果库:
                光线描述 = 光线效果库[光线类型]
                prompt_parts.append(光线描述)
            
            # 组合最终提示词
            final_prompt = " ".join(prompt_parts)
            
            print(f"[Wan22PromptGenerator] 生成的WAN2.2提示词长度: {len(final_prompt)}")
            print(f"[Wan22PromptGenerator] WAN2.2提示词: {final_prompt[:100]}...")
            
            return (final_prompt,)
            
        except Exception as e:
            error_msg = f"生成WAN2.2提示词时发生错误: {str(e)}"
            print(f"[Wan22PromptGenerator] 错误: {error_msg}")
            print(f"[Wan22PromptGenerator] 错误详情: {traceback.format_exc()}")
            return (f"错误：{error_msg}",)



# 节点类映射
NODE_CLASS_MAPPINGS = {
    "Wan22PromptGenerator": Wan22PromptGenerator,
  
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22PromptGenerator": "Wan2.2提示词预设生成器",

}
