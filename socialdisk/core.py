"""
VaultCore — Main Encryption and Payload Core

Encoding Pipeline (pack_payload):
  Raw data
    → LZMA-9 maximum compression
    → AES-256-GCM encryption (PBKDF2 100k iterations)
    → Header + CRC32 for fast integrity check
    → Reed-Solomon ECC for error correction
    → Interleaving to break up burst errors
    → 3× repeated length header (Majority Voting)
    → Bit array ready for embedding

Decoding Pipeline (unpack_payload):
  Extracted bit array (after external majority voting)
    → De-interleaving
    → Reed-Solomon correction
    → CRC32 + Magic verification
    → AES-GCM decryption
    → LZMA decompression
    → Original data
"""
from __future__ import annotations

import hashlib
import lzma
import os
import random
import struct
import zlib

import numpy as np
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from reedsolo import RSCodec, ReedSolomonError


class VaultCore:
    """
    Multi-layer encryption and protection core.

    Class Attributes:
        MAGIC   : Format fingerprint for SocialDisk v2
        VERSION : Internal protocol version number
    """

    MAGIC   = b"IVLT"    # 4 bytes — format fingerprint
    VERSION = b"\x02"   # 1 byte  — protocol version

    # ------------------------------------------------------------------ #
    #  Secure Key Derivation (PBKDF2-SHA256)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
        """Derive an AES-256 key from a password and salt using PBKDF2-HMAC-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password.encode("utf-8"))

    # ------------------------------------------------------------------ #
    #  Byte Shuffling (Interleaving) against Burst Errors
    # ------------------------------------------------------------------ #
    @staticmethod
    def _interleave(data: bytes, seed_bytes: bytes, inverse: bool = False) -> bytes:
        """
        Shuffle bytes based on a key derived from the password.

        Output: same bytes in a shuffled (or restored) order that is reversible.
        Purpose: Convert clustered burst errors into distributed errors
                 that Reed-Solomon can correct more easily.
        """
        n   = len(data)
        rng = random.Random(int.from_bytes(seed_bytes[:8], "big"))
        idx = list(range(n))
        rng.shuffle(idx)
        out = bytearray(n)
        if not inverse:
            for i, j in enumerate(idx):
                out[j] = data[i]
        else:
            for i, j in enumerate(idx):
                out[i] = data[j]
        return bytes(out)

    # ------------------------------------------------------------------ #
    #  Full Encoding → Bit Array
    # ------------------------------------------------------------------ #
    @classmethod
    def pack_payload(
        cls,
        raw_data: bytes,
        password: str,
        ecc_symbols: int = 64,
    ) -> np.ndarray:
        """
        Pack raw data into a bit array ready for embedding.

        Args:
            raw_data:    Original data (any bytes).
            password:    Password for encryption and shuffle ordering.
            ecc_symbols: Number of Reed-Solomon symbols (more = higher correction = less capacity).

        Returns:
            np.ndarray of dtype uint8 containing 0/1 values (unpacked bits).
        """
        # 1. Maximum compression (LZMA preset=9 | EXTREME)
        compressed = lzma.compress(raw_data, preset=9 | lzma.PRESET_EXTREME)

        # 2. Generate random salt and nonce, then derive key
        salt       = os.urandom(16)
        nonce      = os.urandom(12)
        key        = cls._derive_key(password, salt)
        aesgcm     = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, compressed, None)

        # 3. Build the structured packet:
        #    envelope  = salt(16) + nonce(12) + ciphertext(N)
        #    crc       = CRC32(envelope)   — for fast integrity check
        #    full_pkt  = MAGIC(4) + VERSION(1) + len(envelope)(4) + crc(4) + envelope
        envelope    = salt + nonce + ciphertext
        crc         = struct.pack(">I", zlib.crc32(envelope) & 0xFFFFFFFF)
        env_len_hdr = struct.pack(">I", len(envelope))
        full_packet = cls.MAGIC + cls.VERSION + env_len_hdr + crc + envelope

        # 4. Reed-Solomon encoding for error correction
        rsc         = RSCodec(ecc_symbols)
        encoded_ecc = bytes(rsc.encode(full_packet))

        # 5. Interleaving with a key derived from the password
        seed        = hashlib.sha256(password.encode()).digest()
        interleaved = cls._interleave(encoded_ecc, seed, inverse=False)

        # 6. 3× repeated length header (Majority Voting on decoding)
        total_len    = len(interleaved)
        len_header   = struct.pack(">I", total_len) * 3
        final_stream = len_header + interleaved

        # 7. Convert to bit array (0/1)
        return np.unpackbits(np.frombuffer(final_stream, dtype=np.uint8))

    # ------------------------------------------------------------------ #
    #  Full Decoding ← Bit Array
    # ------------------------------------------------------------------ #
    @classmethod
    def unpack_payload(
        cls,
        bits: np.ndarray,
        password: str,
        ecc_symbols: int = 64,
    ) -> bytes:
        """
        Extract original data from a bit array (after external majority voting).

        Args:
            bits:        uint8 bit array extracted from the medium (after majority voting).
            password:    Same password used in pack_payload.
            ecc_symbols: Same number of Reed-Solomon symbols used in pack_payload.

        Returns:
            Original data as bytes.

        Raises:
            ValueError: On any failure in verification or correction stages.
        """
        raw_bytes = np.packbits(bits).tobytes()
        if len(raw_bytes) < 12:
            raise ValueError("Extracted data is too short or completely corrupted.")

        # 1. Read length via majority voting (3 repeated copies)
        try:
            l1, l2, l3 = struct.unpack(">III", raw_bytes[:12])
        except struct.error as exc:
            raise ValueError("Failed to read length header — data is corrupted.") from exc

        lengths   = [l1, l2, l3]
        total_len = max(set(lengths), key=lengths.count)   # majority

        if total_len <= 0 or 12 + total_len > len(raw_bytes):
            raise ValueError(
                f"Invalid packet size (read: {total_len}, "
                f"available: {len(raw_bytes) - 12} bytes)."
            )

        interleaved = raw_bytes[12 : 12 + total_len]

        # 2. De-interleaving
        seed        = hashlib.sha256(password.encode()).digest()
        encoded_ecc = cls._interleave(interleaved, seed, inverse=True)

        # 3. Reed-Solomon error correction
        rsc = RSCodec(ecc_symbols)
        try:
            decoded_pkt, _, _ = rsc.decode(encoded_ecc)
            decoded_pkt = bytes(decoded_pkt)
        except ReedSolomonError as exc:
            raise ValueError(
                "Corruption level exceeds Reed-Solomon capacity. "
                "Try increasing ecc_symbols or block size."
            ) from exc

        # 4. Verify magic bytes (fingerprint)
        if decoded_pkt[:4] != cls.MAGIC:
            raise ValueError(
                "File fingerprint mismatch — data is corrupted or password is wrong."
            )

        # 5. Extract length header and CRC (after MAGIC=4 + VERSION=1)
        offset = 5
        env_len, expected_crc = struct.unpack(">II", decoded_pkt[offset : offset + 8])
        envelope = decoded_pkt[offset + 8 : offset + 8 + env_len]

        # 6. Verify CRC32 for integrity
        actual_crc = zlib.crc32(envelope) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(
                f"CRC32 verification failed — data is corrupted "
                f"(expected: {expected_crc:#010x}, actual: {actual_crc:#010x})."
            )

        # 7. AES-256-GCM decryption
        salt_bytes = envelope[:16]
        nonce_data = envelope[16:28]
        ciphertext = envelope[28:]
        key        = cls._derive_key(password, salt_bytes)
        aesgcm     = AESGCM(key)
        try:
            compressed = aesgcm.decrypt(nonce_data, ciphertext, None)
        except Exception as exc:
            raise ValueError(
                "Decryption failed — wrong password or data is corrupted."
            ) from exc

        # 8. LZMA decompression
        try:
            return lzma.decompress(compressed)
        except lzma.LZMAError as exc:
            raise ValueError("LZMA decompression failed — data is internally corrupted.") from exc
