"""
InstaDisk v2.0 — Multi-Platform Steganography Suite
أداة إخفاء وتشفير البيانات عبر المنصات الاجتماعية

الهيكل:
  instadisk/
    core.py      — نواة التشفير والتحزيم (AES-GCM + Reed-Solomon + LZMA)
    platforms.py — ملفات إعداد المنصات (Instagram, WhatsApp, TikTok, ...)
    engines/
      image.py   — محرك الإخفاء الترددي DCT في الصور
      video.py   — محرك المصفوفة البصرية HyperGrid للفيديو
      audio.py   — محرك المودم الصوتي Acoustic FSK
    api.py       — الواجهة الموحدة InstaVault
"""

from instadisk.api import InstaVault
from instadisk.platforms import PLATFORMS, get_platform, list_platforms
from instadisk.core import VaultCore

__version__ = "2.0.0"
__all__ = ["InstaVault", "VaultCore", "PLATFORMS", "get_platform", "list_platforms"]
