#!/usr/bin/env python3
"""
Fine-tune TinyLlama with LoRA/QLoRA using TRL
This script trains the model on local JSONL datasets
"""

import json
import os
import torch
from datasets import Dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig
from trl import SFTConfig, SFTTrainer
from huggingface_hub import model_info

# ============================================================================
# CONFIGURATION
# ============================================================================

# Model configuration
model_id = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
output_dir = "Elevaretinyllma"  # Name for the fine-tuned model

# Dataset files
train_file = "train.jsonl"
test_file = "test.jsonl"

print("=" * 80)
print("FINE-TUNING TINYLLAMA WITH LORA/QLORA")
print("=" * 80)
print()
print(f"Model: {model_id}")
print(f"Output: {output_dir}")
print()

# ============================================================================
# LOAD DATASET
# ============================================================================

def load_jsonl(file_path):
    """Load data from a JSONL file"""
    data = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:  # utf-8-sig handles BOM
        for line in f:
            line = line.strip()
            if line:
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError as e:
                    print(f"Warning: Skipping invalid JSON line: {e}")
                    continue
    return data

def convert_to_messages_format(example):
    """Convert to messages format - handles both text-only and instruction/input/output formats"""
    messages = []
    
    # Handle simple text format (new format)
    if 'text' in example and not example.get('instruction'):
        # Extract the text content
        text_content = example['text']
        
        # Parse the text to extract components (if structured)
        # The text should start with the main content, then AI_SUPPORT, REINFORCEMENT, FOOTER, HASHTAGS
        lines = text_content.split('\n')
        
        # Create a prompt that explicitly requires reproducing the text
        system_prompt = """You are a helpful assistant that writes Facebook posts for Elevare by Amaziah. 
When given a text block, you must start your response by reproducing that text EXACTLY as provided, then continue with the rest of the post format."""
        
        user_prompt = f"""Write a Facebook post. Start by reproducing this text EXACTLY:

{text_content}

Then continue with the complete post following the Elevare brand style."""
        
        messages.append({
            'role': 'system',
            'content': system_prompt
        })
        messages.append({
            'role': 'user',
            'content': user_prompt
        })
        messages.append({
            'role': 'assistant',
            'content': text_content  # Expected output is the full text
        })
    
    # Handle instruction/input/output format (old format)
    elif example.get('instruction'):
        system_content = example['instruction']
        if example.get('input'):
            system_content += f"\n\n{example['input']}"
        messages.append({
            'role': 'system',
            'content': system_content
        })
        
        user_content = example.get('instruction', '')
        if example.get('input'):
            user_content += f"\n\n{example['input']}"
        messages.append({
            'role': 'user',
            'content': user_content
        })
        
        if example.get('output'):
            messages.append({
                'role': 'assistant',
                'content': example['output']
            })
    
    else:
        # Fallback
        messages.append({
            'role': 'system',
            'content': 'You are a helpful assistant.'
        })
        messages.append({
            'role': 'user',
            'content': 'Write a Facebook post.'
        })
        if 'text' in example:
            messages.append({
                'role': 'assistant',
                'content': example['text']
            })
    
    return {"messages": messages}

print("Loading training dataset...")
if not os.path.exists(train_file):
    raise FileNotFoundError(f"Training file not found: {train_file}")

train_data = load_jsonl(train_file)
print(f"✓ Loaded {len(train_data)} training examples")

# Convert to messages format
train_data_formatted = [convert_to_messages_format(ex) for ex in train_data]
train_dataset = Dataset.from_list(train_data_formatted)
print(f"✓ Training dataset created with {len(train_dataset)} examples")
print()

# Load test dataset (optional)
test_dataset = None
if os.path.exists(test_file):
    print("Loading test dataset...")
    test_data = load_jsonl(test_file)
    test_data_formatted = [convert_to_messages_format(ex) for ex in test_data]
    test_dataset = Dataset.from_list(test_data_formatted)
    print(f"✓ Test dataset created with {len(test_dataset)} examples")
    print()
else:
    print(f"⚠️ Test file not found: {test_file} (skipping test dataset)")
    print()

# ============================================================================
# VERIFY MODEL AVAILABILITY
# ============================================================================

print("Verifying model availability...")
try:
    info = model_info(model_id)
    print(f"✓ Model found on Hugging Face Hub!")
    print(f"  - Model ID: {model_id}")
    print(f"  - Model Card: https://huggingface.co/{model_id}")
    print()
except Exception as e:
    print(f"⚠️ Could not fetch model info: {e}")
    print(f"  Model will be downloaded when loading...")
    print()

# ============================================================================
# LOAD MODEL WITH QLORA
# ============================================================================

print("Loading model with QLoRA configuration...")
print("This may take a few minutes to download the model...")

model = AutoModelForCausalLM.from_pretrained(
    model_id,
    attn_implementation="sdpa",
    dtype=torch.float16,
    use_cache=True,
    quantization_config=BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4"
    )
)

print("✓ Model loaded successfully")
print()

# ============================================================================
# CONFIGURE LORA
# ============================================================================

print("Configuring LoRA...")
peft_config = LoraConfig(
    r=32,
    lora_alpha=32,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
)

print("✓ LoRA configuration created")
print()

# ============================================================================
# CONFIGURE TRAINING
# ============================================================================

print("Configuring training parameters...")
training_args = SFTConfig(
    # Training schedule / optimization
    per_device_train_batch_size=1,
    gradient_accumulation_steps=4,
    warmup_steps=5,
    max_steps=30,
    learning_rate=2e-4,
    optim="paged_adamw_8bit",

    # Logging / reporting
    logging_steps=1,
    report_to="none",  # Disable trackio to avoid Hugging Face login requirement
    output_dir=output_dir,

    max_length=1024,
    use_liger_kernel=True,
    activation_offloading=True,
    gradient_checkpointing=True,

    # Hub integration
    push_to_hub=False,  # Set to True if you want to push to Hub (requires login)

    gradient_checkpointing_kwargs={"use_reentrant": False},
)

print("✓ Training configuration created")
print()

# ============================================================================
# INITIALIZE TRAINER
# ============================================================================

print("Initializing trainer...")
tokenizer = AutoTokenizer.from_pretrained(model_id)
# Set pad_token if it doesn't exist
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token

trainer = SFTTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    peft_config=peft_config,
)
# Note: tokenizer is loaded above for use in testing later
# SFTTrainer uses the model's tokenizer automatically

print("✓ Trainer initialized")
print()

# ============================================================================
# TRAIN MODEL
# ============================================================================

print("=" * 80)
print("STARTING TRAINING")
print("=" * 80)
print()

trainer_stats = trainer.train()

print()
print("=" * 80)
print("TRAINING COMPLETE")
print("=" * 80)
print()

# ============================================================================
# SAVE MODEL
# ============================================================================

print("Saving model...")
trainer.save_model(output_dir)
print(f"✓ Model saved to: {output_dir}")
print()

# ============================================================================
# TEST MODEL
# ============================================================================

if test_dataset is not None:
    print("=" * 80)
    print("TESTING MODEL")
    print("=" * 80)
    print()
    
    from peft import PeftModel
    
    # Load fine-tuned model - IMPORTANT: Load from base model, not the already-trained model
    # This prevents stacking multiple adapters
    print("Loading base model for testing...")
    base_model = AutoModelForCausalLM.from_pretrained(
        model_id,
        attn_implementation="sdpa",
        dtype=torch.float16,
        quantization_config=BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4"
        ),
        device_map="auto"
    )
    
    print("Loading fine-tuned adapter...")
    fine_tuned_model = PeftModel.from_pretrained(base_model, output_dir)
    fine_tuned_model.eval()  # Set to evaluation mode
    print("✓ Fine-tuned model loaded (single adapter)")
    
    # Ensure tokenizer is properly configured
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    print("✓ Tokenizer configured")
    print()
    
    # Function to identify domain
    def identify_domain(text):
        """Identify the domain from the text content"""
        text_lower = text.lower()
        if any(word in text_lower for word in ['foreclosure', 'homeowner', 'housing']):
            return 'Foreclosure'
        elif any(word in text_lower for word in ['trader', 'trading', 'futures', 'market']):
            return 'Trading'
        elif any(word in text_lower for word in ['assisted living', 'care', 'resident', 'operator']):
            return 'Assisted Living'
        else:
            return 'Other'
    
    # Function to run inference
    def test_model_on_example(model, tokenizer, example, max_new_tokens=512):
        """Run inference on a single test example"""
        messages = example['messages']
        inference_messages = [msg for msg in messages if msg['role'] in ['system', 'user']]
        
        # Build prompt with explicit instruction to reproduce text
        text = tokenizer.apply_chat_template(
            inference_messages, tokenize=False, add_generation_prompt=True
        )
        
        # Debug: Print the prompt being sent (first 500 chars)
        print(f"\n[DEBUG] Prompt sent to model (first 500 chars):")
        print(text[:500] + "..." if len(text) > 500 else text)
        print()
        
        model_inputs = tokenizer([text], return_tensors="pt").to(model.device)
        
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.3,  # Lower temperature for more deterministic output
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            repetition_penalty=1.1  # Prevent repetition
        )
        
        output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
        generated_text = tokenizer.decode(output_ids, skip_special_tokens=True)
        
        return generated_text
    
    # Load original test data for display
    test_data_original = load_jsonl(test_file)
    
    # Find one example from each domain
    domains_found = {'Foreclosure': None, 'Trading': None, 'Assisted Living': None}
    
    for i, example_original in enumerate(test_data_original):
        # Get text content (could be 'text' field or 'output' field)
        text_content = example_original.get('text', '') or example_original.get('output', '') or example_original.get('instruction', '')
        domain = identify_domain(text_content)
        if domain in domains_found and domains_found[domain] is None:
            domains_found[domain] = i
    
    # Test and display results
    results_shown = 0
    for domain, idx in domains_found.items():
        if idx is not None and results_shown < 3:
            print(f"\n{'='*80}")
            print(f"DOMAIN: {domain.upper()}")
            print(f"{'='*80}\n")
            
            # Get original example data
            original_example = test_data_original[idx]
            test_example = test_dataset[idx]
            
            # Display input
            if original_example.get('instruction'):
                print("INSTRUCTION:")
                print(f"   {original_example.get('instruction', 'N/A')}")
                if original_example.get('input'):
                    print(f"\nINPUT:")
                    print(f"   {original_example['input']}")
            else:
                print("TEXT:")
                text_preview = original_example.get('text', 'N/A')
                if len(text_preview) > 200:
                    text_preview = text_preview[:200] + "..."
                print(f"   {text_preview}")
            
            # Run inference
            print(f"\nGENERATING RESPONSE...")
            generated_output = test_model_on_example(fine_tuned_model, tokenizer, test_example)
            
            # Display generated output
            print(f"\nGENERATED OUTPUT:")
            print(f"   {generated_output}")
            
            # Display expected output (for comparison)
            expected = original_example.get('output') or original_example.get('text', '')
            if expected:
                print(f"\nEXPECTED OUTPUT:")
                if len(expected) > 500:
                    expected = expected[:500] + "..."
                print(f"   {expected}")
            
            results_shown += 1
            print()
    
    print("=" * 80)
    print("TESTING COMPLETE")
    print("=" * 80)
else:
    print("⚠️ Test dataset not available. Skipping testing.")

print()
print("=" * 80)
print("ALL DONE!")
print("=" * 80)
print(f"Fine-tuned model saved to: {output_dir}")
print("You can now use this model for inference!")
