"""
ComfyUI Wan2.2 Prompt Generation Plugin - Core Node Class
"""

import json
import os
import traceback
import base64
from io import BytesIO

# Try to import PIL, use a mock if it fails
try:
    from PIL import Image
except ImportError:
    Image = None

# Try to import requests
try:
    import requests
except ImportError:
    requests = None

# Try to import utils module, create a mock if it fails
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
            return (f"Node {node_name}.{method_name} Error: {str(error)}",)

class Wan22PromptGenerator:
    """
    Wan2.2 Prompt Preset Generator Node
    Generates a complete WAN2.2 prompt based on user selections for subject type, camera type, and lighting type
    """
    
    CATEGORY = "Wan2.2/Prompt Generation"
    FUNCTION = "generate_preset_prompt"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("Generated Prompt",)
    
    def __init__(self):
        # Load wan2.2 template configuration
        self.templates = self.load_templates()
    
    def load_templates(self):
        """Load wan2.2 template configuration file"""
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            template_path = os.path.join(current_dir, "wan22_templates.json")
            
            with open(template_path, 'r', encoding='utf-8') as f:
                templates = json.load(f)
            
            # Load character action presets
            character_actions_path = os.path.join(current_dir, "character_actions.json")
            if os.path.exists(character_actions_path):
                with open(character_actions_path, 'r', encoding='utf-8') as f:
                    character_actions = json.load(f)
                    # Merge character action presets into the templates
                    if "character action presets" in character_actions:
                        actions = character_actions["character action presets"]["actions"]
                        action_options = [f"{k} - {v['name']}" for k, v in actions.items()]
                        action_options.insert(0, "No Specific Action")
                        
                        # Update parameter options
                        if "parameter_options" not in templates:
                            templates["parameter_options"] = {}
                        templates["parameter_options"]["Character Action"] = action_options
                        
                        # Add character action preset library
                        templates["character action preset library"] = {
                            "presets": {f"{k} - {v['name']}": {"description": v['description']} for k, v in actions.items()}
                        }
            
            return templates
        except Exception as e:
            print(f"[Wan22PromptGenerator] Failed to load template file: {str(e)}")
            return self.get_default_templates()
    
    def get_default_templates(self):
        """Get default template configuration"""
        return {
            "required": {
                "Subject Type": (["Character", "Object"], {"default": "Character"}),
                "Custom Subject": ("STRING", {"default": "girl", "multiline": False}),
                "Camera Type": (["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"], {"default": "1"}),
                "Lighting Type": (["No Lighting Effect", "Soft Natural Light", "Top Spotlight", "Neon Gradient Light", "Afterglow of the Sunset", "Cold Moonlight", "Morning Mist Light", "Flickering Strobe Light", "Spotlight Sweep", "Candlelight", "Thunderstorm Flash"], {"default": "No Lighting Effect"}),
            }
        }

    def resolve_preset_id(self, selection, presets):
        """Parses camera selection to a preset number, compatible with the following formats:
        - 'Number - Name', e.g., '1 - Fixed Composition'
        - Number only, e.g., '1'
        - Name only, e.g., 'Fixed Composition'
        - Directly as a number key
        """
        try:
            if not presets:
                return "1"
            
            print(f"[DEBUG] Parsing preset selection: '{selection}'")
            print(f"[DEBUG] Available preset keys: {list(presets.keys())}")
            
            # Direct key match
            if selection in presets:
                print(f"[DEBUG] Direct key match: {selection}")
                return selection
            
            # 'Number - Name' format
            if " - " in selection:
                preset_id = selection.split(" - ", 1)[0].strip()
                print(f"[DEBUG] Extracted number: {preset_id}")
                if preset_id in presets:
                    print(f"[DEBUG] Number match successful: {preset_id}")
                    return preset_id
            
            # Number only
            if selection.isdigit() and selection in presets:
                print(f"[DEBUG] Numeric key match: {selection}")
                return selection
            
            # Reverse lookup by name
            for k, v in presets.items():
                if isinstance(v, dict) and v.get("name") == selection:
                    print(f"[DEBUG] Name match successful: {k}")
                    return k
            
            # Fallback to the smallest number
            available_keys = list(presets.keys())
            if available_keys:
                fallback = sorted(available_keys, key=lambda x: int(x) if str(x).isdigit() else 999)[0]
                print(f"[DEBUG] Using fallback key: {fallback}")
                return fallback
            
            return "1"
        except Exception as e:
            print(f"[DEBUG] Preset parsing exception: {e}")
            return "1"
    
    @classmethod
    def INPUT_TYPES(cls):
        """Defines node input parameter types"""
        try:
            instance = cls()
            options = instance.templates.get("parameter_options", {})
            
            print(f"[DEBUG] Loaded parameter options: {list(options.keys())}")
            
            # Ensure all options have default values
            default_options = {
                "Subject Type": ["Character", "Object"],
                "Character Camera Type": ["1 - Fixed Composition"],
                "Object Camera Type": ["1 - Rotate in place (Camera surrounding)"],
                "Lighting Type": ["No Lighting Effect"],
                "Character Action": ["No Specific Action"],
                "Emotional Expression": ["No Specific Emotion"]
            }
            
            # Merge options, prioritizing those from the template
            final_options = {}
            for key, default_value in default_options.items():
                final_options[key] = options.get(key, default_value)
                print(f"[DEBUG] {key}: {len(final_options[key])} options")
            
            return {
                "required": {
                    "Subject Type": (final_options["Subject Type"], {"default": "Character"}),
                    "Custom Subject": ("STRING", {"default": "girl", "multiline": False}),
                },
                "optional": {
                    "Character Camera Type": (final_options["Character Camera Type"], {"default": final_options["Character Camera Type"][0]}),
                    "Object Camera Type": (final_options["Object Camera Type"], {"default": final_options["Object Camera Type"][0]}),
                    "Lighting Type": (final_options["Lighting Type"], {"default": "No Lighting Effect"}),
                    "Character Action": (final_options["Character Action"], {"default": "No Specific Action"}),
                    "Emotional Expression": (final_options["Emotional Expression"], {"default": "No Specific Emotion"}),
                }
            }
        except Exception as e:
            print(f"[ERROR] INPUT_TYPES failed to load: {e}")
            # Return basic default configuration
            return {
                "required": {
                    "Subject Type": (["Character", "Object"], {"default": "Character"}),
                    "Custom Subject": ("STRING", {"default": "girl", "multiline": False}),
                },
                "optional": {
                    "Character Camera Type": (["1 - Fixed Composition"], {"default": "1 - Fixed Composition"}),
                    "Object Camera Type": (["1 - Rotate in place (Camera surrounding)"], {"default": "1 - Rotate in place (Camera surrounding)"}),
                    "Lighting Type": (["No Lighting Effect"], {"default": "No Lighting Effect"}),
                    "Character Action": (["No Specific Action"], {"default": "No Specific Action"}),
                    "Emotional Expression": (["No Specific Emotion"], {"default": "No Specific Emotion"}),
                }
            }
    
    @log_function_call
    def generate_preset_prompt(self, subject_type, custom_subject, character_camera_type=None, object_camera_type=None, lighting_type="No Lighting Effect", character_action="No Specific Action", emotional_expression="No Specific Emotion"):
        """Generate wan2.2 preset prompt"""
        try:
            # Validate input parameters
            ErrorHandler.validate_inputs(
                subject_type=subject_type, custom_subject=custom_subject
            )
            
            logger.info(f"Starting WAN2.2 prompt generation - Subject Type: {subject_type}, Subject: {custom_subject}")
            logger.info(f"Camera Type: {character_camera_type if subject_type == 'Character' else object_camera_type}, Lighting: {lighting_type}")
            logger.info(f"Character Action: {character_action}, Emotional Expression: {emotional_expression}")
            
            # Select camera template based on subject type - use default if not specified
            if subject_type == "Character":
                if not character_camera_type:
                    character_camera_type = "1 - Fixed Composition"  # Use default value
                    print(f"[INFO] No camera type specified for character, using default: {character_camera_type}")
                camera_type = character_camera_type
                camera_presets = self.templates.get("character camera presets", {}).get("presets", {})
            else:  # Object
                if not object_camera_type:
                    object_camera_type = "1 - Rotate in place (Camera surrounding)"  # Use default value
                    print(f"[INFO] No camera type specified for object, using default: {object_camera_type}")
                camera_type = object_camera_type
                camera_presets = self.templates.get("object camera presets", {}).get("presets", {})
            
            # Parse camera selection to preset number
            preset_number = self.resolve_preset_id(camera_type, camera_presets)
            print(f"[DEBUG] Final preset number used: {preset_number}")
            
            # Get the corresponding camera template
            camera_template = camera_presets.get(preset_number, {}).get("template", "")
            print(f"[DEBUG] Retrieved camera template: {camera_template[:100] if camera_template else 'None'}...")
            
            if not camera_template:
                print(f"[ERROR] Template for preset number {preset_number} not found")
                print(f"[ERROR] Available presets: {list(camera_presets.keys())}")
                return (f"Error: Template for camera type {preset_number} not found. Available presets: {list(camera_presets.keys())}",)
            
            # Build the new prompt structure: Custom Subject -> Emotional Expression -> Character Action -> Camera Type -> Lighting Effect
            prompt_parts = []
            
            # 1. Custom subject description
            if subject_type == "Character":
                subject_description = f"{custom_subject} stands in the center of the frame, body naturally upright, expression calm, gazing straight ahead."
            else:
                subject_description = f"{custom_subject} is located in the center of the frame, with a complete and clear structure, and a stable base touching the ground."
            prompt_parts.append(subject_description)
            
            # 2. Emotional expression (if an expression is selected)
            if emotional_expression != "No Specific Emotion":
                # Look up in the emotional expression preset library
                emotional_expression_library = self.templates.get("emotional expression preset library", {}).get("presets", {})
                if emotional_expression in emotional_expression_library:
                    emotion_description = emotional_expression_library[emotional_expression].get("description", "")
                    if emotion_description:
                        prompt_parts.append(emotion_description)
                else:
                    # Look up in emotional expression presets
                    emotional_expression_presets = self.templates.get("emotional expression presets", {})
                    if emotional_expression in emotional_expression_presets:
                        emotion_description = emotional_expression_presets[emotional_expression].get("description", "")
                        if emotion_description:
                            prompt_parts.append(emotion_description)
            
            # 3. Character action (if a character action is selected)
            if character_action != "No Specific Action":
                # Look up in the character action preset library
                character_action_library = self.templates.get("character action preset library", {}).get("presets", {})
                if character_action in character_action_library:
                    action_description = character_action_library[character_action].get("description", "")
                    if action_description:
                        prompt_parts.append(action_description)
                else:
                    # Look up in character action presets (character_actions.json format)
                    character_action_presets = self.templates.get("character action presets", {}).get("actions", {})
                    action_description = None
                    
                    # Try multiple matching methods
                    for key, action in character_action_presets.items():
                        action_option = f"{key} - {action['name']}"
                        # Match full format "Number - Name"
                        if character_action == action_option:
                            action_description = action['description']
                            break
                        # Match name only
                        elif character_action == action['name']:
                            action_description = action['description']
                            break
                        # Match number only
                        elif character_action == key:
                            action_description = action['description']
                            break
                        # Match format with number prefix
                        elif character_action.startswith(f"{key} - "):
                            action_description = action['description']
                            break
                    
                    if action_description:
                        prompt_parts.append(action_description)
            
            # 4. Camera description (extract camera portion after replacing subject words in the template)
            camera_description = camera_template
            if subject_type == "Character":
                # Replace character-related words
                camera_description = camera_description.replace("girl", custom_subject)
                camera_description = camera_description.replace("she", custom_subject)
                camera_description = camera_description.replace("her", f"{custom_subject}’s")
                camera_description = camera_description.replace("character", custom_subject)
                camera_description = camera_description.replace("subject", custom_subject)
                camera_description = camera_description.replace("subject’s back", f"{custom_subject} back")
                camera_description = camera_description.replace("subject’s", f"{custom_subject}’s")
                # Accurately remove subject description prefix, keeping camera description
                prefixes_to_remove = [
                    f"{custom_subject} stands in the center of the frame, body naturally upright, arms down, expression calm, gazing straight ahead.",
                    f"{custom_subject} stands in the center of the frame, body remains still, expression calm.",
                    f"{custom_subject} stands naturally, facing the camera, arms down, hair clinging to her cheeks.",
                    f"{custom_subject} is located in the center of the frame, expression determined, gazing straight ahead.",
                    f"{custom_subject} stands in the center of the frame, body naturally upright, hair hanging down, expression calm.",
                    f"{custom_subject} stands in the center of the frame, expression calm,",
                    f"{custom_subject} stands in the center of the frame, arms naturally down, expression calm.",
                    f"{custom_subject} stands in the center of the frame,",
                    f"{custom_subject} stands facing the camera, expression calm.",
                    f"{custom_subject} stands still in the center of the frame, expression determined.",
                    f"{custom_subject} stands still,",
                    f"{custom_subject} stands in the center of the frame, the camera is close to the front of {custom_subject}.",
                    f"{custom_subject} slowly walks toward the camera,"
                ]
                for prefix in prefixes_to_remove:
                    if camera_description.startswith(prefix):
                        camera_description = camera_description[len(prefix):].strip()
                        break
            else:
                # Replace object-related words
                camera_description = camera_description.replace("subject", custom_subject)
                camera_description = camera_description.replace("subject’s back", f"{custom_subject} back")
                camera_description = camera_description.replace("subject’s", f"{custom_subject}’s")
                # Accurately remove object description prefix, keeping camera description
                prefixes_to_remove = [
                    f"{custom_subject} is located in the center of the frame, with a complete and clear structure, and a stable base touching the ground.",
                    f"{custom_subject} is located in the center of the frame, with the whole object visible.",
                    f"{custom_subject} is located in the center of the frame,",
                ]
                for prefix in prefixes_to_remove:
                    if camera_description.startswith(prefix):
                        camera_description = camera_description[len(prefix):].strip()
                        break
            
            prompt_parts.append(camera_description)
            
            # 5. Lighting effect (if a lighting type is selected) - placed at the end
            lighting_effects_library = self.templates.get("lighting effects library", {}).get("effects", {})
            if lighting_type != "No Lighting Effect" and lighting_type in lighting_effects_library:
                lighting_description = lighting_effects_library[lighting_type]
                prompt_parts.append(lighting_description)
            
            # Combine the final prompt
            final_prompt = " ".join(prompt_parts)
            
            print(f"[Wan22PromptGenerator] Generated WAN2.2 prompt length: {len(final_prompt)}")
            print(f"[Wan22PromptGenerator] WAN2.2 prompt: {final_prompt[:100]}...")
            
            return (final_prompt,)
            
        except Exception as e:
            error_msg = f"An error occurred while generating the WAN2.2 prompt: {str(e)}"
            print(f"[Wan22PromptGenerator] Error: {error_msg}")
            print(f"[Wan22PromptGenerator] Error details: {traceback.format_exc()}")
            return (f"Error: {error_msg}",)

# Node class mapping
NODE_CLASS_MAPPINGS = {
    "Wan22PromptGenerator": Wan22PromptGenerator,
  
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Wan22PromptGenerator": "Wan2.2 Prompt Preset Generator",
}
