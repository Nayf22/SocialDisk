"""
DCT Image Steganography Engine — Invisible frequency-domain image hiding

Algorithm (Differential Mid-Band DCT Steganography):
  ┌─────────────────────────────────────────────────────────────────┐
  │ 1. Convert image to YCrCb and extract the luminance channel Y   │
  │ 2. Split the channel into 8×8 pixel blocks                      │
  │ 3. Shuffle block order based on the password (for security)     │
  │ 4. For each bit in the data:                                     │
  │    • Apply 2D-DCT to the block                                   │
  │    • Read two mid-band frequency coefficients:                   │
  │        POS_A = (3,2)  ,  POS_B = (2,3)                          │
  │    • bit=1 → c[A] = avg + δ/2  ,  c[B] = avg - δ/2             │
  │    • bit=0 → c[A] = avg - δ/2  ,  c[B] = avg + δ/2             │
  │    • 2D-IDCT to recover pixels                                   │
  │ 5. Repeat each bit `redundancy` times across different blocks    │
  └─────────────────────────────────────────────────────────────────┘

Why mid-band frequencies?
  - Low frequencies (DC + neighbours): visually sensitive, JPEG preserves them
  - High frequencies (block corners): less visible, but JPEG erases them entirely
  - Mid-band: golden middle — JPEG attenuates but does not erase, and they are imperceptible

Why differential encoding?
  - Comparing two coefficients instead of an absolute value
  - Cancels the effect of overall DC offset (global brightness changes)
  - More robust against global processing operations (brightness/contrast adjustments)
"""
from __future__ import annotations

import hashlib
import random
from typing import Optional

import cv2
import numpy as np
from scipy.fftpack import dct, idct

from socialdisk.core import VaultCore
from socialdisk.platforms import ImageProfile


class DCTImageEngine:
    """
    Differential frequency-domain image steganography engine (Differential DCT Steganography).

    Attributes:
        POS_A: Position of the first mid-band DCT coefficient (row=3, col=2)
        POS_B: Position of the second mid-band DCT coefficient (row=2, col=3)
              — Both positions are symmetric in the mid-band with similar quantization values
    """

    POS_A = (3, 2)   # First mid-band coefficient
    POS_B = (2, 3)   # Second mid-band coefficient (similar frequency)

    # ------------------------------------------------------------------ #
    #  2D DCT Transforms
    # ------------------------------------------------------------------ #
    @staticmethod
    def _dct2(block: np.ndarray) -> np.ndarray:
        """Apply standard 2D-DCT (ortho norm) to an 8×8 block."""
        return dct(dct(block.T, norm="ortho").T, norm="ortho")

    @staticmethod
    def _idct2(block: np.ndarray) -> np.ndarray:
        """Apply standard 2D-IDCT (ortho norm) — inverse of _dct2."""
        return idct(idct(block.T, norm="ortho").T, norm="ortho")

    # ------------------------------------------------------------------ #
    #  Block Ordering
    # ------------------------------------------------------------------ #
    @classmethod
    def _get_block_order(cls, h: int, w: int, password: str) -> list[tuple[int, int]]:
        """
        Create a list of 8×8 blocks in a password-shuffled random order.

        Dual purpose:
          1. Security: attacker cannot know where data is located
          2. Distribution: spreads errors evenly if a region is damaged
        """
        blocks = [(r, c) for r in range(0, h, 8) for c in range(0, w, 8)]
        seed   = int.from_bytes(hashlib.sha256(password.encode()).digest()[:8], "big")
        rng    = random.Random(seed)
        rng.shuffle(blocks)
        return blocks

    # ------------------------------------------------------------------ #
    #  Embedding
    # ------------------------------------------------------------------ #
    @classmethod
    def embed(
        cls,
        image_path: str,
        output_path: str,
        payload: bytes,
        password: str,
        profile: Optional[ImageProfile] = None,
        *,
        delta: Optional[float] = None,
        ecc_symbols: Optional[int] = None,
        redundancy: Optional[int] = None,
    ) -> dict:
        """
        Embed data inside an image using differential DCT steganography.

        Args:
            image_path:  Path to the original cover image (any format readable by OpenCV).
            output_path: Path to save the modified image (.jpg recommended).
            payload:     Secret data (bytes).
            password:    Password.
            profile:     Platform configuration profile (if given, sets delta/ecc/redundancy automatically).
            delta:       Overrides profile.delta if given.
            ecc_symbols: Overrides profile.ecc_symbols if given.
            redundancy:  Overrides profile.redundancy if given.

        Returns:
            dict: Detailed embedding statistics.

        Raises:
            FileNotFoundError: If the image does not exist.
            ValueError:        If the data is larger than the image capacity.
        """
        # --- Determine final parameters (priority: kwarg > profile > default)
        _delta = (
            delta if delta is not None
            else (profile.delta if profile else 42.0)
        )
        _ecc = (
            ecc_symbols if ecc_symbols is not None
            else (profile.ecc_symbols if profile else 80)
        )
        _redundancy = (
            redundancy if redundancy is not None
            else (profile.redundancy if profile else 3)
        )
        _max_width = profile.max_width if profile else 1080

        # --- Load image
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        # --- Resize to platform maximum width (preserving aspect ratio)
        h, w = img.shape[:2]
        if w > _max_width:
            new_h = int(h * _max_width / w)
            new_h = max(8, (new_h // 8) * 8)   # multiple of 8
            img   = cv2.resize(img, (_max_width, new_h), interpolation=cv2.INTER_AREA)

        # --- Crop to nearest multiple of 8 in both dimensions
        h = (img.shape[0] // 8) * 8
        w = (img.shape[1] // 8) * 8
        img = img[:h, :w]

        # --- Pack payload
        bits = VaultCore.pack_payload(payload, password, ecc_symbols=_ecc)

        # --- Apply spatial redundancy
        # Each bit is repeated _redundancy times across consecutive different blocks
        redundant_bits = np.repeat(bits, _redundancy)

        # --- Check capacity
        max_blocks = (h // 8) * (w // 8)
        if len(redundant_bits) > max_blocks:
            max_safe_bytes = max(
                0,
                (max_blocks // _redundancy // 8) - _ecc - 60
            )
            raise ValueError(
                f"Data is larger than image capacity ({_max_width}×{h}).\n"
                f"Recommended maximum for this image: ~{max_safe_bytes} bytes.\n"
                f"Try: larger image | reduce ecc_symbols | reduce redundancy."
            )

        # --- Convert to YCrCb and modify the Y channel
        ycrcb     = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y_channel = ycrcb[:, :, 0]
        all_blocks = cls._get_block_order(h, w, password)

        for idx, bit in enumerate(redundant_bits):
            if idx >= len(all_blocks):
                break
            r, c   = all_blocks[idx]
            block  = y_channel[r : r + 8, c : c + 8] - 128.0
            dct_b  = cls._dct2(block)

            # --- Modify coefficient difference to encode the bit
            c1  = dct_b[cls.POS_A]
            c2  = dct_b[cls.POS_B]
            avg = (c1 + c2) / 2.0

            half_delta = _delta / 2.0
            if bit == 1:
                dct_b[cls.POS_A] = avg + half_delta
                dct_b[cls.POS_B] = avg - half_delta
            else:
                dct_b[cls.POS_A] = avg - half_delta
                dct_b[cls.POS_B] = avg + half_delta

            y_channel[r : r + 8, c : c + 8] = np.clip(
                cls._idct2(dct_b) + 128.0, 0, 255
            )

        # --- Rebuild and save image at 95% quality
        # (95% quality reduces self-compression by the save tool, leaving margin for platform compression)
        ycrcb[:, :, 0] = y_channel
        stego = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
        cv2.imwrite(output_path, stego, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        return {
            "dimensions":           f"{w}×{h}",
            "raw_size_bytes":        len(payload),
            "encoded_bits":          len(redundant_bits),
            "total_blocks":          max_blocks,
            "capacity_used_percent": round(len(redundant_bits) / max_blocks * 100, 2),
            "delta_used":            _delta,
            "ecc_symbols":           _ecc,
            "redundancy":            _redundancy,
        }

    # ------------------------------------------------------------------ #
    #  Extraction
    # ------------------------------------------------------------------ #
    @classmethod
    def extract(
        cls,
        image_path: str,
        password: str,
        profile: Optional[ImageProfile] = None,
        *,
        ecc_symbols: Optional[int] = None,
        redundancy: Optional[int] = None,
    ) -> bytes:
        """
        Extract embedded data from an image (even after platform compression).

        Reads the coefficient difference from each block in the same order used in embed,
        then performs majority voting to remove spatial redundancy.

        ⚠️ Values of ecc_symbols and redundancy must match those used during embedding.
        """
        _ecc = (
            ecc_symbols if ecc_symbols is not None
            else (profile.ecc_symbols if profile else 80)
        )
        _redundancy = (
            redundancy if redundancy is not None
            else (profile.redundancy if profile else 3)
        )

        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"Image not found: {image_path}")

        h = (img.shape[0] // 8) * 8
        w = (img.shape[1] // 8) * 8
        img = img[:h, :w]

        ycrcb     = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y_channel = ycrcb[:, :, 0]
        all_blocks = cls._get_block_order(h, w, password)

        # --- Read bit from each block via differential signal
        raw_bits: list[int] = []
        for r, c in all_blocks:
            block  = y_channel[r : r + 8, c : c + 8] - 128.0
            dct_b  = cls._dct2(block)
            diff   = dct_b[cls.POS_A] - dct_b[cls.POS_B]
            raw_bits.append(1 if diff > 0 else 0)

        # --- Remove spatial redundancy via majority voting
        usable     = (len(raw_bits) // _redundancy) * _redundancy
        groups     = np.array(raw_bits[:usable], dtype=np.uint8).reshape(-1, _redundancy)
        voted_bits = (np.sum(groups, axis=1) > _redundancy // 2).astype(np.uint8)

        return VaultCore.unpack_payload(voted_bits, password, ecc_symbols=_ecc)
