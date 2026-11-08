"""
VaultCore — نواة التشفير والتحزيم الرئيسية

Pipeline الترميز (pack_payload):
  البيانات الخام
    → LZMA-9 ضغط أقصى
    → AES-256-GCM تشفير (PBKDF2 100k iteration)
    → Header + CRC32 للتحقق السريع
    → Reed-Solomon ECC لتصحيح الأخطاء
    → Interleaving لتفكيك أخطاء الحزمة (Burst Errors)
    → رأس طول مكرر 3× (Majority Voting)
    → مصفوفة بتات جاهزة للتضمين

Pipeline فك الترميز (unpack_payload):
  مصفوفة بتات مستخرجة (بعد التصويت خارجياً)
    → De-interleaving
    → Reed-Solomon تصحيح
    → تحقق CRC32 + Magic
    → AES-GCM فك تشفير
    → LZMA فك ضغط
    → البيانات الأصلية
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
    نواة التشفير والحماية متعددة الطبقات.

    السمات الثابتة:
        MAGIC   : بصمة التعرف على تنسيق InstaDisk v2
        VERSION : رقم إصدار البروتوكول الداخلي
    """

    MAGIC   = b"IVLT"    # 4 bytes — بصمة الصيغة
    VERSION = b"\x02"   # 1 byte  — إصدار البروتوكول

    # ------------------------------------------------------------------ #
    #  اشتقاق المفتاح الآمن (PBKDF2-SHA256)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _derive_key(password: str, salt: bytes, iterations: int = 100_000) -> bytes:
        """اشتقاق مفتاح AES-256 من كلمة المرور والملح باستخدام PBKDF2-HMAC-SHA256."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=iterations,
        )
        return kdf.derive(password.encode("utf-8"))

    # ------------------------------------------------------------------ #
    #  تشويش البايتات (Interleaving) ضد Burst Errors
    # ------------------------------------------------------------------ #
    @staticmethod
    def _interleave(data: bytes, seed_bytes: bytes, inverse: bool = False) -> bytes:
        """
        بعثرة البايتات بناءً على مفتاح مشتق من كلمة المرور.

        المُخرج: نفس البايتات بترتيب مختلط (أو مُعاد) قابل للعكس.
        الغرض:  تحويل أخطاء الحزمة المتكتلة (Burst) إلى أخطاء موزعة
                 يمكن لـ Reed-Solomon تصحيحها بسهولة.
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
    #  الترميز الكامل → مصفوفة بتات
    # ------------------------------------------------------------------ #
    @classmethod
    def pack_payload(
        cls,
        raw_data: bytes,
        password: str,
        ecc_symbols: int = 64,
    ) -> np.ndarray:
        """
        تحزيم البيانات الخام في مصفوفة بتات جاهزة للتضمين.

        Args:
            raw_data:    البيانات الأصلية (أي bytes).
            password:    كلمة المرور للتشفير وترتيب التشويش.
            ecc_symbols: عدد رموز Reed-Solomon (أكثر = تصحيح أعلى = سعة أقل).

        Returns:
            np.ndarray بنوع uint8 يحتوي على قيم 0/1 (unpacked bits).
        """
        # 1. ضغط أقصى (LZMA preset=9 | EXTREME)
        compressed = lzma.compress(raw_data, preset=9 | lzma.PRESET_EXTREME)

        # 2. توليد ملح وnonce عشوائيَّين واشتقاق المفتاح
        salt       = os.urandom(16)
        nonce      = os.urandom(12)
        key        = cls._derive_key(password, salt)
        aesgcm     = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, compressed, None)

        # 3. بناء الحزمة المُصفَّفة:
        #    envelope  = salt(16) + nonce(12) + ciphertext(N)
        #    crc       = CRC32(envelope)   — للتحقق السريع
        #    full_pkt  = MAGIC(4) + VERSION(1) + len(envelope)(4) + crc(4) + envelope
        envelope    = salt + nonce + ciphertext
        crc         = struct.pack(">I", zlib.crc32(envelope) & 0xFFFFFFFF)
        env_len_hdr = struct.pack(">I", len(envelope))
        full_packet = cls.MAGIC + cls.VERSION + env_len_hdr + crc + envelope

        # 4. ترميز Reed-Solomon لتصحيح الأخطاء
        rsc         = RSCodec(ecc_symbols)
        encoded_ecc = bytes(rsc.encode(full_packet))

        # 5. تشويش (Interleaving) بمفتاح مشتق من كلمة المرور
        seed        = hashlib.sha256(password.encode()).digest()
        interleaved = cls._interleave(encoded_ecc, seed, inverse=False)

        # 6. رأس الطول مكرر 3× (Majority Voting عند فك التشفير)
        total_len    = len(interleaved)
        len_header   = struct.pack(">I", total_len) * 3
        final_stream = len_header + interleaved

        # 7. تحويل إلى مصفوفة بتات (0/1)
        return np.unpackbits(np.frombuffer(final_stream, dtype=np.uint8))

    # ------------------------------------------------------------------ #
    #  فك الترميز الكامل ← مصفوفة بتات
    # ------------------------------------------------------------------ #
    @classmethod
    def unpack_payload(
        cls,
        bits: np.ndarray,
        password: str,
        ecc_symbols: int = 64,
    ) -> bytes:
        """
        استخراج البيانات الأصلية من مصفوفة بتات (بعد التصويت بالأغلبية خارجياً).

        Args:
            bits:        مصفوفة بتات uint8 مستخرجة من الوسيط (بعد majority voting).
            password:    نفس كلمة المرور المستخدمة في pack_payload.
            ecc_symbols: نفس عدد رموز Reed-Solomon المستخدمة في pack_payload.

        Returns:
            البيانات الأصلية كـ bytes.

        Raises:
            ValueError: عند أي إخفاق في مراحل التحقق أو التصحيح.
        """
        raw_bytes = np.packbits(bits).tobytes()
        if len(raw_bytes) < 12:
            raise ValueError("البيانات المستخرجة قصيرة جداً أو تالفة تماماً.")

        # 1. قراءة الطول عبر التصويت بالأغلبية (3 نسخ مكررة)
        try:
            l1, l2, l3 = struct.unpack(">III", raw_bytes[:12])
        except struct.error as exc:
            raise ValueError("فشل قراءة رأس الطول — البيانات تالفة.") from exc

        lengths   = [l1, l2, l3]
        total_len = max(set(lengths), key=lengths.count)   # الأغلبية

        if total_len <= 0 or 12 + total_len > len(raw_bytes):
            raise ValueError(
                f"حجم الحزمة غير صالح (قُرئ: {total_len}, "
                f"المتاح: {len(raw_bytes) - 12} بايت)."
            )

        interleaved = raw_bytes[12 : 12 + total_len]

        # 2. إلغاء التشويش (De-interleaving)
        seed        = hashlib.sha256(password.encode()).digest()
        encoded_ecc = cls._interleave(interleaved, seed, inverse=True)

        # 3. تصحيح الأخطاء بـ Reed-Solomon
        rsc = RSCodec(ecc_symbols)
        try:
            decoded_pkt, _, _ = rsc.decode(encoded_ecc)
            decoded_pkt = bytes(decoded_pkt)
        except ReedSolomonError as exc:
            raise ValueError(
                "نسبة التلف أعلى من طاقة Reed-Solomon. "
                "جرب زيادة ecc_symbols أو حجم البلوك."
            ) from exc

        # 4. التحقق من البصمة (Magic Bytes)
        if decoded_pkt[:4] != cls.MAGIC:
            raise ValueError(
                "بصمة الملف غير متطابقة — البيانات تالفة أو كلمة المرور خاطئة."
            )

        # 5. استخراج رأس الطول والـ CRC (بعد MAGIC=4 + VERSION=1)
        offset = 5
        env_len, expected_crc = struct.unpack(">II", decoded_pkt[offset : offset + 8])
        envelope = decoded_pkt[offset + 8 : offset + 8 + env_len]

        # 6. التحقق من CRC32 للسلامة
        actual_crc = zlib.crc32(envelope) & 0xFFFFFFFF
        if actual_crc != expected_crc:
            raise ValueError(
                f"فشل التحقق من CRC32 — البيانات تالفة "
                f"(متوقع: {expected_crc:#010x}, فعلي: {actual_crc:#010x})."
            )

        # 7. فك التشفير AES-256-GCM
        salt_bytes = envelope[:16]
        nonce_data = envelope[16:28]
        ciphertext = envelope[28:]
        key        = cls._derive_key(password, salt_bytes)
        aesgcm     = AESGCM(key)
        try:
            compressed = aesgcm.decrypt(nonce_data, ciphertext, None)
        except Exception as exc:
            raise ValueError(
                "فشل فك التشفير — كلمة المرور خاطئة أو البيانات تالفة."
            ) from exc

        # 8. فك ضغط LZMA
        try:
            return lzma.decompress(compressed)
        except lzma.LZMAError as exc:
            raise ValueError("فشل فك ضغط LZMA — البيانات داخلياً تالفة.") from exc
