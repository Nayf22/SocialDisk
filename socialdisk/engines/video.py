"""
HyperGrid Video Engine — High-capacity visual matrix for video

Algorithm:
  ┌────────────────────────────────────────────────────────────────────┐
  │ 1. Pack data → bit array (pack_payload)                            │
  │ 2. Per frame: fill a grid of block_size×block_size squares         │
  │    • Color values: 35 (bit=0) and 220 (bit=1)                      │
  │      [chosen to be outside the TV-Range YUV420p that clips 16/235] │
  │ 3. Draw calibration borders (white/black) for dynamic threshold     │
  │ 4. Upscale grid to full resolution (Nearest-Neighbor, no smoothing) │
  │ 5. Save as MP4 (mp4v codec)                                         │
  │                                                                      │
  │ Extraction:                                                          │
  │ 1. Per frame: sample the centre of each square (safe region)         │
  │ 2. Dynamic calibration from frame borders (adapts to platform        │
  │    H.264 re-encoding distortions)                                    │
  │ 3. Accumulate bits and decrypt                                        │
  └────────────────────────────────────────────────────────────────────┘

Why block_size ≥ 16?
  H.264 uses 16×16 pixel macroblocks. A block matching the macroblock size
  means the content inside the block is processed as a single unit, reducing distortion.

Why 35 and 220 (not 0 and 255)?
  MPEG/H.264 uses TV-Range: Y=[16..235], Cb/Cr=[16..240]
  Values 0 and 255 are clipped to range boundaries.
  Values 35 and 220 provide a safety margin from both ends.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from socialdisk.core import VaultCore
from socialdisk.platforms import VideoProfile


class HyperGridVideoEngine:
    """
    Visual matrix video engine.
    Converts any large file into encrypted video frames that can be embedded in platforms.
    """

    # Safe colour values within TV-Range YUV420p
    VAL_ZERO  = 35    # Represents bit=0
    VAL_ONE   = 220   # Represents bit=1
    MARGIN    = 2     # Number of blocks on each side for calibration

    # ------------------------------------------------------------------ #
    #  Encoding (data → video)
    # ------------------------------------------------------------------ #
    @classmethod
    def encode(
        cls,
        output_video: str,
        payload: bytes,
        password: str,
        profile: Optional[VideoProfile] = None,
        *,
        fps: Optional[int] = None,
        block_size: Optional[int] = None,
        ecc_symbols: Optional[int] = None,
    ) -> dict:
        """
        Convert a data file into an encrypted video.

        Args:
            output_video: Path to the output video (.mp4 recommended).
            payload:      Data to store (bytes).
            password:     Encryption password.
            profile:      Platform configuration profile.
            fps:          Overrides profile.fps if given.
            block_size:   Overrides profile.block_size if given.
            ecc_symbols:  Overrides profile.ecc_symbols if given.

        Returns:
            dict: Encoding statistics.
        """
        _fps        = fps        or (profile.fps        if profile else 30)
        _block_size = block_size or (profile.block_size if profile else 16)
        _ecc        = ecc_symbols or (profile.ecc_symbols if profile else 128)
        _width      = profile.max_width  if profile else 1080
        _height     = profile.max_height if profile else 1920

        # --- Pack data
        bits = VaultCore.pack_payload(payload, password, ecc_symbols=_ecc)

        # --- Calculate per-frame capacity
        grid_w    = _width  // _block_size
        grid_h    = _height // _block_size
        m         = cls.MARGIN
        data_cols = grid_w - 2 * m
        data_rows = grid_h - 2 * m
        bpf       = data_cols * data_rows   # bits per frame

        # --- Generate enough frames (zero-padded)
        total_frames = max(1, int(np.ceil(len(bits) / bpf)))
        padded_bits  = np.zeros(total_frames * bpf, dtype=np.uint8)
        padded_bits[: len(bits)] = bits

        # --- Open video writer
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_video, fourcc, _fps, (_width, _height))
        if not writer.isOpened():
            raise RuntimeError(
                f"Failed to open output file for writing: {output_video}\n"
                "Ensure the directory exists and the file extension is .mp4"
            )

        # --- Pre-build calibration template (shared across all frames — avoids redundant fill)
        template = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)
        template[:m,  :, :] = cls.VAL_ONE   # top → white (VAL_ONE)
        template[-m:, :, :] = cls.VAL_ZERO  # bottom → black (VAL_ZERO)
        template[:,  :m, :] = cls.VAL_ONE   # left → white
        template[:, -m:, :] = cls.VAL_ZERO  # right → black
        # LUT: index 0 → VAL_ZERO, index 1 → VAL_ONE (faster than np.where)
        lut = np.array([cls.VAL_ZERO, cls.VAL_ONE], dtype=np.uint8)

        for f_idx in range(total_frames):
            frame_grid = template.copy()

            # --- Data region using LUT (faster than np.where + 3 separate channel assigns)
            chunk    = padded_bits[f_idx * bpf : (f_idx + 1) * bpf]
            val_grid = lut[chunk.reshape((data_rows, data_cols))]
            frame_grid[m : -m, m : -m, :] = val_grid[:, :, None]

            # --- Upscale to full resolution (Nearest-Neighbor — no edge smoothing)
            full_frame = cv2.resize(
                frame_grid, (_width, _height), interpolation=cv2.INTER_NEAREST
            )
            writer.write(full_frame)

        writer.release()

        return {
            "resolution":               f"{_width}×{_height}",
            "total_frames":              total_frames,
            "duration_sec":              round(total_frames / _fps, 2),
            "capacity_per_frame_bytes":  bpf // 8,
            "total_capacity_bytes":      (bpf * total_frames) // 8,
            "ecc_symbols":               _ecc,
            "block_size":                _block_size,
        }

    # ------------------------------------------------------------------ #
    #  Decoding (video → data)
    # ------------------------------------------------------------------ #
    @classmethod
    def decode(
        cls,
        video_path: str,
        password: str,
        profile: Optional[VideoProfile] = None,
        *,
        block_size: Optional[int] = None,
        ecc_symbols: Optional[int] = None,
    ) -> bytes:
        """
        Recover the original file from a video (even after platform compression).

        Uses per-frame dynamic calibration (white_ref/black_ref) to adapt to
        brightness distortions caused by the platform's H.264 re-encoding.
        """
        _block_size = block_size or (profile.block_size if profile else 16)
        _ecc        = ecc_symbols or (profile.ecc_symbols if profile else 128)
        _width      = profile.max_width  if profile else 1080
        _height     = profile.max_height if profile else 1920

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"Failed to open video: {video_path}")

        grid_w = _width  // _block_size
        grid_h = _height // _block_size
        m      = cls.MARGIN
        all_bits: list[np.ndarray] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # --- Resize if the platform has downscaled the video
            if frame.shape[1] != _width or frame.shape[0] != _height:
                frame = cv2.resize(
                    frame, (_width, _height), interpolation=cv2.INTER_LINEAR
                )

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # --- Sample the centre of each square (safe region, far from edges)
            half    = _block_size // 2
            centers = gray[half :: _block_size, half :: _block_size]

            # --- Check dimensions
            if centers.shape[0] < grid_h or centers.shape[1] < grid_w:
                continue
            centers = centers[:grid_h, :grid_w]

            # --- Dynamic calibration from frame borders
            white_ref = float(np.mean(centers[:m, :]))
            black_ref = float(np.mean(centers[-m:, :]))

            # Skip frames where calibration borders are corrupted
            if abs(white_ref - black_ref) < 30:
                continue

            thresh = (white_ref + black_ref) / 2.0

            # --- Extract bits from data region
            data_zone  = centers[m : -m, m : -m]
            frame_bits = (data_zone > thresh).astype(np.uint8).flatten()
            all_bits.append(frame_bits)

        cap.release()

        if not all_bits:
            raise ValueError(
                "No valid frames were read.\n"
                "Ensure the video is valid and that block_size parameters match those used during encoding."
            )

        combined = np.concatenate(all_bits)
        return VaultCore.unpack_payload(combined, password, ecc_symbols=_ecc)
