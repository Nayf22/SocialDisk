"""
SocialDisk v2.0 — Multi-Platform Steganography Suite
A tool for hiding and encrypting data across social media platforms.

Structure:
  socialdisk/
    core.py      — Encryption and payload core (AES-GCM + Reed-Solomon + LZMA)
    platforms.py — Platform configuration profiles (Instagram, WhatsApp, TikTok, ...)
    engines/
      image.py   — DCT frequency-domain image steganography engine
      video.py   — HyperGrid visual matrix video engine
      audio.py   — Acoustic FSK modem engine
    api.py       — Unified SocialVault interface
"""

from socialdisk.api import SocialVault
from socialdisk.platforms import PLATFORMS, get_platform, list_platforms
from socialdisk.core import VaultCore

__version__ = "2.0.0"
__all__ = ["SocialVault", "VaultCore", "PLATFORMS", "get_platform", "list_platforms"]
