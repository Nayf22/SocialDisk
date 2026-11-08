"""
Social Platform Configuration Profiles — Platform Profiles

Each platform defines precise parameters built on analysis of its actual compression mechanism:

  ImageProfile:
    jpeg_attack_quality  — JPEG quality the platform applies on upload
    max_width            — Maximum width before automatic resizing
    strips_exif          — Does the platform strip EXIF metadata?
    delta                — DCT signal strength (must be >> quantization step at attack quality)
    ecc_symbols          — Reed-Solomon symbols (more compression → more symbols)
    redundancy           — Spatial repetition count per bit (more compression → more repetitions)

  VideoProfile:
    max_width/height     — Maximum resolution accepted by the platform
    fps                  — Recommended frame rate
    block_size           — Data square size (pixels) — larger than H.264 macroblock=16
    ecc_symbols, redundancy

  AudioProfile:
    freq_zero/one        — FSK frequencies safe from AAC/Opus compression
    sync_freq            — Sync tone frequency (lower → more detectable)
    baud_rate            — Bit transmission rate (baud/second)
    sample_rate          — Sample rate
    ecc_symbols

Optimal Delta calculation per platform:
  JPEG quantization step for position (3,2) ≈ 22 (from standard luminance table)
  At quality q: step ≈ 22 × (100-q)/50
  To ensure survival: delta > step × 2.5 (safety margin ×2.5)

  q=90 → step≈4.4  → delta≥11  (we use 20)
  q=85 → step≈6.6  → delta≥17  (we use 32)
  q=80 → step≈8.8  → delta≥22  (we use 38)
  q=75 → step≈11   → delta≥28  (we use 44)
  q=70 → step≈13.2 → delta≥33  (we use 50)
  q=65 → step≈15.4 → delta≥39  (we use 55)
  q=60 → step≈17.6 → delta≥44  (we use 60)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ======================================================================
#  Profile Dataclass Definitions
# ======================================================================

@dataclass
class ImageProfile:
    """Image embedding configuration profile."""
    jpeg_attack_quality: int    # JPEG quality applied by the platform
    max_width: int              # Maximum width (pixels)
    strips_exif: bool           # Does the platform strip EXIF data?
    delta: float                # DCT signal strength (must be > quantization step × 2.5)
    ecc_symbols: int            # Reed-Solomon correction symbols
    redundancy: int = 3         # Spatial repetition count per bit


@dataclass
class VideoProfile:
    """Video embedding configuration profile."""
    max_width: int              # Maximum width (pixels)
    max_height: int             # Maximum height (pixels)
    fps: int                    # Recommended frame rate
    block_size: int             # Data square size (pixels) ≥ 16
    ecc_symbols: int
    redundancy: int = 1


@dataclass
class AudioProfile:
    """Audio embedding configuration profile (Acoustic FSK)."""
    freq_zero: float            # Frequency for bit=0 (Hz)
    freq_one: float             # Frequency for bit=1 (Hz)
    sync_freq: float            # Sync tone frequency (Hz)
    baud_rate: int              # Bits per second
    sample_rate: int            # Sample rate (Hz)
    ecc_symbols: int
    redundancy: int = 1


@dataclass
class PlatformProfile:
    """Complete configuration profile for a social media platform."""
    key: str                             # Internal key
    name: str                            # Display name
    emoji: str                           # Emoji icon
    description: str                     # Short description
    image: Optional[ImageProfile] = None
    video: Optional[VideoProfile] = None
    audio: Optional[AudioProfile] = None


# ======================================================================
#  Platform Table — 14 Supported Platforms
# ======================================================================

PLATFORMS: dict[str, PlatformProfile] = {

    # ═══════════════════════════════════════════════════════════════
    # Instagram — JPEG 65-80% | H.264 | AAC 128k
    # Images: strong compression | Video: H.264 at 30fps | Audio: AAC 128k
    # ═══════════════════════════════════════════════════════════════
    "instagram": PlatformProfile(
        key="instagram", name="Instagram", emoji="📸",
        description="Photos and Reels platform | Medium-strong JPEG compression (q≈70)",
        image=ImageProfile(
            jpeg_attack_quality=70, max_width=1080,
            strips_exif=True, delta=50.0, ecc_symbols=80, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1080, max_height=1920, fps=30,
            block_size=16, ecc_symbols=128, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=2700.0, sync_freq=900.0,
            baud_rate=150, sample_rate=44100, ecc_symbols=64,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # WhatsApp — JPEG 70% | H.264 | Opus 32k (voice) / AAC
    # Very strong image compression | Opus audio cuts <400Hz and >4000Hz
    # ═══════════════════════════════════════════════════════════════
    "whatsapp": PlatformProfile(
        key="whatsapp", name="WhatsApp", emoji="💬",
        description="Messaging app | Strong image compression (q≈70) | Opus audio",
        image=ImageProfile(
            jpeg_attack_quality=70, max_width=1600,
            strips_exif=True, delta=55.0, ecc_symbols=96, redundancy=5,
        ),
        video=VideoProfile(
            max_width=1280, max_height=720, fps=25,
            block_size=16, ecc_symbols=150, redundancy=1,
        ),
        audio=AudioProfile(
            # Opus safe range 400-7700 Hz at 32kbps
            freq_zero=1200.0, freq_one=2400.0, sync_freq=700.0,
            baud_rate=100, sample_rate=44100, ecc_symbols=80,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Twitter / X — JPEG 85% | H.264 | AAC 128k
    # Relatively light image compression | Video up to 60fps and 1080p
    # ═══════════════════════════════════════════════════════════════
    "twitter": PlatformProfile(
        key="twitter", name="Twitter / X", emoji="🐦",
        description="Microblogging platform | Light image compression (q≈85)",
        image=ImageProfile(
            jpeg_attack_quality=85, max_width=4096,
            strips_exif=True, delta=32.0, ecc_symbols=64, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1920, max_height=1080, fps=60,
            block_size=16, ecc_symbols=100, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=2700.0, sync_freq=900.0,
            baud_rate=200, sample_rate=44100, ecc_symbols=64,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # TikTok — Video only | H.264 very heavy compression | AAC 128k
    # Does not support image posts as standalone in the same way
    # ═══════════════════════════════════════════════════════════════
    "tiktok": PlatformProfile(
        key="tiktok", name="TikTok", emoji="🎵",
        description="Short video platform | Very heavy video compression | 9:16 only",
        video=VideoProfile(
            max_width=1080, max_height=1920, fps=30,
            block_size=20,   # Larger than 16 to survive heavy macroblock compression
            ecc_symbols=160, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=2700.0, sync_freq=900.0,
            baud_rate=120, sample_rate=44100, ecc_symbols=80,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # YouTube — H.264/VP9 light compression | AAC 128-384k
    # Preserves higher quality especially at 1080p+ resolutions
    # ═══════════════════════════════════════════════════════════════
    "youtube": PlatformProfile(
        key="youtube", name="YouTube", emoji="▶️",
        description="Long video platform | Light compression at high resolutions",
        video=VideoProfile(
            max_width=3840, max_height=2160, fps=60,
            block_size=12,   # Smaller blocks possible since compression is light
            ecc_symbols=64, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=3000.0, sync_freq=800.0,
            baud_rate=300, sample_rate=44100, ecc_symbols=48,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Telegram — JPEG 85% (as photo) or no compression (as file) | MP3/AAC
    # Images can be sent as "file" to avoid full compression
    # ═══════════════════════════════════════════════════════════════
    "telegram": PlatformProfile(
        key="telegram", name="Telegram", emoji="✈️",
        description="Messaging app | Moderate compression as photo, or no compression as file",
        image=ImageProfile(
            jpeg_attack_quality=85, max_width=2560,
            strips_exif=False, delta=32.0, ecc_symbols=64, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1280, max_height=720, fps=30,
            block_size=16, ecc_symbols=100, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=3000.0, sync_freq=800.0,
            baud_rate=200, sample_rate=44100, ecc_symbols=48,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Discord — JPEG 90% | H.264 | Opus 128k
    # Relatively light image compression compared to other platforms
    # ═══════════════════════════════════════════════════════════════
    "discord": PlatformProfile(
        key="discord", name="Discord", emoji="🎮",
        description="Community platform | Light image compression (q≈90) | Opus audio",
        image=ImageProfile(
            jpeg_attack_quality=90, max_width=4096,
            strips_exif=False, delta=22.0, ecc_symbols=48, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1920, max_height=1080, fps=60,
            block_size=12, ecc_symbols=64, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=3000.0, sync_freq=800.0,
            baud_rate=300, sample_rate=48000, ecc_symbols=48,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Facebook — JPEG 80-85% | H.264 | AAC 128k
    # Modifies EXIF and resizes images to 2048px
    # ═══════════════════════════════════════════════════════════════
    "facebook": PlatformProfile(
        key="facebook", name="Facebook", emoji="👥",
        description="Social media platform | Medium image compression (q≈80)",
        image=ImageProfile(
            jpeg_attack_quality=80, max_width=2048,
            strips_exif=True, delta=40.0, ecc_symbols=80, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1920, max_height=1080, fps=60,
            block_size=16, ecc_symbols=120, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=2700.0, sync_freq=900.0,
            baud_rate=150, sample_rate=44100, ecc_symbols=64,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Snapchat — JPEG 70-80% | H.264 | AAC
    # Strong image compression and resizes to 1080px
    # ═══════════════════════════════════════════════════════════════
    "snapchat": PlatformProfile(
        key="snapchat", name="Snapchat", emoji="👻",
        description="Ephemeral media app | Strong image compression (q≈72)",
        image=ImageProfile(
            jpeg_attack_quality=72, max_width=1080,
            strips_exif=True, delta=50.0, ecc_symbols=90, redundancy=5,
        ),
        video=VideoProfile(
            max_width=1080, max_height=1920, fps=30,
            block_size=18, ecc_symbols=140, redundancy=1,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Reddit — JPEG 85% (i.redd.it) | H.264 | AAC
    # ═══════════════════════════════════════════════════════════════
    "reddit": PlatformProfile(
        key="reddit", name="Reddit", emoji="🔴",
        description="Community and discussion platform | Moderate image compression (q≈85)",
        image=ImageProfile(
            jpeg_attack_quality=85, max_width=4096,
            strips_exif=True, delta=32.0, ecc_symbols=64, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1920, max_height=1080, fps=30,
            block_size=16, ecc_symbols=100, redundancy=1,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # LinkedIn — JPEG 85% | H.264
    # ═══════════════════════════════════════════════════════════════
    "linkedin": PlatformProfile(
        key="linkedin", name="LinkedIn", emoji="💼",
        description="Employment and business platform | Medium compression (q≈85)",
        image=ImageProfile(
            jpeg_attack_quality=85, max_width=1584,
            strips_exif=True, delta=35.0, ecc_symbols=70, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1920, max_height=1080, fps=30,
            block_size=16, ecc_symbols=110, redundancy=1,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Pinterest — JPEG 80-85%
    # Optimised for portrait images (2:3)
    # ═══════════════════════════════════════════════════════════════
    "pinterest": PlatformProfile(
        key="pinterest", name="Pinterest", emoji="📌",
        description="Inspirational image platform | Medium image compression (q≈82)",
        image=ImageProfile(
            jpeg_attack_quality=82, max_width=1200,
            strips_exif=True, delta=38.0, ecc_symbols=75, redundancy=3,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Mastodon — Open network | Very light compression
    # ═══════════════════════════════════════════════════════════════
    "mastodon": PlatformProfile(
        key="mastodon", name="Mastodon", emoji="🐘",
        description="Open-source social network | Very light compression",
        image=ImageProfile(
            jpeg_attack_quality=88, max_width=2560,
            strips_exif=False, delta=22.0, ecc_symbols=48, redundancy=3,
        ),
        video=VideoProfile(
            max_width=1920, max_height=1080, fps=60,
            block_size=12, ecc_symbols=64, redundancy=1,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Signal — Very strong image compression to save bandwidth (q≈65-70)
    # ═══════════════════════════════════════════════════════════════
    "signal": PlatformProfile(
        key="signal", name="Signal", emoji="🔒",
        description="Encrypted messaging app | Very strong image compression (q≈65)",
        image=ImageProfile(
            jpeg_attack_quality=65, max_width=1600,
            strips_exif=True, delta=60.0, ecc_symbols=100, redundancy=5,
        ),
        audio=AudioProfile(
            # Opus in Signal cuts frequencies <400Hz and >4000Hz
            freq_zero=1200.0, freq_one=2400.0, sync_freq=700.0,
            baud_rate=80, sample_rate=44100, ecc_symbols=96,
        ),
    ),
}


# ======================================================================
#  Helper Functions
# ======================================================================

def get_platform(key: str) -> PlatformProfile:
    """Retrieve a platform configuration profile or raise a clear exception."""
    key = key.lower().strip()
    if key not in PLATFORMS:
        available = ", ".join(PLATFORMS.keys())
        raise KeyError(
            f"Platform '{key}' is not recognised.\n"
            f"Available platforms: {available}"
        )
    return PLATFORMS[key]


def list_platforms() -> list[PlatformProfile]:
    """Return a list of all supported platforms."""
    return list(PLATFORMS.values())
