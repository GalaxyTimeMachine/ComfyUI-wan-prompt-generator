"""
ComfyUI Wan2.2 Prompt Generation Plugin - Core Node Class
"""

import json
import os
import traceback
import base64
from io import BytesIO

# Try importing PIL, use a mock if it fails
try:
    from PIL import Image
except ImportError:
    Image = None

# Try importing requests
try:
    import requests
except ImportError:
    requests = None

# Try importing utils module, create a mock if it fails
try:
    from .utils import logger, log_function_call, safe_json_load, validate_api_key, handle_api_error, ErrorHandler
except ImportError:
    # Create mock objects for testing
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
        return f"{provider} API Error: {str(error)}"

    class ErrorHandler:
        @staticmethod
        def validate_inputs(**kwargs):
            pass

        @staticmethod
        def handle_node_error(node_name, method_name, error):
            return (f"Node {node_name}.{method_name} failed: {str(error)}",)

class Wan22PromptGenerator:
    """
    Wan2.2 Prompt Generator Node
    """
    def __init__(self):
        self.templates = self.load_templates()

    @staticmethod
    def load_templates():
        """Safely load JSON templates"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(current_dir, "wan22_templates.json")
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load wan22_templates.json: {str(e)}")
            return None

    @classmethod
    def INPUT_TYPES(cls):
        """Define node input types"""
        templates = cls.load_templates()
        if not templates:
            return {}
        
        options_map = templates.get("parameter_options", {})
        
        logger.info(f"Loaded parameter options: {list(options_map.keys())}")
        for k, v in options_map.items():
            logger.info(f"{k}: {len(v)} options")
        
        return {
            "required": {
                "subject_type": (options_map.get("subject_type", []),),
                "custom_subject": ("STRING", {"multiline": False, "default": ""}),
                "character_camera_type": (options_map.get("character_camera_type", []), {"default": "No Specific Action"}),
                "object_camera_type": (options_map.get("object_camera_type", []), {"default": "No Specific Action"}),
                "lighting_type": (options_map.get("lighting_type", []), {"default": "No Lighting Effect"}),
                "character_action": (options_map.get("character_action", []), {"default": "No Specific Action"}),
                "emotional_expression": (options_map.get("emotional_expression", []), {"default": "No Specific Emotion"})
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    FUNCTION = "generate_preset_prompt"
    CATEGORY = "Wan2.2/Prompt Generation"

    @log_function_call
    def generate_preset_prompt(self, subject_type, custom_subject, character_camera_type, object_camera_type, lighting_type, character_action, emotional_expression):
        """Generate a complete Wan2.2 format prompt"""
        try:
            # Load templates again inside the function to be safe
            self.templates = self.load_templates()
            if not self.templates:
                return ("Error: Template file not loaded.",)
            
            prompt_parts = []
            
            # 1. Subject Type (mandatory)
            if not custom_subject or custom_subject.strip() == "":
                return ("Error: Please provide a custom subject description.",)
            
            prompt_parts.append(custom_subject)
            
            # 2. Emotional Expression (if selected)
            emotional_expression_presets = self.templates.get("emotional expression presets", {})
            if emotional_expression != "No Specific Emotion" and emotional_expression in emotional_expression_presets:
                emotion_description = emotional_expression_presets[emotional_expression].get("description", "")
                prompt_parts.append(emotion_description)
            
            # 3. Character Action (if selected)
            character_action_presets = self.templates.get("character action presets", {}).get("actions", {})
            if character_action != "No Specific Action" and character_action in character_action_presets:
                action_description = character_action_presets[character_action].get("description", "")
                
                # Replace the generic subject with the custom subject
                if "subject" in action_description.lower():
                    action_description = action_description.replace("The subject", custom_subject.capitalize())
                
                prompt_parts.append(action_description)
            
            # 4. Camera Movement (conditional based on subject type)
            if subject_type == "Character":
                camera_presets = self.templates.get("character camera presets", {}).get("presets", {})
                camera_description = ""
                for preset_id, preset_data in camera_presets.items():
                    if preset_data.get("name") == character_camera_type:
                        camera_description = preset_data.get("template", "")
                        break
                
                if camera_description:
                    # Replace the generic subject with the custom subject
                    camera_description = camera_description.replace("Subject", custom_subject.capitalize()).replace("subject", custom_subject.capitalize())
                    prompt_parts.append(camera_description)

            elif subject_type == "Object":
                camera_presets = self.templates.get("object camera presets", {}).get("presets", {})
                camera_description = ""
                for preset_id, preset_data in camera_presets.items():
                    if preset_data.get("name") == object_camera_type:
                        camera_description = preset_data.get("template", "")
                        break

                if camera_description:
                    # Replace the generic subject with the custom subject
                    camera_description = camera_description.replace("Subject", custom_subject.capitalize()).replace("subject", custom_subject.capitalize())
                    prompt_parts.append(camera_description)

            # 5. Lighting Effect (if selected)
            lighting_effects = self.templates.get("lighting effects library", {}).get("effects", {})
            if lighting_type != "No Lighting Effect" and lighting_type in lighting_effects:
                lighting_description = lighting_effects[lighting_type]
                
                # Replace the generic subject with the custom subject
                lighting_description = lighting_description.replace("Subject", custom_subject.capitalize()).replace("subject", custom_subject.capitalize())

                prompt_parts.append(lighting_description)
            
            # Combine the final prompt
            final_prompt = " ".join(prompt_parts)
            
            logger.info(f"Generated WAN2.2 prompt length: {len(final_prompt)}")
            logger.info(f"WAN2.2 prompt: {final_prompt[:100]}...")
            
            return (final_prompt,)
            
        except Exception as e:
            error_msg = f"An error occurred while generating the Wan2.2 prompt: {str(e)}"
            return ErrorHandler.handle_node_error("Wan22PromptGenerator", "generate_preset_prompt", error_msg)

    @classmethod
    def IS_CHANGED(cls, **kwargs):
        """Prevent caching of the node's output"""
        return float("NaN")

    @classmethod
    def IS_A_VALID_NODE(cls):
        """Check if the node is valid to load"""
        return cls.load_templates() is not None

# Define the node mappings for ComfyUI
NODE_CLASS_MAPPINGS = {
    "Wan22PromptGenerator": Wan22PromptGenerator,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22PromptGenerator": "Wan2.2 Prompt Preset Generator",
}
