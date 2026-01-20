"""
Run this script on your GCP instance to update text_generator.py with PEFT support.
Copy and paste this entire script into your GCP instance terminal.
"""

import re
import shutil

file_path = "agents/content_creator/text_generator.py"

# Backup
shutil.copy(file_path, file_path + ".backup")
print(f"✓ Backed up to {file_path}.backup")

# Read file
with open(file_path, 'r') as f:
    content = f.read()

# Check if already updated
if "self.peft_adapter_path = os.environ.get" in content:
    print("✓ File already has PEFT support!")
    exit(0)

# New __init__ method with PEFT support
new_init = '''    def __init__(
        self,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_retries: int = 3,
        api_key: Optional[str] = None,
        local_llm_endpoint: Optional[str] = None,
        timeout_s: int = 120,
        brand_manager: Optional[Any] = None  # Deprecated - kept for compatibility
    ):
        self.temperature = temperature
        self.max_retries = max_retries
        self.timeout_s = timeout_s

        # Model selection
        self.model = os.environ.get("LOCAL_LLM_MODEL") or model or "tinyllama"

        # Direct PEFT model mode (preferred if you have it)
        self.peft_adapter_path = os.environ.get("PEFT_ADAPTER_PATH")
        self.base_model_name = os.environ.get("BASE_MODEL_NAME", "TinyLlama/TinyLlama-1.1B-Chat-v1.0")

        self.use_direct_model = False
        self.model_obj = None
        self.tokenizer = None

        if self.peft_adapter_path:
            if not PEFT_AVAILABLE:
                logger.warning("PEFT_ADAPTER_PATH set, but peft/transformers/torch not installed. Falling back to HTTP mode.")
            else:
                try:
                    self._load_peft_model()
                    self.use_direct_model = True
                    logger.info("TextGenerator running in DIRECT MODEL mode (PEFT).")
                except Exception as e:
                    logger.warning("PEFT load failed (%s). Falling back to HTTP mode.", e)

        # HTTP endpoint mode
        self.api_key = api_key or os.environ.get("LOCAL_LLM_API_KEY")
        self.local_llm_endpoint = local_llm_endpoint or os.environ.get("LOCAL_LLM_ENDPOINT")

        if not self.use_direct_model:
            if not self.local_llm_endpoint:
                allow_default = os.environ.get("ALLOW_DEFAULT_LLM_ENDPOINT", "").lower() in ("true", "1", "yes")
                if allow_default:
                    self.local_llm_endpoint = "http://localhost:11434/v1/chat/completions"
                    logger.warning("LOCAL_LLM_ENDPOINT not set; using default: %s", self.local_llm_endpoint)
                else:
                    raise ValueError(
                        "Need PEFT_ADAPTER_PATH (direct model) OR LOCAL_LLM_ENDPOINT (HTTP). "
                        "To allow default endpoint, set ALLOW_DEFAULT_LLM_ENDPOINT=true."
                    )
            logger.info("TextGenerator running in HTTP mode. endpoint=%s model=%s", self.local_llm_endpoint, self.model)'''

# Find the old __init__ method (the one with brand_manager as first param)
old_init_pattern = r'(    def __init__\([^)]*brand_manager: BrandGuidelinesManager[^)]*\):.*?)(?=\n    def |\n    # |\nclass |\Z)'

def replace_init(match):
    return new_init

# Replace
new_content = re.sub(old_init_pattern, replace_init, content, flags=re.DOTALL)

# Write back
with open(file_path, 'w') as f:
    f.write(new_content)

print("✓ Updated text_generator.py with PEFT support!")
print("✓ Verify with: grep 'PEFT_ADAPTER_PATH' agents/content_creator/text_generator.py")
