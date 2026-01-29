#!/usr/bin/env python3
"""
Process datasets: Remove labels, combine, deduplicate, shuffle, and split 90/10
"""

import json
import random
import os
import glob

def remove_labels(text):
    """Remove structural labels while keeping text content and line breaks"""
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append('')
            continue
        
        # Remove labels: CONTEXT:, PROBLEM:, AI_SUPPORT:, REINFORCEMENT:, FOOTER:, HASHTAGS:
        for label in ['CONTEXT:', 'PROBLEM:', 'AI_SUPPORT:', 'REINFORCEMENT:', 'FOOTER:', 'HASHTAGS:']:
            if line.startswith(label):
                # Remove label and keep the content
                content = line[len(label):].strip()
                if content:
                    cleaned_lines.append(content)
                break
        else:
            # No label found, keep the line as-is
            if line:
                cleaned_lines.append(line)
    
    # Join with line breaks and clean up multiple empty lines
    result = '\n'.join(cleaned_lines)
    # Remove excessive empty lines (more than 2 consecutive)
    while '\n\n\n' in result:
        result = result.replace('\n\n\n', '\n\n')
    
    return result.strip()

def extract_from_notebook(notebook_path):
    """Extract all data from a notebook file"""
    if not os.path.exists(notebook_path):
        return []
    
    with open(notebook_path, 'r', encoding='utf-8') as f:
        notebook = json.load(f)
    
    all_data = []
    for cell in notebook['cells']:
        source = cell.get('source', [])
        if isinstance(source, list):
            content = ''.join(source)
        else:
            content = source
        
        # Split by lines and parse JSON objects
        for line in content.split('\n'):
            line = line.strip()
            if line and line.startswith('{'):
                try:
                    data = json.loads(line)
                    all_data.append(data)
                except json.JSONDecodeError:
                    continue
    
    return all_data

def load_all_jsonl_files():
    """Load all JSONL files and notebook files in the directory"""
    jsonl_files = glob.glob('*.jsonl')
    notebook_files = ['2.train.ipynb', '2test.ipynb', 'Train.ipynb', 'test.ipynb']
    
    print(f"Found JSONL files: {jsonl_files}")
    print(f"Found notebook files: {[f for f in notebook_files if os.path.exists(f)]}")
    
    all_data = []
    
    # Load JSONL files
    for file_path in jsonl_files:
        print(f"\nLoading {file_path}...")
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    all_data.append(data)
                except json.JSONDecodeError as e:
                    print(f"  Warning: Skipping invalid JSON in {file_path} line {line_num}: {e}")
                    continue
    
    # Extract from notebooks
    for notebook_path in notebook_files:
        if os.path.exists(notebook_path):
            print(f"\nExtracting from {notebook_path}...")
            notebook_data = extract_from_notebook(notebook_path)
            all_data.extend(notebook_data)
            print(f"  Extracted {len(notebook_data)} examples")
    
    return all_data

def normalize_text(data):
    """Normalize data to have a 'text' field"""
    if 'text' in data:
        return {'text': data['text']}
    elif 'output' in data:
        return {'text': data['output']}
    elif 'instruction' in data and 'output' in data:
        # Combine instruction and output
        text = data.get('instruction', '')
        if data.get('input'):
            text += '\n\n' + data['input']
        if data.get('output'):
            text += '\n\n' + data['output']
        return {'text': text}
    else:
        # Try to use the first string value
        for key, value in data.items():
            if isinstance(value, str):
                return {'text': value}
        return None

# Load all JSONL files
print("=" * 80)
print("PROCESSING DATASETS")
print("=" * 80)
print()

all_data = load_all_jsonl_files()
print(f"\nTotal examples loaded: {len(all_data)}")

# Normalize to text format
print("\nNormalizing to text format...")
normalized_data = []
for item in all_data:
    normalized = normalize_text(item)
    if normalized:
        normalized_data.append(normalized)

print(f"Normalized examples: {len(normalized_data)}")

# Remove labels and clean text
print("\nRemoving structural labels...")
cleaned_data = []
for item in normalized_data:
    cleaned_text = remove_labels(item['text'])
    if cleaned_text:  # Only keep non-empty text
        cleaned_data.append({'text': cleaned_text})

print(f"Cleaned examples: {len(cleaned_data)}")

# Remove exact duplicates
print("\nRemoving duplicates...")
seen = set()
unique_data = []
for item in cleaned_data:
    text = item['text']
    if text not in seen:
        seen.add(text)
        unique_data.append(item)

print(f"Unique examples: {len(unique_data)}")
print(f"Duplicates removed: {len(cleaned_data) - len(unique_data)}")

# Shuffle
print("\nShuffling data...")
random.seed(42)
random.shuffle(unique_data)

# 90/10 split
split_idx = int(len(unique_data) * 0.9)
train_split = unique_data[:split_idx]
test_split = unique_data[split_idx:]

print(f"\n90/10 Split:")
print(f"  Training: {len(train_split)} examples ({len(train_split)/len(unique_data)*100:.1f}%)")
print(f"  Test: {len(test_split)} examples ({len(test_split)/len(unique_data)*100:.1f}%)")

# Write to JSONL files
print("\nWriting train.jsonl and test.jsonl...")
with open('train.jsonl', 'w', encoding='utf-8') as f:
    for item in train_split:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

with open('test.jsonl', 'w', encoding='utf-8') as f:
    for item in test_split:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"\nFiles created:")
print(f"  - train.jsonl: {len(train_split)} examples")
print(f"  - test.jsonl: {len(test_split)} examples")

# Show sample
print(f"\nSample from train.jsonl:")
if train_split:
    sample = json.dumps(train_split[0], ensure_ascii=False, indent=2)
    print(sample[:500] + "..." if len(sample) > 500 else sample)

print("\n" + "=" * 80)
print("PROCESSING COMPLETE")
print("=" * 80)
