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

# Test LLM connection first
print("Step 1: Testing LLM Connection...")
try:
    import requests
    
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
        print("✓ LLM connection successful!")
        response_text = test_response.json().get('choices', [{}])[0].get('message', {}).get('content', '')
        print(f"  Response: {response_text}")
    else:
        print(f"✗ LLM connection failed: {test_response.status_code}")
        print(f"  Error: {test_response.text}")
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

# Create mock trend data (single trend that will be used for all platforms)
print("Step 3: Creating mock trend data...")
mock_trend = {
    'title': 'AI Solving Real-World Healthcare Problems',
    'description': 'AI applications in healthcare are revolutionizing patient care and medical diagnosis',
    'hashtags': ['AIHealthcare', 'MachineLearning', 'HealthTech', 'AIforGood'],
    'platform': 'all',
    'engagement': 5000,
    'trending': True
}
print("✓ Mock trend data created")
print(f"  Title: {mock_trend['title']}")
print(f"  Hashtags: {', '.join(mock_trend['hashtags'])}")
print()

# Generate content
print("Step 4: Generating content for all platforms...")
print("-" * 60)
try:
    content = agent.generate_multi_platform_content(
        trend_data=mock_trend,
        platforms=['twitter', 'instagram', 'linkedin', 'facebook']
    )
    
    print(f"\n✓ Successfully generated {len(content)} posts!")
    print()
    
    # Display generated content
    for platform, post_data in content.items():
        print("=" * 60)
        print(f"PLATFORM: {platform.upper()}")
        print("=" * 60)
        
        # Check for errors first
        if 'error' in post_data:
            print(f"\n✗ Error: {post_data['error']}")
            print()
            continue
        
        # Get text content (different keys for different platforms)
        text = post_data.get('text', '') or post_data.get('caption', '') or post_data.get('content', '')
        if text:
            print("\nGenerated Text:")
            print("-" * 60)
            print(text)
            print("-" * 60)
        else:
            print("\n⚠ No text content generated")
        
        # Show hashtags if available
        hashtags = post_data.get('hashtags', [])
        if hashtags:
            print(f"\nHashtags: {', '.join(hashtags)}")
        
        # Show image prompt if available
        image_prompt = post_data.get('image_prompt', '')
        if image_prompt:
            print(f"\nImage Prompt: {image_prompt}")
        
        print()
    
    print("=" * 60)
    print("✓ TEST COMPLETE - All content generated successfully!")
    print("=" * 60)
    
except Exception as e:
    print(f"✗ Error generating content: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

