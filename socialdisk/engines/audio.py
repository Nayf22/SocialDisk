"""
Acoustic FSK Engine — Audio modem resistant to AAC/Opus compression

Algorithm (Frequency Shift Keying — FSK) redesigned:
  ┌─────────────────────────────────────────────────────────────────┐
  │ Encoded Signal Structure (Protocol Frame):                       │
  │                                                                  │
  │  [silence 0.25s] [preamble SYNC 0.5s] [header 32 bits] [data N bits] [silence 0.25s] │
  │                                                                  │
  │  preamble: continuous sync_freq tone 0.5s — detects signal start │
  │  header:   32 bits sent using SYNC freq (bit=1) or freq_zero (bit=0) │
  │            represents the number of data bits (N) XOR-encoded for concealment │
  │  data:     N bits — bit=0 → freq_zero, bit=1 → freq_one          │
  │                                                                  │
  │ Decoding:                                                         │
  │  1. Detect preamble start (first window with high SYNC power)    │
  │  2. Skip preamble (fixed 0.5s)                                   │
  │  3. Read 32 header bits → extract N                              │
  │  4. Read N data bits                                             │
  │  5. VaultCore.unpack_payload to decrypt                          │
  └─────────────────────────────────────────────────────────────────┘

Why embed the header in the signal?
  Detecting preamble end via FFT fails because harmonics of data frequencies
  (1500 Hz / 2700 Hz) can produce a component at the SYNC frequency (900 Hz),
  making a "last SYNC appearance" algorithm unreliable.
  Solution: embed N directly in the signal to know the data size with absolute precision.

Why frequencies 1500/2700/900 Hz?
  - AAC at 128kbps: range 20Hz–16kHz (safe)
  - Opus at 32kbps: range 400Hz–7700Hz (safe)
  - 1200Hz gap between f0/f1 reduces mixing under heavy compression
  - 900 Hz for SYNC: far from 1500/2700 and does not interfere
"""
from __future__ import annotations

import os
import struct
import subprocess
from typing import Optional

import numpy as np
from scipy.io import wavfile

from socialdisk.core import VaultCore
from socialdisk.platforms import AudioProfile

# ───────────────────────────────────────────────────────────────────
#  Frame Protocol Constants
# ───────────────────────────────────────────────────────────────────
_HEADER_BITS    = 32          # Number of bits in the header field (stores N data bits)
_HEADER_XOR_KEY = 0xA5C3E1F7  # XOR key to conceal N value (avoids repetitive patterns)
_PREAMBLE_DUR   = 0.5         # SYNC tone duration in seconds
_SILENCE_DUR    = 0.25        # Silence duration before/after the signal


class AcousticFSKEngine:
    """
    Acoustic FSK modem engine.
    Converts data into audio waves using audible frequencies safe from platform compression.

    Signal Structure (Protocol Frame):
        [silence 0.25s] → [SYNC preamble 0.5s] → [32-bit header] → [data bits] → [silence 0.25s]

    Where header = number of data bits (N) XOR-encoded, transmitted using:
        bit=1 → sync_freq tone (same as preamble)
        bit=0 → freq_zero tone
    """

    # ------------------------------------------------------------------ #
    #  Tone generation helper with Hanning fade-in/out
    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_tone(
        freq: float,
        duration: float,
        sample_rate: int,
        amplitude: float = 0.85,
    ) -> np.ndarray:
        """
        Generate a pure sine tone with smooth fade (Hanning window on 5% of edges).
        The fade prevents click artifacts when transitioning between tones.
        """
        n       = max(1, int(sample_rate * duration))
        t       = np.linspace(0, duration, n, endpoint=False)
        signal  = amplitude * np.sin(2.0 * np.pi * freq * t)
        fade    = max(2, n // 20)
        signal[:fade]  *= np.linspace(0.0, 1.0, fade)
        signal[-fade:] *= np.linspace(1.0, 0.0, fade)
        return signal.astype(np.float32)

    # ------------------------------------------------------------------ #
    #  FFT frequency power helper (vectorized)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _fft_magnitude(
        samples: np.ndarray,
        target_freq: float,
        sample_rate: int,
    ) -> float:
        """
        Calculate the power of a specific frequency via FFT with Hanning window to reduce spectral leakage.
        Averages ±2 bins for a more stable reading.
        """
        n     = len(samples)
        win   = np.hanning(n)
        spec  = np.abs(np.fft.rfft(samples * win))
        freqs = np.fft.rfftfreq(n, 1.0 / sample_rate)
        idx   = int(np.argmin(np.abs(freqs - target_freq)))
        lo    = max(0, idx - 2)
        hi    = min(len(spec), idx + 3)
        return float(np.mean(spec[lo:hi]))

    # ------------------------------------------------------------------ #
    #  Encode 32-bit integer to bit list (MSB first)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _int_to_bits(value: int, n_bits: int = 32) -> list[int]:
        """Convert an integer to a bit list in MSB-first order."""
        return [(value >> (n_bits - 1 - i)) & 1 for i in range(n_bits)]

    # ------------------------------------------------------------------ #
    #  Decode bit list to integer (MSB first)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _bits_to_int(bits: list[int]) -> int:
        """Convert a bit list (MSB-first) to an integer."""
        result = 0
        for b in bits:
            result = (result << 1) | int(b)
        return result

    # ------------------------------------------------------------------ #
    #  Encoding: data → WAV
    # ------------------------------------------------------------------ #
    @classmethod
    def encode_wav(
        cls,
        output_wav: str,
        payload: bytes,
        password: str,
        profile: Optional[AudioProfile] = None,
        *,
        ecc_symbols: Optional[int] = None,
    ) -> dict:
        """
        Convert data into an FSK-encoded WAV file.

        Generated signal structure:
            [silence 0.25s] [SYNC 0.5s] [32-bit header] [N data bits] [silence 0.25s]

        Where header = (N XOR _HEADER_XOR_KEY) transmitted using SYNC/f0 instead of f0/f1
        to avoid overlap with the data pattern.

        Args:
            output_wav:  Path to the output audio file (.wav).
            payload:     Secret data (bytes).
            password:    Password.
            profile:     Platform configuration profile (sets frequencies and speed).
            ecc_symbols: Overrides profile.ecc_symbols if given.

        Returns:
            dict: Audio file statistics.
        """
        _ecc  = ecc_symbols or (profile.ecc_symbols if profile else 64)
        _sr   = profile.sample_rate if profile else 44100
        _baud = profile.baud_rate   if profile else 150
        _f0   = profile.freq_zero   if profile else 1500.0
        _f1   = profile.freq_one    if profile else 2700.0
        _fs   = profile.sync_freq   if profile else 900.0

        # --- Pack data → bits
        data_bits    = VaultCore.pack_payload(payload, password, ecc_symbols=_ecc)
        n_data_bits  = len(data_bits)
        bit_duration = 1.0 / _baud

        spb = _sr // _baud  # samples per bit (294 at 44100/150)

        # --- Pre-generate base tones (pre-generated for efficiency)
        tone0     = cls._make_tone(_f0, bit_duration, _sr)   # data: bit=0
        tone1     = cls._make_tone(_f1, bit_duration, _sr)   # data: bit=1
        tone_sync = cls._make_tone(_fs, bit_duration, _sr)   # header/preamble: bit=1

        # --- header = (n_data_bits XOR _HEADER_XOR_KEY) — 32 bits MSB-first
        header_val  = n_data_bits ^ _HEADER_XOR_KEY
        header_bits = cls._int_to_bits(header_val, _HEADER_BITS)

        # --- Calculate segment sizes in bit units (spb samples per bit)
        #   This ensures every boundary in the signal falls at an exact multiple of spb,
        #   eliminating the need for any alignment during decoding.
        #
        #   SILENCE_BITS = number of bits for silence (nearest integer to 0.25s)
        #   PREAMBLE_BITS = number of bits for preamble (nearest integer to 0.5s)
        #
        SILENCE_BITS  = max(1, round(_sr * _SILENCE_DUR  / spb))  # ≈37 bits
        PREAMBLE_BITS = max(1, round(_sr * _PREAMBLE_DUR / spb))  # ≈75 bits

        # --- Build the complete signal (each element = one tone of spb samples)
        parts: list[np.ndarray] = []

        # Leading silence (SILENCE_BITS zero tones)
        for _ in range(SILENCE_BITS):
            parts.append(np.zeros(spb, dtype=np.float32))

        # SYNC preamble (PREAMBLE_BITS tones at SYNC frequency)
        for _ in range(PREAMBLE_BITS):
            parts.append(tone_sync)

        # Header bits (bit=1 → sync_freq, bit=0 → freq_zero)
        # Using sync_freq for header distinguishes it from data bits (which use f0/f1)
        for b in header_bits:
            parts.append(tone_sync if b == 1 else tone0)

        # Data bits (bit=1 → freq_one, bit=0 → freq_zero)
        for b in data_bits:
            parts.append(tone1 if b == 1 else tone0)

        # Trailing silence (SILENCE_BITS zero tones)
        for _ in range(SILENCE_BITS):
            parts.append(np.zeros(spb, dtype=np.float32))

        full_signal = np.concatenate(parts)
        pcm_data    = (full_signal * 28_000).astype(np.int16)
        wavfile.write(output_wav, _sr, pcm_data)

        return {
            "duration_sec":    round(len(full_signal) / _sr, 2),
            "baud_rate":       _baud,
            "total_bits":      n_data_bits,
            "freq_zero_hz":    _f0,
            "freq_one_hz":     _f1,
            "sync_freq_hz":    _fs,
            "header_bits":     _HEADER_BITS,
            "silence_bits":    SILENCE_BITS,
            "preamble_bits":   PREAMBLE_BITS,
        }

    # ------------------------------------------------------------------ #
    #  Decoding: WAV/MP4 → data
    # ------------------------------------------------------------------ #
    @classmethod
    def decode_media(
        cls,
        media_path: str,
        password: str,
        profile: Optional[AudioProfile] = None,
        *,
        ecc_symbols: Optional[int] = None,
    ) -> bytes:
        """
        Extract data from a WAV audio file or MP4 video.

        Decoding steps:
          1. If input is MP4: extract audio via ffmpeg
          2. Detect preamble SYNC start (first window with high power)
          3. Skip preamble (fixed 0.5s) to reach the header
          4. Read 32 header bits → extract N (number of data bits)
          5. Read N data bits (FFT vectorized)
          6. VaultCore.unpack_payload to decrypt

        Args:
            media_path:  Path to the audio file (.wav) or video (.mp4/.mkv/...).
            password:    Password.
            profile:     Platform configuration profile.
            ecc_symbols: Overrides profile.ecc_symbols if given.

        Returns:
            Extracted data (bytes).
        """
        _ecc  = ecc_symbols or (profile.ecc_symbols if profile else 64)
        _sr   = profile.sample_rate if profile else 44100
        _baud = profile.baud_rate   if profile else 150
        _f0   = profile.freq_zero   if profile else 1500.0
        _f1   = profile.freq_one    if profile else 2700.0
        _fs   = profile.sync_freq   if profile else 900.0

        # --- Extract audio from video via ffmpeg if needed
        temp_wav = None
        if not media_path.lower().endswith(".wav"):
            temp_wav = "_socialdisk_temp_audio.wav"
            cmd = [
                "ffmpeg", "-y", "-i", media_path,
                "-vn", "-ac", "1", "-ar", str(_sr),
                "-sample_fmt", "s16", temp_wav,
            ]
            try:
                subprocess.run(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=True,
                )
            except subprocess.CalledProcessError:
                raise RuntimeError(
                    "Failed to extract audio from video.\n"
                    "Ensure ffmpeg is installed and added to PATH."
                )
            target = temp_wav
        else:
            target = media_path

        try:
            sr_read, raw_data = wavfile.read(target)

            # --- Convert to mono float32 normalised to [-1, 1]
            if raw_data.ndim > 1:
                raw_data = raw_data[:, 0]
            data = raw_data.astype(np.float32)
            max_val = np.abs(data).max()
            if max_val > 0:
                data = data / max_val

            # --- Resample if recorded sample rate differs
            if sr_read != _sr:
                from scipy.signal import resample_poly
                from math import gcd
                g    = gcd(int(_sr), int(sr_read))
                up   = int(_sr)     // g
                dn   = int(sr_read) // g
                data = resample_poly(data, up, dn).astype(np.float32)

            spb = _sr // _baud   # samples per bit / tone

            # Calculate SILENCE_BITS and PREAMBLE_BITS using the same method as encode_wav
            # (must be identical to ensure alignment)
            SILENCE_BITS  = max(1, round(_sr * _SILENCE_DUR  / spb))  # ≈37 bits
            PREAMBLE_BITS = max(1, round(_sr * _PREAMBLE_DUR / spb))  # ≈75 bits

            # ══════════════════════════════════════════════════════════
            #  STEP 1: Verify preamble (SYNC) presence and quality
            #
            #  Scan the expected SILENCE range to verify the signal
            #  started correctly. Used for early detection of file errors
            #  (wrong file / not encoded / corrupted).
            #
            #  We do not use this detection result to determine the header
            #  start, because SILENCE_BITS and PREAMBLE_BITS are fixed and
            #  known in advance.
            # ══════════════════════════════════════════════════════════
            # Search range for preamble: from SILENCE_BITS to SILENCE_BITS+PREAMBLE_BITS
            preamble_region_start = SILENCE_BITS * spb
            preamble_region_end   = (SILENCE_BITS + PREAMBLE_BITS) * spb

            if preamble_region_end > len(data):
                raise ValueError(
                    "Audio file is too short — it must contain a SYNC preamble.\n"
                    "Ensure the file was encoded with SocialDisk and is not truncated."
                )

            # Measure SYNC power at the midpoint of the expected preamble (verification only)
            mid_preamble = preamble_region_start + (PREAMBLE_BITS // 2) * spb
            chunk_mid    = data[mid_preamble: mid_preamble + spb]
            sync_power_mid = cls._fft_magnitude(chunk_mid, _fs, _sr)

            # Measure SYNC power at the midpoint of the expected preceding silence
            mid_silence  = (SILENCE_BITS // 2) * spb
            chunk_sil    = data[mid_silence: mid_silence + spb]
            sync_power_sil = cls._fft_magnitude(chunk_sil, _fs, _sr)

            # SYNC power in preamble must be significantly higher than in silence
            if sync_power_mid < 0.5 or (sync_power_sil > 0 and sync_power_mid < sync_power_sil * 2.0):
                raise ValueError(
                    "Sync tone (preamble) not found at the expected position.\n"
                    "Ensure the file was encoded with SocialDisk."
                )

            # ══════════════════════════════════════════════════════════
            #  STEP 2: Determine header start with absolute precision
            #
            #  Header start = (SILENCE_BITS + PREAMBLE_BITS) * spb
            #  This is fixed and identical to encode_wav, because both
            #  use the same formula to calculate SILENCE_BITS and PREAMBLE_BITS.
            #  No alignment or rounding is needed.
            # ══════════════════════════════════════════════════════════
            header_start = (SILENCE_BITS + PREAMBLE_BITS) * spb

            if header_start + _HEADER_BITS * spb > len(data):
                raise ValueError(
                    "Audio file is too short — it does not contain a complete header.\n"
                    "Ensure the file was encoded with SocialDisk and is not truncated."
                )

            # ══════════════════════════════════════════════════════════
            #  STEP 3: Read 32-bit header → extract N (number of data bits)
            #
            #  Header uses: bit=1 → sync_freq, bit=0 → freq_zero
            #  This distinguishes it from data bits (bit=1 → freq_one)
            #  N = header_value XOR _HEADER_XOR_KEY
            # ══════════════════════════════════════════════════════════
            header_bits: list[int] = []
            pos = header_start
            for _ in range(_HEADER_BITS):
                chunk  = data[pos: pos + spb]
                p_sync = cls._fft_magnitude(chunk, _fs, _sr)
                p_zero = cls._fft_magnitude(chunk, _f0, _sr)
                header_bits.append(1 if p_sync > p_zero else 0)
                pos += spb

            header_val  = cls._bits_to_int(header_bits)
            n_data_bits = header_val ^ _HEADER_XOR_KEY

            # Validate N
            data_start = pos   # data start (immediately after header)
            available  = (len(data) - data_start) // spb

            if n_data_bits <= 0 or n_data_bits > available:
                raise ValueError(
                    f"Invalid header value (N={n_data_bits}, available={available} bits).\n"
                    "File is corrupted or encoded with a different version of SocialDisk."
                )

            # ══════════════════════════════════════════════════════════
            #  STEP 4: Read N data bits — FFT vectorized (very fast)
            #
            #  For each time frame (spb samples):
            #    mag0 = freq_zero power, mag1 = freq_one power
            #    Higher power wins (0 or 1)
            #
            #  Process all frames at once (vectorized) instead of a loop
            #  → 50-100× faster than a pure Python loop
            # ══════════════════════════════════════════════════════════
            data_segment = data[data_start: data_start + n_data_bits * spb]

            # Reshape to (n_data_bits, spb) for batch processing
            frames     = data_segment.reshape(n_data_bits, spb)
            win        = np.hanning(spb)
            frames_win = frames * win   # broadcast: (n_data_bits, spb)

            # FFT on all frames at once
            spectra = np.abs(np.fft.rfft(frames_win, axis=1))  # (n_data_bits, spb//2+1)
            freqs   = np.fft.rfftfreq(spb, 1.0 / _sr)

            # Find bin for each frequency (±2 bins for robustness)
            idx0 = int(np.argmin(np.abs(freqs - _f0)))
            idx1 = int(np.argmin(np.abs(freqs - _f1)))
            lo0, hi0 = max(0, idx0 - 2), min(spectra.shape[1], idx0 + 3)
            lo1, hi1 = max(0, idx1 - 2), min(spectra.shape[1], idx1 + 3)

            # Power of each frequency per frame
            mag0 = spectra[:, lo0:hi0].mean(axis=1)   # (n_data_bits,)
            mag1 = spectra[:, lo1:hi1].mean(axis=1)   # (n_data_bits,)

            # Bit decision: highest power wins
            bits_arr = (mag1 > mag0).astype(np.uint8)

            # ══════════════════════════════════════════════════════════
            #  STEP 5: Full decryption
            # ══════════════════════════════════════════════════════════
            return VaultCore.unpack_payload(bits_arr, password, ecc_symbols=_ecc)

        finally:
            if temp_wav and os.path.exists(temp_wav):
                os.remove(temp_wav)
