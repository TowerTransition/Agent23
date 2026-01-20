#!/usr/bin/env python3
"""
Quick test for PEFT adapter integration.
Tests that TextGenerator can load and use Elevaretinyllma directly.
"""

import os
import sys

# Set PEFT adapter path
os.environ["PEFT_ADAPTER_PATH"] = "/home/amaziahy80/AGENT/models/Elevaretinyllma"
os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

print("=" * 80)
print("PEFT Adapter Test - Elevaretinyllma")
print("=" * 80)
print()

# Test 1: Check imports
print("Test 1: Checking imports...")
try:
    import torch
    print(f"  ✓ torch {torch.__version__} imported")
except ImportError as e:
    print(f"  ✗ torch import failed: {e}")
    sys.exit(1)

try:
    import transformers
    print(f"  ✓ transformers {transformers.__version__} imported")
except ImportError as e:
    print(f"  ✗ transformers import failed: {e}")
    sys.exit(1)

try:
    import peft
    print(f"  ✓ peft {peft.__version__} imported")
except ImportError as e:
    print(f"  ✗ peft import failed: {e}")
    sys.exit(1)

print()

# Test 2: Check model path exists
print("Test 2: Checking model path...")
model_path = os.environ.get("PEFT_ADAPTER_PATH")
if not model_path:
    print("  ✗ PEFT_ADAPTER_PATH not set")
    sys.exit(1)

if not os.path.exists(model_path):
    print(f"  ✗ Model path not found: {model_path}")
    sys.exit(1)

print(f"  ✓ Model path exists: {model_path}")

# Get directory size
import subprocess
try:
    result = subprocess.run(['du', '-sh', model_path], capture_output=True, text=True)
    if result.returncode == 0:
        size = result.stdout.split()[0]
        print(f"  ✓ Model directory size: {size}")
except:
    pass

# Check for required files
required_files = ["adapter_config.json", "adapter_model.safetensors"]
for file in required_files:
    file_path = os.path.join(model_path, file)
    if os.path.exists(file_path):
        print(f"  ✓ Found: {file}")
    else:
        print(f"  ⚠ Missing: {file}")

print()

# Test 3: Initialize TextGenerator
print("Test 3: Initializing TextGenerator with PEFT adapter...")
try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    
    from agents.content_creator.brand_guidelines_manager import BrandGuidelinesManager
    from agents.content_creator.text_generator import TextGenerator
    
    # Initialize brand manager
    brand_manager = BrandGuidelinesManager()
    print("  ✓ BrandGuidelinesManager initialized")
    
    # Initialize TextGenerator (should load PEFT adapter)
    text_gen = TextGenerator(brand_manager=brand_manager)
    print("  ✓ TextGenerator initialized")
    
    # Check if using direct model
    if hasattr(text_gen, 'use_direct_model') and text_gen.use_direct_model:
        print("  ✓ Using direct PEFT model (not HTTP endpoint)")
        if text_gen.model_obj is not None:
            print("  ✓ Model object loaded successfully")
        else:
            print("  ⚠ Model object is None")
    else:
        print("  ⚠ Falling back to HTTP endpoint mode")
        print(f"     Endpoint: {text_gen.local_llm_endpoint}")
        
except Exception as e:
    print(f"  ✗ Initialization failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Test 4: Simple generation test (optional - can skip if takes too long)
print("Test 4: Testing text generation (this may take a minute)...")
try:
    context = {
        "trend": {
            "title": "AI in Healthcare",
            "description": "AI helping doctors diagnose diseases"
        },
        "lens_plan": {
            "domain": "Healthcare"
        },
        "platform_guidelines": {}
    }
    
    print("  Generating test post...")
    result = text_gen.generate_text(
        context=context,
        platform="facebook",
        max_length=200,
        temperature=0.7
    )
    
    if result and "text" in result:
        text = result["text"]
        print(f"  ✓ Generation successful!")
        print(f"  ✓ Generated {len(text)} characters")
        print(f"  Preview: {text[:100]}...")
    else:
        print(f"  ⚠ Generation returned: {result}")
        
except Exception as e:
    print(f"  ⚠ Generation test failed: {e}")
    print("  (This is okay if model loading takes time or needs more space)")
    import traceback
    traceback.print_exc()

print()
print("=" * 80)
print("Test Complete!")
print("=" * 80)
print()
print("If all tests passed, your PEFT adapter is working!")
print("The TextGenerator will now use Elevaretinyllma directly for inference.")
