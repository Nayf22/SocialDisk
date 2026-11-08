"""
DCT Image Steganography Engine — الإخفاء الترددي غير المرئي في الصور

الخوارزمية (Differential Mid-Band DCT Steganography):
  ┌─────────────────────────────────────────────────────────────────┐
  │ 1. تحويل الصورة إلى YCrCb واستخراج قناة الإضاءة Y             │
  │ 2. تقسيم القناة إلى كتل 8×8 بكسل                             │
  │ 3. ترتيب الكتل عشوائياً بناءً على كلمة المرور (للأمان)        │
  │ 4. لكل بت في البيانات:                                         │
  │    • تطبيق DCT-2D على الكتلة                                   │
  │    • قراءة معاملتَي التردد المتوسط:                            │
  │        POS_A = (3,2)  ،  POS_B = (2,3)                        │
  │    • bit=1 → c[A] = avg + δ/2  ,  c[B] = avg - δ/2            │
  │    • bit=0 → c[A] = avg - δ/2  ,  c[B] = avg + δ/2            │
  │    • IDCT-2D لاسترجاع البكسلات                                │
  │ 5. تكرار كل بت `redundancy` مرات مكانياً                       │
  └─────────────────────────────────────────────────────────────────┘

لماذا التردد المتوسط (Mid-Band)?
  - التردد المنخفض (DC + مجاورات): حساس بصرياً، ضغط JPEG يحافظ عليه
  - التردد العالي (زوايا الكتلة): أقل بصرياً، لكن JPEG يمحوه تماماً
  - التردد المتوسط: وسط ذهبي — JPEG يُخففه لكن لا يمحوه، وهو غير محسوس

لماذا الفرق الديناميكي (Differential)?
  - المقارنة بين معاملَتين بدلاً من قيمة مطلقة
  - يلغي تأثير إزاحة DC الكلية (التغييرات العامة في السطوع)
  - أكثر صموداً أمام عمليات المعالجة الكلية (تعديل السطوع/التباين)
"""
from __future__ import annotations

import hashlib
import random
from typing import Optional

import cv2
import numpy as np
from scipy.fftpack import dct, idct

from instadisk.core import VaultCore
from instadisk.platforms import ImageProfile


class DCTImageEngine:
    """
    محرك الإخفاء الترددي الفارقي في الصور (Differential DCT Steganography).

    Attributes:
        POS_A: موضع معامل DCT الأول في التردد المتوسط (row=3, col=2)
        POS_B: موضع معامل DCT الثاني في التردد المتوسط (row=2, col=3)
              — الموضعَان متناظران في التردد المتوسط لقيمة تكميم متقاربة
    """

    POS_A = (3, 2)   # معامل Mid-Band الأول
    POS_B = (2, 3)   # معامل Mid-Band الثاني (تردد مماثل)

    # ------------------------------------------------------------------ #
    #  تحويلات DCT ثنائية الأبعاد
    # ------------------------------------------------------------------ #
    @staticmethod
    def _dct2(block: np.ndarray) -> np.ndarray:
        """تطبيق DCT-2D مُعياريّ (ortho norm) على كتلة 8×8."""
        return dct(dct(block.T, norm="ortho").T, norm="ortho")

    @staticmethod
    def _idct2(block: np.ndarray) -> np.ndarray:
        """تطبيق IDCT-2D مُعياريّ (ortho norm) — عكس _dct2."""
        return idct(idct(block.T, norm="ortho").T, norm="ortho")

    # ------------------------------------------------------------------ #
    #  ترتيب الكتل
    # ------------------------------------------------------------------ #
    @classmethod
    def _get_block_order(cls, h: int, w: int, password: str) -> list[tuple[int, int]]:
        """
        إنشاء قائمة بالكتل 8×8 مرتبة عشوائياً بكلمة المرور.

        الغرض المزدوج:
          1. أمان: لا يعرف المهاجم أين تقع البيانات
          2. توزيع: يوزع الأخطاء بالتساوي إن تلفت منطقة معينة
        """
        blocks = [(r, c) for r in range(0, h, 8) for c in range(0, w, 8)]
        seed   = int.from_bytes(hashlib.sha256(password.encode()).digest()[:8], "big")
        rng    = random.Random(seed)
        rng.shuffle(blocks)
        return blocks

    # ------------------------------------------------------------------ #
    #  التضمين
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
        تضمين بيانات داخل صورة بطريقة DCT الفارقية.

        Args:
            image_path:  مسار صورة الغلاف الأصلية (أي صيغة يقرأها OpenCV).
            output_path: مسار حفظ الصورة المُعدَّلة (يُوصى بـ .jpg).
            payload:     البيانات السرية (bytes).
            password:    كلمة المرور.
            profile:     ملف إعداد المنصة (إن أُعطي، يُحدد delta/ecc/redundancy تلقائياً).
            delta:       يتجاوز profile.delta إن أُعطي.
            ecc_symbols: يتجاوز profile.ecc_symbols إن أُعطي.
            redundancy:  يتجاوز profile.redundancy إن أُعطي.

        Returns:
            dict: إحصائيات التضمين التفصيلية.

        Raises:
            FileNotFoundError: إن لم تُوجد الصورة.
            ValueError:        إن كانت البيانات أكبر من سعة الصورة.
        """
        # --- تحديد المعاملات النهائية (أولوية: kwarg > profile > افتراضي)
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

        # --- تحميل الصورة
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"لم يُعثر على الصورة: {image_path}")

        # --- إعادة التحجيم إلى العرض الأقصى للمنصة (محافظاً على النسبة)
        h, w = img.shape[:2]
        if w > _max_width:
            new_h = int(h * _max_width / w)
            new_h = max(8, (new_h // 8) * 8)   # مضاعف 8
            img   = cv2.resize(img, (_max_width, new_h), interpolation=cv2.INTER_AREA)

        # --- قص إلى أقرب مضاعف 8 في كلا البُعدَين
        h = (img.shape[0] // 8) * 8
        w = (img.shape[1] // 8) * 8
        img = img[:h, :w]

        # --- تحزيم البيانات
        bits = VaultCore.pack_payload(payload, password, ecc_symbols=_ecc)

        # --- تطبيق التكرار المكاني (Spatial Redundancy)
        # كل بت يُكرَّر _redundancy مرة في كتل متتالية مختلفة
        redundant_bits = np.repeat(bits, _redundancy)

        # --- التحقق من السعة
        max_blocks = (h // 8) * (w // 8)
        if len(redundant_bits) > max_blocks:
            max_safe_bytes = max(
                0,
                (max_blocks // _redundancy // 8) - _ecc - 60
            )
            raise ValueError(
                f"البيانات أكبر من سعة الصورة ({_max_width}×{h}).\n"
                f"الحد الأقصى الموصى به لهذه الصورة: ~{max_safe_bytes} بايت.\n"
                f"جرب: صورة أكبر | تقليل ecc_symbols | تقليل redundancy."
            )

        # --- التحويل إلى YCrCb والتعديل على قناة Y
        ycrcb     = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y_channel = ycrcb[:, :, 0]
        all_blocks = cls._get_block_order(h, w, password)

        for idx, bit in enumerate(redundant_bits):
            if idx >= len(all_blocks):
                break
            r, c   = all_blocks[idx]
            block  = y_channel[r : r + 8, c : c + 8] - 128.0
            dct_b  = cls._dct2(block)

            # --- تعديل الفرق بين المعاملتَين لترميز البت
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

        # --- إعادة بناء الصورة وحفظها بجودة 95%
        # (جودة 95% تُقلل الضغط الذاتي لأداة الحفظ، لتترك هامشاً لضغط المنصة)
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
    #  الاستخراج
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
        استخراج البيانات المُضمَّنة من صورة (حتى بعد ضغط المنصة).

        يقرأ فرق المعاملات من كل كتلة بنفس الترتيب المُستخدم في embed،
        ثم يُجري تصويتاً بالأغلبية لإزالة التكرار المكاني.

        ⚠️ يجب أن تتطابق قيم ecc_symbols وredundancy مع تلك المستخدمة عند التضمين.
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
            raise FileNotFoundError(f"لم يُعثر على الصورة: {image_path}")

        h = (img.shape[0] // 8) * 8
        w = (img.shape[1] // 8) * 8
        img = img[:h, :w]

        ycrcb     = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y_channel = ycrcb[:, :, 0]
        all_blocks = cls._get_block_order(h, w, password)

        # --- قراءة البت من كل كتلة عبر إشارة الفرق
        raw_bits: list[int] = []
        for r, c in all_blocks:
            block  = y_channel[r : r + 8, c : c + 8] - 128.0
            dct_b  = cls._dct2(block)
            diff   = dct_b[cls.POS_A] - dct_b[cls.POS_B]
            raw_bits.append(1 if diff > 0 else 0)

        # --- إزالة التكرار المكاني بالتصويت بالأغلبية
        usable     = (len(raw_bits) // _redundancy) * _redundancy
        groups     = np.array(raw_bits[:usable], dtype=np.uint8).reshape(-1, _redundancy)
        voted_bits = (np.sum(groups, axis=1) > _redundancy // 2).astype(np.uint8)

        return VaultCore.unpack_payload(voted_bits, password, ecc_symbols=_ecc)
