#!/usr/bin/env python3
"""
Generate Sample Posts for Facebook, Instagram, and LinkedIn
Uses the Elevare fine-tuned PEFT model

Usage on GCP:
    cd ~/Agent23
    source venv/bin/activate  # if you have a venv
    python generate_sample_posts.py
"""

import os
import sys
from pathlib import Path

# Set environment variables BEFORE importing the generator
os.environ["PEFT_ADAPTER_PATH"] = "/home/amaziahy80/LLM_VAULT/Elevaretinyllma"
os.environ["BASE_MODEL_NAME"] = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

# Add Agent23 to path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    print("=" * 70)
    print("  ELEVARE BY AMAZIAH - SAMPLE POST GENERATOR")
    print("  Fine-tuned PEFT Model Test")
    print("=" * 70)
    print(f"\nPEFT Adapter: {os.environ['PEFT_ADAPTER_PATH']}")
    print(f"Base Model: {os.environ['BASE_MODEL_NAME']}")

    # Import after setting env vars
    print("\n[1/2] Loading fine-tuned model...")
    try:
        from agents.content_creator.text_generator import TextGenerator
        generator = TextGenerator()
        print(f"      Model loaded successfully!")
        print(f"      Using direct PEFT model: {generator.use_direct_model}")
    except Exception as e:
        print(f"      ERROR loading model: {e}")
        print("\n      Make sure you have installed:")
        print("        pip install peft transformers torch")
        sys.exit(1)

    # Sample contexts for each trained domain
    test_contexts = [
        {
            "domain": "Foreclosures",
            "title": "AI helps homeowners navigate foreclosure timelines",
            "description": "Coordinating document deadlines and process steps without legal advice"
        },
        {
            "domain": "Trading Futures",
            "title": "AI supports disciplined trading execution",
            "description": "Maintaining focus and structure during fast-moving markets"
        },
        {
            "domain": "Assisted Living",
            "title": "AI helps families compare senior care options",
            "description": "Organizing facility information for confident decisions"
        },
    ]

    platforms = ["facebook", "instagram", "linkedin"]

    print("\n[2/2] Generating sample posts...\n")

    for ctx in test_contexts:
        print("=" * 70)
        print(f"  DOMAIN: {ctx['domain'].upper()}")
        print(f"  Topic: {ctx['title']}")
        print("=" * 70)

        for platform in platforms:
            print(f"\n{'─' * 50}")
            print(f"  {platform.upper()}")
            print(f"{'─' * 50}")

            try:
                result = generator.generate_text(ctx, platform)
                print(result["text"])
                print(f"\n  Hashtags: {' '.join(result['hashtags'])}")
            except Exception as e:
                print(f"  ERROR: {e}")

        print()

    print("=" * 70)
    print("  GENERATION COMPLETE")
    print("=" * 70)
    print("\nTo post these to social media, use:")
    print("  python test_n8n_platforms.py")
    print()


if __name__ == "__main__":
    main()
