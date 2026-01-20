"""
Image Generator - Module for generating images using Stability AI API.

Handles creating image prompts, calling the Stability AI API, and processing responses
for different content types and platforms.

CHANGES MADE (stability + instagram workflow):
1) Add `max_retries_override` so Instagram can try more times than other platforms.
2) Fix retry loop and add timeout to prevent hanging.
3) Never raise on failures — return a structured error so the pipeline can continue.
4) Create output_dir with exist_ok=True.
5) Return useful error context (status_code + response snippet) without crashing.
"""

import logging
import os
import requests
import base64
import time
from typing import Dict, Any, Optional
from datetime import datetime
import uuid


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ImageGenerator")

# Maximum backoff time in seconds (cap exponential backoff)
MAX_BACKOFF_SECONDS = 60


class ImageGenerator:
    """
    Generates images using Stability AI's API.
    """

    def __init__(
        self,
        enabled: bool = True,
        api_host: str = "https://api.stability.ai",
        engine_id: str = "stable-diffusion-xl-1024-v1-0",
        output_dir: str = "generated_images",
        max_retries: int = 3,
        timeout_s: int = 30
    ):
        """
        Initialize the ImageGenerator.

        Args:
            enabled: Whether image generation is enabled
            api_host: Stability AI API host
            engine_id: Model engine ID to use
            output_dir: Directory to save generated images
            max_retries: Default maximum number of API call retries
            timeout_s: Request timeout (seconds)
        """
        self.enabled = enabled
        self.api_host = api_host.rstrip("/")
        self.engine_id = engine_id
        self.output_dir = output_dir
        self.max_retries = max_retries
        self.timeout_s = timeout_s

        # Load API key from environment variable
        self.api_key = os.environ.get("STABILITY_API_KEY")
        if not self.api_key and self.enabled:
            logger.warning("Stability AI API key not found. Image generation will be disabled.")
            self.enabled = False  # disable rather than fail later

        # Create output directory if it doesn't exist
        os.makedirs(self.output_dir, exist_ok=True)
        logger.info("ImageGenerator initialized (enabled: %s, output_dir: %s)", self.enabled, self.output_dir)

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        save_image: bool = True,
        cfg_scale: float = 7.0,
        steps: int = 30,
        max_retries_override: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate an image using the Stability AI API.

        Args:
            prompt: Image generation prompt
            aspect_ratio: Image aspect ratio (1:1, 16:9, 4:5, etc.)
            save_image: Whether to save the image to disk
            cfg_scale: How strictly to follow the prompt
            steps: Number of diffusion steps
            max_retries_override: Optional override for retry attempts (useful for Instagram)

        Returns:
            Dictionary with image information OR a structured error.
            Never raises (so your posting workflow can continue).
        """
        if not self.enabled:
            logger.info("Image generation disabled")
            return {"status": "disabled", "prompt": prompt}

        if not prompt or not isinstance(prompt, str):
            return {"error": "Invalid prompt", "prompt": prompt}

        max_attempts = max_retries_override if isinstance(max_retries_override, int) else self.max_retries
        if max_attempts < 1:
            max_attempts = 1

        width, height = self._get_dimensions_from_aspect_ratio(aspect_ratio)
        endpoint = f"{self.api_host}/v1/generation/{self.engine_id}/text-to-image"

        last_status: Optional[int] = None
        last_snippet: Optional[str] = None
        last_error: Optional[str] = None

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info(
                    "Generating image (attempt %d/%d) prompt: %s",
                    attempt,
                    max_attempts,
                    (prompt[:100] + "...") if len(prompt) > 100 else prompt
                )

                response = requests.post(
                    endpoint,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    },
                    json={
                        "text_prompts": [{"text": prompt, "weight": 1.0}],
                        "cfg_scale": cfg_scale,
                        "height": height,
                        "width": width,
                        "steps": steps,
                        "samples": 1
                    },
                    timeout=self.timeout_s
                )

                if response.status_code != 200:
                    last_status = response.status_code
                    last_snippet = (response.text or "")[:500]
                    last_error = f"API error {response.status_code}"
                    logger.warning("Image API non-200 (%s): %s", last_status, last_snippet)

                    if attempt < max_attempts:
                        backoff = min(2 ** attempt, MAX_BACKOFF_SECONDS)
                        time.sleep(backoff)
                        continue

                    return {
                        "error": last_error,
                        "status_code": last_status,
                        "response_snippet": last_snippet,
                        "prompt": prompt
                    }

                data = response.json()
                image_info = self._process_image_response(
                    response_data=data,
                    prompt=prompt,
                    save_image=save_image,
                    width=width,
                    height=height
                )

                if "error" in image_info:
                    last_error = image_info["error"]
                    logger.warning("Image response processing error: %s", last_error)
                    if attempt < max_attempts:
                        backoff = min(2 ** attempt, MAX_BACKOFF_SECONDS)
                        time.sleep(backoff)
                        continue
                    return {**image_info, "prompt": prompt}

                logger.info("Successfully generated image: %s", image_info.get("filename", "unknown"))
                return image_info

            except requests.exceptions.Timeout:
                last_error = f"Request timed out after {self.timeout_s}s"
                logger.warning("%s (attempt %d/%d)", last_error, attempt, max_attempts)
                if attempt < max_attempts:
                    backoff = min(2 ** attempt, MAX_BACKOFF_SECONDS)
                    time.sleep(backoff)
                    continue
                return {"error": last_error, "prompt": prompt}

            except requests.exceptions.RequestException as e:
                last_error = f"RequestException: {str(e)}"
                logger.warning("%s (attempt %d/%d)", last_error, attempt, max_attempts)
                if attempt < max_attempts:
                    backoff = min(2 ** attempt, MAX_BACKOFF_SECONDS)
                    time.sleep(backoff)
                    continue
                return {"error": last_error, "prompt": prompt}

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                logger.error(last_error)
                return {"error": last_error, "prompt": prompt}

        # Shouldn't reach here, but keep safe
        return {"error": "Failed to generate image", "prompt": prompt}

    def _get_dimensions_from_aspect_ratio(self, aspect_ratio: str) -> tuple:
        """
        Convert aspect ratio string to width and height dimensions.
        """
        if aspect_ratio == "1:1":
            return (1024, 1024)
        elif aspect_ratio == "16:9":
            return (1024, 576)
        elif aspect_ratio == "4:5":
            return (768, 960)
        elif aspect_ratio == "3:2":
            return (1024, 682)
        elif aspect_ratio == "4:3":
            return (1024, 768)
        else:
            logger.warning("Unrecognized aspect ratio: %s. Using 1:1 (square).", aspect_ratio)
            return (1024, 1024)

    def _process_image_response(
        self,
        response_data: Dict[str, Any],
        prompt: str,
        save_image: bool,
        width: int,
        height: int
    ) -> Dict[str, Any]:
        """
        Process the API response and save the generated image.
        """
        if "artifacts" not in response_data or not response_data["artifacts"]:
            return {"error": "No image artifacts found in response"}

        artifact = response_data["artifacts"][0]
        if "base64" not in artifact:
            return {"error": "Artifact missing base64 image data"}

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"image_{timestamp}_{unique_id}.png"
        filepath = os.path.join(self.output_dir, filename)

        if save_image:
            try:
                image_data = base64.b64decode(artifact["base64"])
                with open(filepath, "wb") as f:
                    f.write(image_data)
                logger.info("Image saved to: %s", filepath)
            except Exception as e:
                return {"error": f"Failed to decode/save image: {str(e)}"}

        return {
            "filename": filename,
            "filepath": filepath if save_image else None,
            "prompt": prompt,
            "seed": artifact.get("seed"),
            "timestamp": timestamp,
            "saved": save_image,
            "width": artifact.get("width") or width,
            "height": artifact.get("height") or height
        }
