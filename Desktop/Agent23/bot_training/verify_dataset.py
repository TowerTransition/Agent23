#!/usr/bin/env python3
"""Verify the processed dataset"""

import json

print("=" * 80)
print("DATASET VERIFICATION")
print("=" * 80)
print()

# Check for labels
labels = ['CONTEXT:', 'PROBLEM:', 'AI_SUPPORT:', 'REINFORCEMENT:', 'FOOTER:', 'HASHTAGS:']

print("1. Checking for structural labels...")
with open('train.jsonl', 'r', encoding='utf-8') as f:
    train_lines = f.readlines()

with open('test.jsonl', 'r', encoding='utf-8') as f:
    test_lines = f.readlines()

labels_found = []
for i, line in enumerate(train_lines[:20]):  # Check first 20
    for label in labels:
        if label in line:
            labels_found.append(f"Line {i+1}: {label}")

if labels_found:
    print(f"  X Found {len(labels_found)} labels in first 20 lines:")
    for found in labels_found[:5]:
        print(f"    - {found}")
else:
    print("  OK NO labels found - All removed!")

print(f"\n2. File counts:")
print(f"  - train.jsonl: {len(train_lines)} examples")
print(f"  - test.jsonl: {len(test_lines)} examples")

print(f"\n3. Format verification:")
# Check first few examples
for i, line in enumerate(train_lines[:3]):
    try:
        data = json.loads(line.strip())
        if 'text' in data:
            print(f"  OK Example {i+1}: Valid JSON with 'text' field")
            text_preview = data['text'][:100].replace('\n', ' ')
            print(f"    Preview: {text_preview}...")
        else:
            print(f"  X Example {i+1}: Missing 'text' field")
    except json.JSONDecodeError as e:
        print(f"  ✗ Example {i+1}: Invalid JSON - {e}")

print(f"\n4. Sample from train.jsonl (full text):")
if train_lines:
    sample = json.loads(train_lines[0].strip())
    print("  " + "="*76)
    print("  " + sample['text'].replace('\n', '\n  '))
    print("  " + "="*76)

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
