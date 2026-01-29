"""
Generate a real Facebook post for each trained domain using the live model.

This script tests the training-aligned format:
- 4-6 sentences ending with STATEMENT (not question)
- Footer: "Real-world systems. Real clarity." + "— Elevare by Amaziah"
- Exactly 4 hashtags

Run:
    PYTHONPATH=. python3 simulate_facebook_post.py
"""

import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)
logger = logging.getLogger("SimulateFacebookPost")

from agents.content_creator.text_generator import TextGenerator

# ---------------------------------------------------------------------------
# Test domains (from training data)
# ---------------------------------------------------------------------------

DOMAINS = [
    {
        "domain": "Foreclosures",
        "title": "Coordinating foreclosure information across parties",
        "description": "When information isn't coordinated, small details fall through the cracks and stress compounds.",
    },
    {
        "domain": "Trading Futures",
        "title": "Maintaining execution discipline in fast markets",
        "description": "When speed increases, skipped steps and emotional reactions become more likely.",
    },
    {
        "domain": "Assisted Living",
        "title": "Helping families compare assisted living options",
        "description": "When families don't understand environments and care models, uncertainty rises.",
    },
]


def main():
    print("=" * 70)
    print("  MODEL CONFIGURATION")
    print("=" * 70)
    peft = os.environ.get("PEFT_ADAPTER_PATH", "(not set)")
    endpoint = os.environ.get("LOCAL_LLM_ENDPOINT", "(not set)")
    model_name = os.environ.get("LOCAL_LLM_MODEL", "(not set)")
    allow_default = os.environ.get("ALLOW_DEFAULT_LLM_ENDPOINT", "(not set)")
    print(f"  PEFT_ADAPTER_PATH           : {peft}")
    print(f"  LOCAL_LLM_ENDPOINT          : {endpoint}")
    print(f"  LOCAL_LLM_MODEL             : {model_name}")
    print(f"  ALLOW_DEFAULT_LLM_ENDPOINT  : {allow_default}")
    print()

    try:
        gen = TextGenerator()
    except ValueError as e:
        print(f"ERROR: {e}")
        print()
        print("Set one of the following before running:")
        print("  export PEFT_ADAPTER_PATH=/path/to/Elevaretinyllma")
        print("  export LOCAL_LLM_ENDPOINT=http://localhost:11434/v1/chat/completions")
        print("  export ALLOW_DEFAULT_LLM_ENDPOINT=true")
        sys.exit(1)

    mode = "PEFT direct" if gen.use_direct_model else f"HTTP endpoint ({gen.local_llm_endpoint})"
    print(f"  Active mode: {mode}")
    print()
    print("  EXPECTED OUTPUT FORMAT (training-aligned):")
    print("    - 4-6 sentences ending with STATEMENT (not question)")
    print("    - Footer: 'Real-world systems. Real clarity.'")
    print("    - Signature: '— Elevare by Amaziah'")
    print("    - Exactly 4 hashtags")
    print()

    for ctx in DOMAINS:
        print("=" * 70)
        print(f"  DOMAIN   : {ctx['domain']}")
        print(f"  PLATFORM : facebook")
        print("=" * 70)

        try:
            result = gen.generate_text(context=ctx, platform="facebook")
            print()
            print(result["text"])
            print()
            print(f"  hashtags : {result['hashtags']} (count: {len(result['hashtags'])})")
            print(f"  mode     : {'PEFT direct' if result['meta']['used_direct_model'] else 'HTTP endpoint'}")

            # Validation checks
            text = result["text"]
            checks = []

            # Check for statement ending (not question)
            body_end = text.split("Real-world systems.")[0].strip() if "Real-world systems." in text else text
            if body_end.rstrip().endswith("?"):
                checks.append("WARN: Body ends with question (should be statement)")
            else:
                checks.append("OK: Body ends with statement")

            # Check for tagline
            if "Real-world systems. Real clarity." in text:
                checks.append("OK: Tagline present")
            else:
                checks.append("WARN: Tagline missing")

            # Check for signature
            if "— Elevare by Amaziah" in text:
                checks.append("OK: Signature present")
            else:
                checks.append("WARN: Signature missing")

            # Check hashtag count
            if len(result['hashtags']) == 4:
                checks.append("OK: Exactly 4 hashtags")
            else:
                checks.append(f"WARN: {len(result['hashtags'])} hashtags (expected 4)")

            print()
            print("  VALIDATION:")
            for check in checks:
                print(f"    {check}")

            if all("OK" in c for c in checks):
                print(f"\n  status   : PASS")
            else:
                print(f"\n  status   : PARTIAL (see warnings)")

        except Exception as e:
            print()
            print(f"  status   : FAIL")
            print(f"  error    : {e}")

        print()


if __name__ == "__main__":
    main()
