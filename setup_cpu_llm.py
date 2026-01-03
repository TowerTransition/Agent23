#!/usr/bin/env python3
"""
Simple CPU-based LLM API server using Hugging Face Transformers
This runs a lightweight model on CPU for testing/development.

Usage:
    python setup_cpu_llm.py --model microsoft/DialoGPT-small --port 8000
"""

import argparse
import json
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

app = Flask(__name__)

# Global model and tokenizer
model = None
tokenizer = None
model_name = None


def load_model(name):
    """Load a Hugging Face model and tokenizer"""
    global model, tokenizer, model_name
    print(f"Loading model: {name}...")
    tokenizer = AutoTokenizer.from_pretrained(name)
    model = AutoModelForCausalLM.from_pretrained(
        name,
        torch_dtype=torch.float32,  # Use float32 for CPU
        device_map="cpu",
        low_cpu_mem_usage=True
    )
    model.eval()
    model_name = name
    print(f"Model {name} loaded successfully!")


@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    """OpenAI-compatible chat completions endpoint"""
    try:
        data = request.json
        messages = data.get('messages', [])
        model_name_param = data.get('model', model_name)
        temperature = data.get('temperature', 0.7)
        max_tokens = data.get('max_tokens', 200)
        
        # Convert messages to prompt
        prompt = ""
        for msg in messages:
            role = msg.get('role', 'user')
            content = msg.get('content', '')
            if role == 'system':
                prompt += f"System: {content}\n\n"
            elif role == 'user':
                prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n\n"
        prompt += "Assistant:"
        
        # Generate response
        inputs = tokenizer.encode(prompt, return_tensors='pt')
        
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                max_length=inputs.shape[1] + max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
        
        response_text = tokenizer.decode(outputs[0][inputs.shape[1]:], skip_special_tokens=True)
        
        # Format OpenAI-compatible response
        return jsonify({
            "id": "chatcmpl-cpu-llm",
            "object": "chat.completion",
            "created": 1234567890,
            "model": model_name_param,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }],
            "usage": {
                "prompt_tokens": inputs.shape[1],
                "completion_tokens": len(tokenizer.encode(response_text)),
                "total_tokens": inputs.shape[1] + len(tokenizer.encode(response_text))
            }
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "model": model_name if model else "not loaded"
    })


@app.route('/v1/models', methods=['GET'])
def list_models():
    """List available models"""
    return jsonify({
        "data": [{
            "id": model_name or "default",
            "object": "model",
            "created": 1234567890,
            "owned_by": "local"
        }]
    })


def main():
    parser = argparse.ArgumentParser(description='CPU-based LLM API server')
    parser.add_argument(
        '--model',
        type=str,
        default='microsoft/DialoGPT-small',
        help='Hugging Face model name (default: microsoft/DialoGPT-small)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000,
        help='Port to run server on (default: 8000)'
    )
    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    
    args = parser.parse_args()
    
    # Load model
    load_model(args.model)
    
    print(f"\nStarting LLM API server on {args.host}:{args.port}")
    print(f"Model: {args.model}")
    print(f"OpenAI-compatible endpoint: http://{args.host}:{args.port}/v1/chat/completions")
    print("\nPress Ctrl+C to stop\n")
    
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == '__main__':
    main()

