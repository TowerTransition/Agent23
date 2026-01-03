#!/usr/bin/env python3
"""
Simple test script to test text generation without social media APIs.
Run this in your SSH session to test the ContentCreatorAgent.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

print("=" * 60)
print("Testing Content Creator Agent - Text Generation Only")
print("=" * 60)
print()

# Check LLM endpoint
llm_endpoint = os.getenv('LOCAL_LLM_ENDPOINT', 'http://localhost:11434/v1/chat/completions')
print(f"LLM Endpoint: {llm_endpoint}")

# Set it in environment if not already set (for TextGenerator)
if not os.getenv('LOCAL_LLM_ENDPOINT'):
    os.environ['LOCAL_LLM_ENDPOINT'] = llm_endpoint
    print(f"Set LOCAL_LLM_ENDPOINT to: {llm_endpoint}")
print()

# Test LLM connection first - try both OpenAI-compatible and Ollama native endpoints
print("Step 1: Testing LLM Connection...")
try:
    import requests
    
    # First try OpenAI-compatible endpoint
    test_response = requests.post(
        llm_endpoint,
        json={
            'model': 'tinyllama',
            'messages': [{'role': 'user', 'content': 'Say OK if you can hear me.'}],
            'max_tokens': 10
        },
        timeout=10
    )
    
    if test_response.status_code == 200:
        print("✓ LLM connection successful (OpenAI-compatible endpoint)!")
        response_text = test_response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"  Response: {response_text}")
    else:
        # Try Ollama native endpoint
        print(f"  OpenAI-compatible endpoint returned {test_response.status_code}, trying Ollama native API...")
        ollama_endpoint = llm_endpoint.replace('/v1/chat/completions', '/api/chat')
        test_response = requests.post(
            ollama_endpoint,
            json={
                'model': 'tinyllama',
                'messages': [{'role': 'user', 'content': 'Say OK if you can hear me.'}],
                'stream': False
            },
            timeout=10
        )
        
        if test_response.status_code == 200:
            print("✓ LLM connection successful (Ollama native endpoint)!")
            response_text = test_response.json().get('message', {}).get('content', '')
            print(f"  Response: {response_text}")
            # Update endpoint to use Ollama native API
            os.environ['LOCAL_LLM_ENDPOINT'] = ollama_endpoint
            print(f"  Updated LOCAL_LLM_ENDPOINT to: {ollama_endpoint}")
        else:
            print(f"✗ LLM connection failed: {test_response.status_code}")
            print(f"  Error: {test_response.text}")
            print("\n  Troubleshooting:")
            print("  1. Make sure Ollama is running: ollama serve")
            print("  2. Check if model is available: ollama list")
            print("  3. Try pulling the model: ollama pull tinyllama")
            sys.exit(1)
        
except requests.exceptions.ConnectionError:
    print("✗ Cannot connect to LLM server!")
    print("  Make sure Ollama is running: ollama serve")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)

print()

# Test Content Creator Agent
print("Step 2: Testing Content Creator Agent...")
try:
    from agents.content_creator.content_creator_agent import ContentCreatorAgent
    
    # Initialize the agent (disable image generation since we don't have API key)
    agent = ContentCreatorAgent(
        brand_guidelines_path='agents/content_creator/example_brand_guidelines.json',
        image_generation_enabled=False  # Disable since we don't have Stability API key
    )
    print("✓ ContentCreatorAgent initialized (image generation disabled)")
    
except Exception as e:
    print(f"✗ Failed to initialize agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Create multiple mock trend data with different topics
print("Step 3: Creating mock trend data with different topics...")
mock_trends = [
    {
        'title': 'AI Transforming Healthcare Diagnosis',
        'description': 'AI-powered diagnostic tools are helping doctors detect diseases earlier and more accurately',
        'hashtags': ['AIHealthcare', 'MedicalAI', 'HealthTech'],
        'platform': 'all',
        'engagement': 5000,
        'trending': True
    },
    {
        'title': 'Machine Learning in Climate Solutions',
        'description': 'ML algorithms are optimizing renewable energy systems and reducing carbon emissions',
        'hashtags': ['ClimateTech', 'GreenAI', 'Sustainability'],
        'platform': 'all',
        'engagement': 4500,
        'trending': True
    },
    {
        'title': 'AI-Powered Education Platforms',
        'description': 'Personalized learning systems using AI are revolutionizing how students learn',
        'hashtags': ['EdTech', 'AIEducation', 'LearningTech'],
        'platform': 'all',
        'engagement': 3800,
        'trending': True
    },
    {
        'title': 'Automated Business Process Optimization',
        'description': 'AI is streamlining supply chains and automating business operations',
        'hashtags': ['BusinessAI', 'Automation', 'SupplyChain'],
        'platform': 'all',
        'engagement': 4200,
        'trending': True
    }
]
print(f"✓ Created {len(mock_trends)} different trend topics")
for i, trend in enumerate(mock_trends, 1):
    print(f"  {i}. {trend['title']}")
print()

# Generate content for each trend
print("Step 4: Generating content for all platforms...")
print("-" * 60)

all_results = {}

for trend_idx, mock_trend in enumerate(mock_trends, 1):
    print(f"\n{'='*60}")
    print(f"TREND {trend_idx}: {mock_trend['title']}")
    print(f"{'='*60}")
    
    try:
        content = agent.generate_multi_platform_content(
            trend_data=mock_trend,
            platforms=['twitter', 'instagram', 'linkedin']  # Removed facebook for now
        )
        
        all_results[mock_trend['title']] = content
        
        # Display generated content for this trend
        for platform, post_data in content.items():
            print(f"\n--- {platform.upper()} ---")
            
            # Check for errors first
            if 'error' in post_data:
                print(f"✗ Error: {post_data['error']}")
                continue
            
            # Get text content (different keys for different platforms)
            text = post_data.get('text', '') or post_data.get('caption', '') or post_data.get('content', '')
            if text:
                print(text[:200] + ('...' if len(text) > 200 else ''))
            else:
                print("⚠ No text content generated")
        
    except Exception as e:
        print(f"✗ Error generating content for trend {trend_idx}: {e}")
        import traceback
        traceback.print_exc()

print()
print("=" * 60)
print("✓ TEST COMPLETE!")
print("=" * 60)
print(f"Generated content for {len(all_results)} trends across multiple platforms")
print()
