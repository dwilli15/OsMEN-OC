"""Vision and image generation tools for OsMEN-OC.

On-demand multimodal inference via lemonade (local NPU/CPU) with
GLM-4.5V cloud fallback for high-stakes tasks.
"""

from __future__ import annotations

from core.vision.client import VisionClient
from core.vision.image_gen import ImageGenClient

__all__ = ["ImageGenClient", "VisionClient"]
