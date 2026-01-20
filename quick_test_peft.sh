#!/bin/bash
# Quick inline test for PEFT adapter
# Run this on SSH: bash quick_test_peft.sh

cd ~/AGENT
source venv/bin/activate

echo "=== Quick PEFT Adapter Test ==="
echo ""

# Set environment variables
export PEFT_ADAPTER_PATH="/home/amaziahy80/AGENT/models/Elevaretinyllma"
export BASE_MODEL_NAME="TinyLlama/TinyLlama-1.1B-Chat-v1.0"

echo "1. Testing imports..."
python3 << 'PYTHON_EOF'
import sys
try:
    import torch
    print(f"  ✓ torch {torch.__version__}")
except ImportError as e:
    print(f"  ✗ torch: {e}")
    sys.exit(1)

try:
    import transformers
    print(f"  ✓ transformers {transformers.__version__}")
except ImportError as e:
    print(f"  ✗ transformers: {e}")
    sys.exit(1)

try:
    import peft
    print(f"  ✓ peft {peft.__version__}")
except ImportError as e:
    print(f"  ✗ peft: {e}")
    sys.exit(1)
PYTHON_EOF

if [ $? -ne 0 ]; then
    echo "Import test failed!"
    exit 1
fi

echo ""
echo "2. Checking model path..."
if [ -d "$PEFT_ADAPTER_PATH" ]; then
    echo "  ✓ Model path exists: $PEFT_ADAPTER_PATH"
    ls -lh "$PEFT_ADAPTER_PATH" | head -5
else
    echo "  ✗ Model path not found: $PEFT_ADAPTER_PATH"
    exit 1
fi

echo ""
echo "3. Testing TextGenerator initialization..."
python3 << 'PYTHON_EOF'
import os
import sys

# Set paths
sys.path.insert(0, os.getcwd())

os.environ["PEFT_ADAPTER_PATH"] = "/home/amaziahy80/AGENT/models/Elevaretinyllma"
os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

try:
    from agents.content_creator.brand_guidelines_manager import BrandGuidelinesManager
    from agents.content_creator.text_generator import TextGenerator
    
    print("  Initializing BrandGuidelinesManager...")
    brand_manager = BrandGuidelinesManager()
    print("  ✓ BrandGuidelinesManager initialized")
    
    print("  Initializing TextGenerator (this may take a minute to load model)...")
    text_gen = TextGenerator(brand_manager=brand_manager)
    print("  ✓ TextGenerator initialized")
    
    if hasattr(text_gen, 'use_direct_model') and text_gen.use_direct_model:
        print("  ✓ Using direct PEFT model (offline mode)")
        if text_gen.model_obj is not None:
            print("  ✓ Model loaded successfully!")
        else:
            print("  ⚠ Model object is None")
    else:
        print(f"  ⚠ Using HTTP endpoint: {text_gen.local_llm_endpoint}")
    
    print("")
    print("  ✓ All tests passed!")
    
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYTHON_EOF

echo ""
echo "=== Test Complete ==="
