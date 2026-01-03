#!/usr/bin/env python3
"""
Quick test to check which endpoint works with your local Ollama setup.
"""

import requests
import os
from dotenv import load_dotenv

load_dotenv()

endpoint = os.getenv('LOCAL_LLM_ENDPOINT', 'http://localhost:11434/v1/chat/completions')

print("=" * 60)
print("Testing Local LLM Endpoints")
print("=" * 60)
print()

# Test 1: OpenAI-compatible endpoint
print("Test 1: OpenAI-compatible endpoint")
print(f"  URL: http://localhost:11434/v1/chat/completions")
try:
    response = requests.post(
        'http://localhost:11434/v1/chat/completions',
        json={
            'model': 'tinyllama',
            'messages': [{'role': 'user', 'content': 'test'}],
            'max_tokens': 5
        },
        timeout=5
    )
    if response.status_code == 200:
        print("  ✓ OpenAI-compatible endpoint WORKS!")
        print(f"  Response: {response.json().get('choices', [{}])[0].get('message', {}).get('content', '')[:50]}")
    else:
        print(f"  ✗ Status: {response.status_code}")
        print(f"  Response: {response.text[:100]}")
except requests.exceptions.ConnectionError:
    print("  ✗ Cannot connect - is Ollama running?")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()

# Test 2: Ollama native endpoint
print("Test 2: Ollama native endpoint")
print(f"  URL: http://localhost:11434/api/chat")
try:
    response = requests.post(
        'http://localhost:11434/api/chat',
        json={
            'model': 'tinyllama',
            'messages': [{'role': 'user', 'content': 'test'}],
            'stream': False
        },
        timeout=5
    )
    if response.status_code == 200:
        print("  ✓ Ollama native endpoint WORKS!")
        print(f"  Response: {response.json().get('message', {}).get('content', '')[:50]}")
    else:
        print(f"  ✗ Status: {response.status_code}")
        print(f"  Response: {response.text[:100]}")
except requests.exceptions.ConnectionError:
    print("  ✗ Cannot connect - is Ollama running?")
except Exception as e:
    print(f"  ✗ Error: {e}")

print()
print("=" * 60)
print("Summary:")
print("  - If Test 1 works: Use OpenAI-compatible endpoint")
print("  - If Test 1 fails but Test 2 works: Code will auto-fallback")
print("  - Both work the same, just different formats")
print("=" * 60)

