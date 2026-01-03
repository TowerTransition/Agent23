#!/bin/bash
# Script to set up vLLM server on Google Cloud VM
# Run this on your LLM server VM

set -e

echo "=========================================="
echo "Setting up vLLM Server on Google Cloud"
echo "=========================================="

# Update system
echo "Updating system packages..."
sudo apt-get update
sudo apt-get install -y python3-pip python3-venv git

# Install NVIDIA drivers if GPU is available
if lspci | grep -i nvidia > /dev/null; then
    echo "GPU detected. Installing NVIDIA drivers..."
    sudo apt-get install -y nvidia-driver-535
    echo "NVIDIA drivers installed. Please reboot: sudo reboot"
fi

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install vLLM
echo "Installing vLLM..."
pip install vllm

# Create systemd service for vLLM
echo "Creating systemd service..."
sudo tee /etc/systemd/system/vllm.service > /dev/null <<EOF
[Unit]
Description=vLLM OpenAI-Compatible API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME
Environment="PATH=$HOME/venv/bin"
ExecStart=$HOME/venv/bin/python -m vllm.entrypoints.openai.api_server \\
    --model meta-llama/Llama-2-7b-chat-hf \\
    --host 0.0.0.0 \\
    --port 8000 \\
    --trust-remote-code
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

echo "Setup complete!"
echo ""
echo "To start vLLM server:"
echo "  sudo systemctl start vllm"
echo "  sudo systemctl enable vllm  # Auto-start on boot"
echo ""
echo "To check status:"
echo "  sudo systemctl status vllm"
echo ""
echo "To view logs:"
echo "  sudo journalctl -u vllm -f"

