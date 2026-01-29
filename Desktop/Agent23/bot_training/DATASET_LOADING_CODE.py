"""
Complete dataset loading code for the training notebook.
Replace the old dataset loading cell with this code.
"""

import json
from datasets import Dataset

# Load training data from JSONL file
def load_jsonl(file_path):
    """Load data from a JSONL file"""
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                data.append(json.loads(line))
    return data

# Convert instruction/input/output format to messages format for SFT trainer
def convert_to_messages_format(example):
    """Convert instruction/input/output format to messages format"""
    # Combine instruction and input into user message
    user_content = example['instruction']
    if example.get('input'):
        user_content += f"\n\n{example['input']}"
    
    # Create messages in the format expected by SFT trainer
    messages = [
        {
            "role": "system",
            "content": "You are a helpful AI assistant that writes Facebook posts following specific instructions and brand guidelines."
        },
        {
            "role": "user",
            "content": user_content
        },
        {
            "role": "assistant",
            "content": example['output']
        }
    ]
    
    return {"messages": messages}

# Load training dataset
print("Loading training data from train.jsonl...")
train_data = load_jsonl("train.jsonl")
print(f"Loaded {len(train_data)} training examples")

# Convert to messages format
train_data_formatted = [convert_to_messages_format(ex) for ex in train_data]

# Create HuggingFace Dataset
train_dataset = Dataset.from_list(train_data_formatted)

print(f"✓ Training dataset created with {len(train_dataset)} examples")
print(f"✓ Dataset features: {list(train_dataset.features.keys())}")
print(f"\nExample from dataset:")
print(train_dataset[0])
