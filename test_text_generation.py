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
    
    # Initialize the agent
    agent = ContentCreatorAgent(
        brand_guidelines_path='agents/content_creator/example_brand_guidelines.json'
    )
    print("✓ ContentCreatorAgent initialized")
    
except Exception as e:
    print(f"✗ Failed to initialize agent: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print()

# Create mock trend data
print("Step 3: Creating mock trend data...")
mock_trends = {
    'twitter': [
        {'hashtag': '#AIHealthcare', 'volume': 5000, 'description': 'AI applications in healthcare trending'}
    ],
    'instagram': [
        {'hashtag': '#MachineLearning', 'volume': 3000, 'description': 'Machine learning innovations'}
    ],
    'linkedin': [
        {'topic': 'AI in Business', 'engagement': 2000, 'description': 'AI transforming business operations'}
    ],
    'facebook': [
        {'topic': 'AI Solving Real-World Problems', 'engagement': 5000, 'description': 'AI helping solve climate change'}
    ]
}
print("✓ Mock trend data created")
print()

# Generate content
print("Step 4: Generating content for all platforms...")
print("-" * 60)
try:
    content = agent.create_content(
        trend_data=mock_trends,
        platforms=['twitter', 'instagram', 'linkedin', 'facebook']
    )
    
    print(f"\n✓ Successfully generated {len(content)} posts!")
    print()
    
    # Display generated content
    for platform, post_data in content.items():
        print("=" * 60)
        print(f"PLATFORM: {platform.upper()}")
        print("=" * 60)
        
        text = post_data.get('text', '')
        if text:
            print("\nGenerated Text:")
            print("-" * 60)
            print(text)
            print("-" * 60)
        
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

