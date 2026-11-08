"""
HyperGrid Video Engine — مصفوفة بصرية عالية السعة للفيديو

الخوارزمية:
  ┌────────────────────────────────────────────────────────────────────┐
  │ 1. تحزيم البيانات → مصفوفة بتات (pack_payload)                   │
  │ 2. لكل إطار: تعبئة شبكة من المربعات block_size×block_size        │
  │    • قيم اللون: 35 (بت=0) و 220 (بت=1)                          │
  │      [اختيرتا لتكون خارج نطاق TV-Range YUV420p الذي يقطع 16/235] │
  │ 3. رسم حدود معايرة (أبيض/أسود) لضبط العتبة ديناميكياً           │
  │ 4. تكبير الشبكة إلى الدقة الكاملة (Nearest-Neighbor لا تنعيم)   │
  │ 5. حفظ كـ MP4 (mp4v codec)                                       │
  │                                                                    │
  │ الاستخراج:                                                         │
  │ 1. لكل إطار: أخذ عينة من مركز كل مربع (المنطقة الآمنة)          │
  │ 2. معايرة ديناميكية من حدود الإطار (تكيف مع تشوه ضغط المنصة)    │
  │ 3. تجميع البتات وفك التشفير                                       │
  └────────────────────────────────────────────────────────────────────┘

لماذا block_size ≥ 16?
  H.264 يستخدم ماكروبلوكات 16×16 بكسل. بلوك مساوٍ لحجم الماكروبلوك
  يعني أن المحتوى داخل البلوك مُعالَج كوحدة واحدة، مما يُقلل التشوه.

لماذا 35 و 220 (وليس 0 و 255)?
  MPEG/H.264 يستخدم نطاق TV-Range: Y=[16..235], Cb/Cr=[16..240]
  القيم 0 و255 تُقطَع إلى حدود النطاق.
  القيم 35 و220 تضمن هامش أمان من كلا الطرفَين.
"""
from __future__ import annotations

from typing import Optional

import cv2
import numpy as np

from instadisk.core import VaultCore
from instadisk.platforms import VideoProfile


class HyperGridVideoEngine:
    """
    محرك المصفوفة البصرية للفيديو.
    يُحوِّل أي ملف كبير إلى إطارات فيديو مُشفَّرة قابلة للتضمين في المنصات.
    """

    # قيم اللون الآمنة ضمن نطاق TV-Range YUV420p
    VAL_ZERO  = 35    # يُمثّل البت=0
    VAL_ONE   = 220   # يُمثّل البت=1
    MARGIN    = 2     # عدد البلوكات من كل جهة للمعايرة

    # ------------------------------------------------------------------ #
    #  الترميز (فيلم → بيانات)
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
        تحويل ملف بيانات إلى فيديو مُشفَّر.

        Args:
            output_video: مسار الفيديو الناتج (.mp4 مُوصى به).
            payload:      البيانات المراد تخزينها (bytes).
            password:     كلمة المرور للتشفير.
            profile:      ملف إعداد المنصة.
            fps:          يتجاوز profile.fps إن أُعطي.
            block_size:   يتجاوز profile.block_size إن أُعطي.
            ecc_symbols:  يتجاوز profile.ecc_symbols إن أُعطي.

        Returns:
            dict: إحصائيات الترميز.
        """
        _fps        = fps        or (profile.fps        if profile else 30)
        _block_size = block_size or (profile.block_size if profile else 16)
        _ecc        = ecc_symbols or (profile.ecc_symbols if profile else 128)
        _width      = profile.max_width  if profile else 1080
        _height     = profile.max_height if profile else 1920

        # --- تحزيم البيانات
        bits = VaultCore.pack_payload(payload, password, ecc_symbols=_ecc)

        # --- حساب السعة بالإطار
        grid_w    = _width  // _block_size
        grid_h    = _height // _block_size
        m         = cls.MARGIN
        data_cols = grid_w - 2 * m
        data_rows = grid_h - 2 * m
        bpf       = data_cols * data_rows   # bits per frame

        # --- توليد إطارات كافية (مع حشو بالأصفار)
        total_frames = max(1, int(np.ceil(len(bits) / bpf)))
        padded_bits  = np.zeros(total_frames * bpf, dtype=np.uint8)
        padded_bits[: len(bits)] = bits

        # --- فتح كاتب الفيديو
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(output_video, fourcc, _fps, (_width, _height))
        if not writer.isOpened():
            raise RuntimeError(
                f"تعذّر فتح ملف الكتابة: {output_video}\n"
                "تأكد من وجود الدليل وأن امتداد الملف .mp4"
            )

        for f_idx in range(total_frames):
            frame_grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)

            # --- منطقة المعايرة (حدود أبيض/أسود لضبط العتبة ديناميكياً)
            frame_grid[:m,  :, :] = cls.VAL_ONE   # أعلى → أبيض (VAL_ONE)
            frame_grid[-m:, :, :] = cls.VAL_ZERO  # أسفل → أسود (VAL_ZERO)
            frame_grid[:,  :m, :] = cls.VAL_ONE   # يسار → أبيض
            frame_grid[:, -m:, :] = cls.VAL_ZERO  # يمين → أسود

            # --- منطقة البيانات (مُضمَّنة بين الحدود)
            chunk    = padded_bits[f_idx * bpf : (f_idx + 1) * bpf]
            chunk_2d = chunk.reshape((data_rows, data_cols))
            val_grid = np.where(chunk_2d == 1, cls.VAL_ONE, cls.VAL_ZERO).astype(np.uint8)

            frame_grid[m : -m, m : -m, 0] = val_grid
            frame_grid[m : -m, m : -m, 1] = val_grid
            frame_grid[m : -m, m : -m, 2] = val_grid

            # --- تكبير إلى الدقة الكاملة (Nearest-Neighbor — لا تنعيم حواف)
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
    #  فك الترميز (فيلم → بيانات)
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
        استرجاع الملف الأصلي من فيديو (حتى بعد ضغط المنصة).

        يستخدم معايرة ديناميكية لكل إطار (white_ref/black_ref) للتكيف
        مع تشوهات السطوع التي تُسبّبها إعادة ترميز H.264 للمنصة.
        """
        _block_size = block_size or (profile.block_size if profile else 16)
        _ecc        = ecc_symbols or (profile.ecc_symbols if profile else 128)
        _width      = profile.max_width  if profile else 1080
        _height     = profile.max_height if profile else 1920

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"تعذّر فتح الفيديو: {video_path}")

        grid_w = _width  // _block_size
        grid_h = _height // _block_size
        m      = cls.MARGIN
        all_bits: list[np.ndarray] = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # --- إعادة ضبط الحجم (قد تُصغّره بعض المنصات)
            if frame.shape[1] != _width or frame.shape[0] != _height:
                frame = cv2.resize(
                    frame, (_width, _height), interpolation=cv2.INTER_LINEAR
                )

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # --- أخذ عينة من مركز كل مربع (المنطقة الآمنة البعيدة عن الحواف)
            half    = _block_size // 2
            centers = gray[half :: _block_size, half :: _block_size]

            # --- تحقق من الأبعاد
            if centers.shape[0] < grid_h or centers.shape[1] < grid_w:
                continue
            centers = centers[:grid_h, :grid_w]

            # --- معايرة ديناميكية من حدود الإطار
            white_ref = float(np.mean(centers[:m, :]))
            black_ref = float(np.mean(centers[-m:, :]))

            # تخطي الإطارات التي تلف فيها حدود المعايرة
            if abs(white_ref - black_ref) < 30:
                continue

            thresh = (white_ref + black_ref) / 2.0

            # --- استخراج بتات منطقة البيانات
            data_zone  = centers[m : -m, m : -m]
            frame_bits = (data_zone > thresh).astype(np.uint8).flatten()
            all_bits.append(frame_bits)

        cap.release()

        if not all_bits:
            raise ValueError(
                "لم تُقرأ أي إطارات صالحة.\n"
                "تأكد من صحة الفيديو وتطابق معاملات block_size مع تلك المستخدمة عند الترميز."
            )

        combined = np.concatenate(all_bits)
        return VaultCore.unpack_payload(combined, password, ecc_symbols=_ecc)
