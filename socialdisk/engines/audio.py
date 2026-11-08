"""
Acoustic FSK Engine — المودم الصوتي المقاوم لضغط AAC/Opus

الخوارزمية (Frequency Shift Keying — FSK) المُعاد تصميمها:
  ┌─────────────────────────────────────────────────────────────────┐
  │ هيكل الإشارة المُرمَّزة (Protocol Frame):                      │
  │                                                                  │
  │  [صمت 0.25s] [preamble SYNC 0.5s] [header 32 بت] [data N بت] [صمت 0.25s] │
  │                                                                  │
  │  preamble: نغمة sync_freq مستمرة 0.5s — للكشف عن بداية الإشارة │
  │  header:   32 بت تُرسَل بتردد SYNC نفسه (بت=1) أو freq_zero (بت=0) │
  │            تُمثِّل عدد بتات البيانات (N) مُشفَّراً بـ XOR لإخفائه │
  │  data:     N بت — bit=0 → freq_zero، bit=1 → freq_one           │
  │                                                                  │
  │ فك الترميز:                                                      │
  │  1. كشف بداية preamble (أول نافذة ذات قوة SYNC عالية)          │
  │  2. تخطي preamble (0.5s ثابت)                                   │
  │  3. قراءة 32 بت header → استخراج N                             │
  │  4. قراءة N بت بيانات                                           │
  │  5. VaultCore.unpack_payload لفك التشفير                        │
  └─────────────────────────────────────────────────────────────────┘

لماذا header مضمَّن في الإشارة؟
  الكشف عن نهاية preamble بالـ FFT يفشل لأن هارمونيكات ترددات البيانات
  (1500 Hz / 2700 Hz) قد تُولِّد مكوناً عند تردد SYNC (900 Hz)،
  مما يجعل خوارزمية "آخر ظهور للـ SYNC" غير موثوقة.
  الحل: نضمِّن N مباشرة في الإشارة لنعرف حجم البيانات بدقة مطلقة.

لماذا ترددات 1500/2700/900 Hz؟
  - AAC عند 128kbps: نطاق 20Hz–16kHz (آمن)
  - Opus عند 32kbps: نطاق 400Hz–7700Hz (آمن)
  - بُعد 1200Hz بين f0/f1 يُقلل الخلط عند ضغط قوي
  - 900 Hz للـ SYNC: بعيد عن 1500/2700 ولا يتداخل
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
#  ثوابت بروتوكول الإطار
# ───────────────────────────────────────────────────────────────────
_HEADER_BITS    = 32          # عدد بتات حقل header (يُخزن N بت البيانات)
_HEADER_XOR_KEY = 0xA5C3E1F7  # مفتاح XOR لإخفاء قيمة N (تجنب أنماط متكررة)
_PREAMBLE_DUR   = 0.5         # مدة نغمة SYNC بالثانية
_SILENCE_DUR    = 0.25        # مدة الصمت قبل/بعد الإشارة


class AcousticFSKEngine:
    """
    محرك المودم الصوتي (Acoustic FSK).
    يُحوِّل البيانات إلى موجات صوتية بترددات مسموعة وآمنة من ضغط المنصة.

    هيكل الإشارة (Protocol Frame):
        [صمت 0.25s] → [SYNC preamble 0.5s] → [32-bit header] → [data bits] → [صمت 0.25s]

    حيث header = عدد بتات البيانات (N) مُشفَّر بـ XOR، مُرسَل باستخدام:
        بت=1 → نغمة sync_freq (نفس الـ preamble)
        بت=0 → نغمة freq_zero
    """

    # ------------------------------------------------------------------ #
    #  مساعد توليد النغمات مع Hanning fade-in/out
    # ------------------------------------------------------------------ #
    @staticmethod
    def _make_tone(
        freq: float,
        duration: float,
        sample_rate: int,
        amplitude: float = 0.85,
    ) -> np.ndarray:
        """
        توليد نغمة جيبية نقية مع تلاشٍ ناعم (Hanning window على أطراف 5%).
        التلاشي يمنع الطقطقة (click artifact) عند الانتقال بين النغمات.
        """
        n       = max(1, int(sample_rate * duration))
        t       = np.linspace(0, duration, n, endpoint=False)
        signal  = amplitude * np.sin(2.0 * np.pi * freq * t)
        fade    = max(2, n // 20)
        signal[:fade]  *= np.linspace(0.0, 1.0, fade)
        signal[-fade:] *= np.linspace(1.0, 0.0, fade)
        return signal.astype(np.float32)

    # ------------------------------------------------------------------ #
    #  مساعد حساب قوة التردد عبر FFT (vectorized)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _fft_magnitude(
        samples: np.ndarray,
        target_freq: float,
        sample_rate: int,
    ) -> float:
        """
        حساب قوة تردد معين عبر FFT مع Hanning window لتقليل spectral leakage.
        يأخذ متوسط ±2 bin للحصول على قراءة أكثر استقراراً.
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
    #  ترميز 32-bit integer إلى قائمة بتات (MSB first)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _int_to_bits(value: int, n_bits: int = 32) -> list[int]:
        """تحويل عدد صحيح إلى قائمة بتات بترتيب MSB أولاً."""
        return [(value >> (n_bits - 1 - i)) & 1 for i in range(n_bits)]

    # ------------------------------------------------------------------ #
    #  فك ترميز قائمة بتات إلى integer (MSB first)
    # ------------------------------------------------------------------ #
    @staticmethod
    def _bits_to_int(bits: list[int]) -> int:
        """تحويل قائمة بتات (MSB أولاً) إلى عدد صحيح."""
        result = 0
        for b in bits:
            result = (result << 1) | int(b)
        return result

    # ------------------------------------------------------------------ #
    #  الترميز: بيانات → WAV
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
        تحويل البيانات إلى ملف WAV مُشفَّر بـ FSK.

        هيكل الإشارة المُولَّدة:
            [صمت 0.25s] [SYNC 0.5s] [32-bit header] [N بت بيانات] [صمت 0.25s]

        حيث header = (N XOR _HEADER_XOR_KEY) مُرسَل بـ SYNC/f0 بدلاً من f0/f1
        حتى لا يتداخل مع نمط البيانات.

        Args:
            output_wav:  مسار ملف الصوت الناتج (.wav).
            payload:     البيانات السرية (bytes).
            password:    كلمة المرور.
            profile:     ملف إعداد المنصة (يُحدد الترددات والسرعة).
            ecc_symbols: يتجاوز profile.ecc_symbols إن أُعطي.

        Returns:
            dict: إحصائيات الملف الصوتي.
        """
        _ecc  = ecc_symbols or (profile.ecc_symbols if profile else 64)
        _sr   = profile.sample_rate if profile else 44100
        _baud = profile.baud_rate   if profile else 150
        _f0   = profile.freq_zero   if profile else 1500.0
        _f1   = profile.freq_one    if profile else 2700.0
        _fs   = profile.sync_freq   if profile else 900.0

        # --- تحزيم البيانات → بتات
        data_bits    = VaultCore.pack_payload(payload, password, ecc_symbols=_ecc)
        n_data_bits  = len(data_bits)
        bit_duration = 1.0 / _baud

        spb = _sr // _baud  # عدد العينات لكل بت (294 عند 44100/150)

        # --- توليد النغمات الأساسية (مُولَّدة مسبقاً لكفاءة أعلى)
        tone0     = cls._make_tone(_f0, bit_duration, _sr)   # بيانات: بت=0
        tone1     = cls._make_tone(_f1, bit_duration, _sr)   # بيانات: بت=1
        tone_sync = cls._make_tone(_fs, bit_duration, _sr)   # header/preamble: بت=1

        # --- header = (n_data_bits XOR _HEADER_XOR_KEY) — 32 بت MSB أولاً
        header_val  = n_data_bits ^ _HEADER_XOR_KEY
        header_bits = cls._int_to_bits(header_val, _HEADER_BITS)

        # --- حساب أحجام القطع بوحدة بتات (spb عينة لكل بت)
        #   هذا يضمن أن كل حدٍّ في الإشارة يقع عند مضاعف دقيق لـ spb،
        #   مما يُلغي الحاجة لأي محاذاة عند فك الترميز.
        #
        #   SILENCE_BITS = عدد البتات للصمت (أقرب عدد صحيح لـ 0.25s)
        #   PREAMBLE_BITS = عدد البتات للـ preamble (أقرب عدد صحيح لـ 0.5s)
        #
        SILENCE_BITS  = max(1, round(_sr * _SILENCE_DUR  / spb))  # ≈37 بت
        PREAMBLE_BITS = max(1, round(_sr * _PREAMBLE_DUR / spb))  # ≈75 بت

        # --- بناء الإشارة الكاملة (كل عنصر = نغمة بمقدار spb عينة)
        parts: list[np.ndarray] = []

        # صمت بداية (SILENCE_BITS نغمة صفرية)
        for _ in range(SILENCE_BITS):
            parts.append(np.zeros(spb, dtype=np.float32))

        # preamble SYNC (PREAMBLE_BITS نغمة بتردد SYNC)
        for _ in range(PREAMBLE_BITS):
            parts.append(tone_sync)

        # header bits (بت=1 → sync_freq، بت=0 → freq_zero)
        # استخدام sync_freq للـ header يُميِّزه عن بيانات البيانات (التي تستخدم f0/f1)
        for b in header_bits:
            parts.append(tone_sync if b == 1 else tone0)

        # data bits (بت=1 → freq_one، بت=0 → freq_zero)
        for b in data_bits:
            parts.append(tone1 if b == 1 else tone0)

        # صمت نهاية (SILENCE_BITS نغمة صفرية)
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
    #  فك الترميز: WAV/MP4 → بيانات
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
        استخراج البيانات من ملف صوتي WAV أو فيديو MP4.

        خطوات فك الترميز:
          1. إن كان المدخل MP4: استخراج الصوت عبر ffmpeg
          2. كشف بداية preamble SYNC (أول نافذة ذات قوة عالية)
          3. تخطي preamble (0.5s ثابت) للوصول إلى header
          4. قراءة 32 بت header → استخراج N (عدد بتات البيانات)
          5. قراءة N بت بيانات (FFT vectorized)
          6. VaultCore.unpack_payload لفك التشفير

        Args:
            media_path:  مسار الملف الصوتي (.wav) أو الفيديو (.mp4/.mkv/...).
            password:    كلمة المرور.
            profile:     ملف إعداد المنصة.
            ecc_symbols: يتجاوز profile.ecc_symbols إن أُعطي.

        Returns:
            البيانات المستخرجة (bytes).
        """
        _ecc  = ecc_symbols or (profile.ecc_symbols if profile else 64)
        _sr   = profile.sample_rate if profile else 44100
        _baud = profile.baud_rate   if profile else 150
        _f0   = profile.freq_zero   if profile else 1500.0
        _f1   = profile.freq_one    if profile else 2700.0
        _fs   = profile.sync_freq   if profile else 900.0

        # --- استخراج الصوت من فيديو عبر ffmpeg إن لزم
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
                    "فشل استخراج الصوت من الفيديو.\n"
                    "تأكد من تثبيت ffmpeg وإضافته إلى PATH."
                )
            target = temp_wav
        else:
            target = media_path

        try:
            sr_read, raw_data = wavfile.read(target)

            # --- تحويل إلى mono float32 مُطبَّع إلى [-1, 1]
            if raw_data.ndim > 1:
                raw_data = raw_data[:, 0]
            data = raw_data.astype(np.float32)
            max_val = np.abs(data).max()
            if max_val > 0:
                data = data / max_val

            # --- إعادة أخذ العينات إن اختلف معدل التسجيل
            if sr_read != _sr:
                from scipy.signal import resample_poly
                from math import gcd
                g    = gcd(int(_sr), int(sr_read))
                up   = int(_sr)     // g
                dn   = int(sr_read) // g
                data = resample_poly(data, up, dn).astype(np.float32)

            spb = _sr // _baud   # عدد العينات لكل بت / نغمة

            # حساب SILENCE_BITS و PREAMBLE_BITS بنفس طريقة encode_wav
            # (يجب أن تكون متطابقة تماماً حتى تتحقق المحاذاة)
            SILENCE_BITS  = max(1, round(_sr * _SILENCE_DUR  / spb))  # ≈37 بت
            PREAMBLE_BITS = max(1, round(_sr * _PREAMBLE_DUR / spb))  # ≈75 بت

            # ══════════════════════════════════════════════════════════
            #  STEP 1: التحقق من وجود preamble (SYNC) وجودته
            #
            #  نمسح نطاق الـ SILENCE المتوقع للتحقق من أن الإشارة
            #  بدأت بشكل صحيح. نستخدم هذا للكشف المبكر عن أخطاء
            #  في الملف (ملف خاطئ / غير مُرمَّز / تالف).
            #
            #  لا نستخدم نتيجة هذا الكشف لتحديد بداية header،
            #  لأن SILENCE_BITS وPREAMBLE_BITS ثابتان ومعروفان مسبقاً.
            # ══════════════════════════════════════════════════════════
            # نطاق البحث عن preamble: من SILENCE_BITS إلى SILENCE_BITS+PREAMBLE_BITS
            preamble_region_start = SILENCE_BITS * spb
            preamble_region_end   = (SILENCE_BITS + PREAMBLE_BITS) * spb

            if preamble_region_end > len(data):
                raise ValueError(
                    "الملف الصوتي قصير جداً — يجب أن يحتوي على preamble SYNC.\n"
                    "تأكد أن الملف مُرمَّز بـ socialdisk وغير مقطوع."
                )

            # قياس قوة SYNC في منتصف الـ preamble المتوقع (للتحقق فقط)
            mid_preamble = preamble_region_start + (PREAMBLE_BITS // 2) * spb
            chunk_mid    = data[mid_preamble: mid_preamble + spb]
            sync_power_mid = cls._fft_magnitude(chunk_mid, _fs, _sr)

            # قياس قوة SYNC في منتصف الـ SILENCE المتوقع قبله
            mid_silence  = (SILENCE_BITS // 2) * spb
            chunk_sil    = data[mid_silence: mid_silence + spb]
            sync_power_sil = cls._fft_magnitude(chunk_sil, _fs, _sr)

            # يجب أن تكون قوة SYNC في preamble أعلى بكثير من الصمت
            if sync_power_mid < 0.5 or (sync_power_sil > 0 and sync_power_mid < sync_power_sil * 2.0):
                raise ValueError(
                    "لم يُعثر على نغمة المزامنة (preamble) في الموضع المتوقع.\n"
                    "تأكد أن الملف مُرمَّز بـ socialdisk."
                )

            # ══════════════════════════════════════════════════════════
            #  STEP 2: تحديد بداية header بدقة مطلقة
            #
            #  بداية header = (SILENCE_BITS + PREAMBLE_BITS) * spb
            #  هذا ثابت ومتطابق مع encode_wav تماماً، لأن كلاهما
            #  يستخدم نفس الصيغة لحساب SILENCE_BITS وPREAMBLE_BITS.
            #  لا توجد حاجة لأي محاذاة أو تقريب.
            # ══════════════════════════════════════════════════════════
            header_start = (SILENCE_BITS + PREAMBLE_BITS) * spb

            if header_start + _HEADER_BITS * spb > len(data):
                raise ValueError(
                    "الملف الصوتي قصير — لا يحتوي على header كامل.\n"
                    "تأكد أن الملف مُرمَّز بـ socialdisk وغير مقطوع."
                )

            # ══════════════════════════════════════════════════════════
            #  STEP 3: قراءة 32-bit header → استخراج N (عدد بتات البيانات)
            #
            #  header يستخدم: بت=1 → sync_freq، بت=0 → freq_zero
            #  هذا يُميِّزه عن بيانات البيانات (بت=1 → freq_one)
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

            # التحقق من صحة N
            data_start = pos   # بداية البيانات (بعد header مباشرة)
            available  = (len(data) - data_start) // spb

            if n_data_bits <= 0 or n_data_bits > available:
                raise ValueError(
                    f"قيمة header غير صالحة (N={n_data_bits}, متاح={available} بت).\n"
                    "الملف تالف أو مُرمَّز بإصدار مختلف من socialdisk."
                )

            # ══════════════════════════════════════════════════════════
            #  STEP 4: قراءة N بت بيانات — FFT vectorized (سريع جداً)
            #
            #  لكل إطار زمني (spb عينة):
            #    mag0 = قوة freq_zero، mag1 = قوة freq_one
            #    الأعلى = البت المُرسَل (0 أو 1)
            #
            #  نُعالج جميع الإطارات دفعة واحدة (vectorized) بدلاً من حلقة
            #  → أسرع بـ 50-100× من حلقة Python خالصة
            # ══════════════════════════════════════════════════════════
            data_segment = data[data_start: data_start + n_data_bits * spb]

            # إعادة تشكيل إلى (n_data_bits, spb) للمعالجة الجماعية
            frames     = data_segment.reshape(n_data_bits, spb)
            win        = np.hanning(spb)
            frames_win = frames * win   # broadcast: (n_data_bits, spb)

            # FFT على جميع الإطارات دفعة واحدة
            spectra = np.abs(np.fft.rfft(frames_win, axis=1))  # (n_data_bits, spb//2+1)
            freqs   = np.fft.rfftfreq(spb, 1.0 / _sr)

            # إيجاد bin كل تردد (±2 bin للمتانة)
            idx0 = int(np.argmin(np.abs(freqs - _f0)))
            idx1 = int(np.argmin(np.abs(freqs - _f1)))
            lo0, hi0 = max(0, idx0 - 2), min(spectra.shape[1], idx0 + 3)
            lo1, hi1 = max(0, idx1 - 2), min(spectra.shape[1], idx1 + 3)

            # قوة كل تردد لكل إطار
            mag0 = spectra[:, lo0:hi0].mean(axis=1)   # (n_data_bits,)
            mag1 = spectra[:, lo1:hi1].mean(axis=1)   # (n_data_bits,)

            # قرار البت: الأعلى قوة يفوز
            bits_arr = (mag1 > mag0).astype(np.uint8)

            # ══════════════════════════════════════════════════════════
            #  STEP 5: فك التشفير الكامل
            # ══════════════════════════════════════════════════════════
            return VaultCore.unpack_payload(bits_arr, password, ecc_symbols=_ecc)

        finally:
            if temp_wav and os.path.exists(temp_wav):
                os.remove(temp_wav)
