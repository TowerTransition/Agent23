# Run Training - Quick Commands

## You're in: `~/Training LLM` directory ✅

### Step 1: Verify Files
```bash
ls -la
```
Should show: `train_model.py`, `train.jsonl`, `test.jsonl`

### Step 2: Install Dependencies (if not already done)
```bash
pip3 install "trl[peft]" trackio bitsandbytes datasets transformers peft huggingface_hub accelerate
```

### Step 3: Run Training
```bash
python3 train_model.py
```

## What You'll See

1. **Loading datasets** (~5 seconds)
   ```
   Loading training dataset...
   ✓ Loaded 125 training examples
   ```

2. **Downloading model** (~2-3 minutes, first time only)
   ```
   Loading model with QLoRA configuration...
   This may take a few minutes to download the model...
   ```

3. **Training progress** (~10-20 minutes)
   ```
   ================================================================================
   STARTING TRAINING
   ================================================================================
   Step 1/30: Loss: 2.345
   Step 2/30: Loss: 2.123
   ...
   ```

4. **Saving model** (~1 minute)
   ```
   Saving model...
   ✓ Model saved to: Elevaretinyllma
   ```

5. **Testing** (~2-3 minutes)
   ```
   ================================================================================
   TESTING MODEL
   ================================================================================
   DOMAIN: FORECLOSURE
   ...
   ```

## Total Time: ~15-25 minutes

## After Training

The trained model will be in:
```bash
ls -la Elevaretinyllma/
```

To download:
- Click gear icon (⚙️) → Download file
- Navigate to `~/Training LLM/Elevaretinyllma/`
- Download the model files
