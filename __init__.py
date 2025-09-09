"""
ComfyUI Wan2.2 Prompt Generation Plugin
Author: CodeBuddy
Version: 1.0
Description: An intelligent prompt generation plugin based on the Wan2.2 golden order template
"""

import os
import sys
import traceback

# Get the absolute path of the current file's directory
current_dir = os.path.dirname(os.path.abspath(__file__))
print(f"[Wan2.2 Prompt Generation Plugin] Current plugin directory: {current_dir}")

# Add the current directory to the Python path
if current_dir not in sys.path:
    sys.path.append(current_dir)
    print(f"[Wan2.2 Prompt Generation Plugin] Directory added to system path: {current_dir}")

# Node class mapping dictionaries
NODE_CLASS_MAPPINGS = {}
NODE_DISPLAY_NAME_MAPPINGS = {}

try:
    # Import the prompt preset generation node
    print("[Wan2.2 Prompt Generation Plugin] Starting import of Wan22PromptGenerator node...")
    
    # Try multiple import methods to ensure compatibility
    try:
        # First, try relative import
        from .nodes import Wan22PromptGenerator
        print("[Wan2.2 Prompt Generation Plugin] Relative import successful")
    except ImportError:
        # If relative import fails, try absolute import
        import nodes
        Wan22PromptGenerator = nodes.Wan22PromptGenerator
        print("[Wan2.2 Prompt Generation Plugin] Absolute import successful")

    # Register the node class
    NODE_CLASS_MAPPINGS["Wan22PromptGenerator"] = Wan22PromptGenerator

    NODE_DISPLAY_NAME_MAPPINGS["Wan22PromptGenerator"] = "Wan2.2 Prompt Preset Generator"

    print(f"[Wan2.2 Prompt Generation Plugin] Successfully registered node count: {len(NODE_CLASS_MAPPINGS)}")
    for node_name, display_name in NODE_DISPLAY_NAME_MAPPINGS.items():
        print(f"[Wan2.2 Prompt Generation Plugin] Registered node: {node_name} -> {display_name}")

except ImportError as e:
    print(f"[Wan2.2 Prompt Generation Plugin] Import error: {str(e)}")
    print(f"[Wan2.2 Prompt Generation Plugin] Error details: {traceback.format_exc()}")
    
    # Try the last fallback method
    try:
        print("[Wan2.2 Prompt Generation Plugin] Attempting fallback import method...")
        import sys
        import importlib.util
        
        nodes_path = os.path.join(current_dir, "nodes.py")
        spec = importlib.util.spec_from_file_location("nodes", nodes_path)
        nodes_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(nodes_module)
        
        NODE_CLASS_MAPPINGS["Wan22PromptGenerator"] = nodes_module.Wan22PromptGenerator

        
        NODE_DISPLAY_NAME_MAPPINGS["Wan22PromptGenerator"] = "Wan2.2 Prompt Preset Generator"
        
        print("[Wan2.2 Prompt Generation Plugin] Fallback import method successful")
        
    except Exception as backup_e:
        print(f"[Wan2.2 Prompt Generation Plugin] Fallback import also failed: {str(backup_e)}")

except Exception as e:
    print(f"[Wan2.2 Prompt Generation Plugin] Unknown error: {str(e)}")
    print(f"[Wan2.2 Prompt Generation Plugin] Error details: {traceback.format_exc()}")

# Export key variables for ComfyUI
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']

print("[Wan2.2 Prompt Generation Plugin] __init__.py loaded!")
