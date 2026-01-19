#!/bin/bash
# Verify PEFT installation and test
# Run this on SSH: bash VERIFY_PEFT_INSTALL.sh

echo "=== Verifying PEFT Installation ==="
echo ""

echo "1. Checking installed packages..."
pip list | grep -E "(torch|transformers|peft)"
echo ""

echo "2. Testing imports..."
python3 -c "
try:
    import torch
    print(f'✓ torch {torch.__version__} installed')
    print(f'  CUDA available: {torch.cuda.is_available()}')
except ImportError as e:
    print(f'✗ torch not installed: {e}')

try:
    import transformers
    print(f'✓ transformers {transformers.__version__} installed')
except ImportError as e:
    print(f'✗ transformers not installed: {e}')

try:
    import peft
    print(f'✓ peft {peft.__version__} installed')
except ImportError as e:
    print(f'✗ peft not installed: {e}')
"
echo ""

echo "3. Checking Elevaretinyllma model..."
if [ -d ~/AGENT/models/Elevaretinyllma ]; then
    echo "✓ Elevaretinyllma found at ~/AGENT/models/Elevaretinyllma"
    du -sh ~/AGENT/models/Elevaretinyllma
    echo ""
    echo "Model contents:"
    ls -lh ~/AGENT/models/Elevaretinyllma/ | head -10
else
    echo "✗ Elevaretinyllma not found!"
fi
echo ""

echo "4. Current disk space:"
df -h | grep "/dev/sda1"
echo ""

echo "=== Next Steps ==="
echo ""
echo "1. Set environment variable:"
echo "   export PEFT_ADAPTER_PATH=\"/home/amaziahy80/AGENT/models/Elevaretinyllma\""
echo ""
echo "2. Test the PEFT adapter:"
echo "   python3 -c \"from agents.content_creator.text_generator import TextGenerator; print('Import successful')\""
echo ""
