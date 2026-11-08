import os
import struct
import zlib
import lzma
import hashlib
import random
import subprocess
from typing import Tuple, Optional
import numpy as np
import cv2
from scipy.fftpack import dct, idct
from scipy.io import wavfile
from reedsolo import RSCodec, ReedSolomonError
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


# =====================================================================
# 1. النواة الرياضية: الضغط، التشفير، تصحيح الأخطاء، وبعثرة البيانات
# =====================================================================
class VaultCore:
    MAGIC = b"IVLT"

    @staticmethod
    def _derive_key(password: str, salt: bytes) -> bytes:
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100_000,
        )
        return kdf.derive(password.encode('utf-8'))

    @staticmethod
    def _interleave(data: bytes, seed_bytes: bytes, inverse: bool = False) -> bytes:
        """بعثرة البيانات لتفكيك الأخطاء المتكتلة (Burst Errors) الناتجة عن ضغط الفيديو/الصور"""
        n = len(data)
        rng = random.Random(int.from_bytes(seed_bytes[:8], 'big'))
        indices = list(range(n))
        rng.shuffle(indices)
        out = bytearray(n)
        if not inverse:
            for i, idx in enumerate(indices):
                out[idx] = data[i]
        else:
            for i, idx in enumerate(indices):
                out[i] = data[idx]
        return bytes(out)

    @classmethod
    def pack_payload(cls, raw_data: bytes, password: str = "default_pass", ecc_symbols: int = 64) -> np.ndarray:
        """ضغط -> تشفير AES-GCM -> ترميز Reed-Solomon -> بعثرة -> تحويل إلى مصفوفة بتات"""
        # 1. ضغط البيانات بأقصى درجة
        compressed = lzma.compress(raw_data)

        # 2. تشفير AES-256-GCM
        salt = os.urandom(16)
        nonce = os.urandom(12)
        key = cls._derive_key(password, salt)
        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, compressed, None)

        # بناء الحزمة الأساسية مع CRC32 للتحقق السريع
        envelope = salt + nonce + ciphertext
        crc = zlib.crc32(envelope)
        header = cls.MAGIC + struct.pack(">II", len(envelope), crc)
        full_packet = header + envelope

        # 3. إضافة معامل تصحيح الأخطاء (Reed-Solomon)
        rsc = RSCodec(ecc_symbols)
        encoded_ecc = bytes(rsc.encode(full_packet))

        # 4. بعثرة البايتات (Interleaving) باستخدام مفتاح مشتق من كلمة المرور
        seed = hashlib.sha256(password.encode()).digest()
        interleaved = cls._interleave(encoded_ecc, seed, inverse=False)

        # إضافة طول الحزمة النهائية في البداية (مكرر 3 مرات للحماية القصوى ضد التلف)
        total_len = len(interleaved)
        len_header = struct.pack(">I", total_len) * 3
        final_stream = len_header + interleaved

        # تحويل البايتات إلى مصفوفة بتات (0 و 1)
        return np.unpackbits(np.frombuffer(final_stream, dtype=np.uint8))

    @classmethod
    def unpack_payload(cls, bits: np.ndarray, password: str = "default_pass", ecc_symbols: int = 64) -> bytes:
        """العملية العكسية لاستخراج الملف الأصلي وإصلاح التلف الناتج عن إنستغرام"""
        raw_bytes = np.packbits(bits).tobytes()
        if len(raw_bytes) < 12:
            raise ValueError("البيانات المستخرجة قصيرة جداً أو تالفة.")

        # قراءة الطول عبر التصويت بالأغلبية (Majority Voting) من التكرارات الثلاثة
        l1, l2, l3 = struct.unpack(">III", raw_bytes[:12])
        lengths = [l1, l2, l3]
        total_len = max(set(lengths), key=lengths.count)

        if total_len <= 0 or 12 + total_len > len(raw_bytes):
            raise ValueError(f"فشل تحديد حجم الحزمة الصحيح (الحجم المقروء: {total_len}).")

        interleaved = raw_bytes[12: 12 + total_len]

        # 1. إلغاء البعثرة (De-interleaving)
        seed = hashlib.sha256(password.encode()).digest()
        encoded_ecc = cls._interleave(interleaved, seed, inverse=True)

        # 2. تصحيح الأخطاء عبر Reed-Solomon
        rsc = RSCodec(ecc_symbols)
        try:
            decoded_pkt, _, _ = rsc.decode(encoded_ecc)
            decoded_pkt = bytes(decoded_pkt)
        except ReedSolomonError as e:
            raise ValueError("نسبة التلف في الملف أعلى من قدرة التصحيح، جرب زيادة ecc_symbols أو حجم البلوك.") from e

        # 3. التحقق من الترويسة وسلامة البيانات
        if decoded_pkt[:4] != cls.MAGIC:
            raise ValueError("بصمة الملف غير متطابقة أو كلمة المرور خاطئة.")

        env_len, expected_crc = struct.unpack(">II", decoded_pkt[4:12])
        envelope = decoded_pkt[12: 12 + env_len]

        if zlib.crc32(envelope) != expected_crc:
            raise ValueError("فشل التحقق من CRC32 بعد التصحيح.")

        # 4. فك التشفير وفك الضغط
        salt = envelope[:16]
        nonce = envelope[16:28]
        ciphertext = envelope[28:]

        key = cls._derive_key(password, salt)
        aesgcm = AESGCM(key)
        compressed = aesgcm.decrypt(nonce, ciphertext, None)
        return lzma.decompress(compressed)


# =====================================================================
# 2. المحرك الأول: إخفاء ترددي غير مرئي داخل الصور (Differential DCT Stego)
# =====================================================================
class DCTImageEngine:
    """
    يخفي البيانات في الفروق الرياضية بين معاملات التردد المتوسط (Mid-Band DCT)
    داخل قناة الإضاءة (Y) ليصمد أمام ضغط JPEG الخاص بإنستغرام دون تشويه الصورة.
    """
    # إحداثيات متناظرة في التردد المتوسط داخل كتلة 8x8
    POS_A = (3, 2)
    POS_B = (2, 3)

    @staticmethod
    def _dct2(block: np.ndarray) -> np.ndarray:
        return dct(dct(block.T, norm='ortho').T, norm='ortho')

    @staticmethod
    def _idct2(block: np.ndarray) -> np.ndarray:
        return idct(idct(block.T, norm='ortho').T, norm='ortho')

    @classmethod
    def embed(cls, image_path: str, output_path: str, payload: bytes, password: str,
              delta: float = 38.0, ecc_symbols: int = 80) -> dict:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"لم يتم العثور على الصورة: {image_path}")

        # ضبط العرض تلقائياً إلى 1080px لمنع إنستغرام من تغيير أبعاد الصورة (Resampling)
        h, w = img.shape[:2]
        if w != 1080:
            new_h = int((h * 1080) / w)
            # تقريب الطول لأقرب مضاعف لـ 8
            new_h = (new_h // 8) * 8
            img = cv2.resize(img, (1080, new_h), interpolation=cv2.INTER_AREA)

        h, w = (img.shape[0] // 8) * 8, (img.shape[1] // 8) * 8
        img = img[:h, :w]

        bits = VaultCore.pack_payload(payload, password, ecc_symbols=ecc_symbols)
        # نكرر كل بت 3 مرات (Spatial Redundancy) لزيادة الصمود أمام مصفوفة التكميم
        redundant_bits = np.repeat(bits, 3)

        max_blocks = (h // 8) * (w // 8)
        if len(redundant_bits) > max_blocks:
            max_bytes = (max_blocks // 3 // 8) - ecc_symbols - 50
            raise ValueError(f"البيانات كبيرة جداً على هذه الصورة. الحد الأقصى الموصى به للوضع الخفي: ~{max(0, max_bytes)} بايت.")

        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y_channel = ycrcb[:, :, 0]

        # توليد ترتيب عشوائي للكتل بناءً على كلمة المرور (أمان + توزيع التلف)
        total_blocks = [(r, c) for r in range(0, h, 8) for c in range(0, w, 8)]
        rng = random.Random(int.from_bytes(hashlib.sha256(password.encode()).digest()[:8], 'big'))
        rng.shuffle(total_blocks)

        for idx, bit in enumerate(redundant_bits):
            r, c = total_blocks[idx]
            block = y_channel[r:r+8, c:c+8] - 128.0
            dct_block = cls._dct2(block)

            c1 = dct_block[cls.POS_A]
            c2 = dct_block[cls.POS_B]
            avg = (c1 + c2) / 2.0

            if bit == 1:
                dct_block[cls.POS_A] = avg + (delta / 2.0)
                dct_block[cls.POS_B] = avg - (delta / 2.0)
            else:
                dct_block[cls.POS_A] = avg - (delta / 2.0)
                dct_block[cls.POS_B] = avg + (delta / 2.0)

            y_channel[r:r+8, c:c+8] = np.clip(cls._idct2(dct_block) + 128.0, 0, 255)

        ycrcb[:, :, 0] = y_channel
        stego_img = cv2.cvtColor(ycrcb.astype(np.uint8), cv2.COLOR_YCrCb2BGR)
        # حفظ بجودة 95% لمحاكاة ضغط قياسي نظيف قبل الرفع
        cv2.imwrite(output_path, stego_img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        return {
            "dimensions": f"{w}x{h}",
            "raw_size_bytes": len(payload),
            "encoded_bits": len(redundant_bits),
            "capacity_used_percent": round((len(redundant_bits) / max_blocks) * 100, 2)
        }

    @classmethod
    def extract(cls, image_path: str, password: str, ecc_symbols: int = 80) -> bytes:
        img = cv2.imread(image_path)
        if img is None:
            raise FileNotFoundError(f"لم يتم العثور على الصورة: {image_path}")

        h, w = (img.shape[0] // 8) * 8, (img.shape[1] // 8) * 8
        img = img[:h, :w]

        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb).astype(np.float32)
        y_channel = ycrcb[:, :, 0]

        total_blocks = [(r, c) for r in range(0, h, 8) for c in range(0, w, 8)]
        rng = random.Random(int.from_bytes(hashlib.sha256(password.encode()).digest()[:8], 'big'))
        rng.shuffle(total_blocks)

        raw_bits = []
        for r, c in total_blocks:
            block = y_channel[r:r+8, c:c+8] - 128.0
            dct_block = cls._dct2(block)
            diff = dct_block[cls.POS_A] - dct_block[cls.POS_B]
            raw_bits.append(1 if diff > 0 else 0)

        # فك التكرار الثلاثي عبر التصويت (Soft/Hard Majority Voting)
        usable_len = (len(raw_bits) // 3) * 3
        triplets = np.array(raw_bits[:usable_len]).reshape(-1, 3)
        voted_bits = (np.sum(triplets, axis=1) >= 2).astype(np.uint8)

        return VaultCore.unpack_payload(voted_bits, password, ecc_symbols=ecc_symbols)


# =====================================================================
# 3. المحرك الثاني: المصفوفة البصرية عالية السعة للفيديو (HyperGrid Video)
# =====================================================================
class HyperGridVideoEngine:
    """
    يحول أي ملف كبير إلى إطارات فيديو مشفرة بـ 4 مستويات لونية لكل قناة (8-bit per cell)
    أو نظام ثنائي فائق الصلابة (1-bit per cell) مع مربعات معايرة لونية وهندسية في الزوايا.
    """
    WIDTH = 1080
    HEIGHT = 1920  # مقاس Reels / Stories القياسي في إنستغرام
    BLOCK_SIZE = 16  # 16x16 بكسل يتخطى ضغط الماكروبلوك (Macroblock) في H.264 بسهولة

    @classmethod
    def encode(cls, output_video: str, payload: bytes, password: str,
               fps: int = 30, ecc_symbols: int = 128) -> dict:
        bits = VaultCore.pack_payload(payload, password, ecc_symbols=ecc_symbols)

        grid_w = cls.WIDTH // cls.BLOCK_SIZE
        grid_h = cls.HEIGHT // cls.BLOCK_SIZE

        # ترك هامش 2 بلوك من كل جهة لرسم إطار المزامنة ومعايرة الألوان
        data_cols = grid_w - 4
        data_rows = grid_h - 4
        bits_per_frame = data_cols * data_rows

        total_frames = int(np.ceil(len(bits) / bits_per_frame))
        padded_bits = np.zeros(total_frames * bits_per_frame, dtype=np.uint8)
        padded_bits[:len(bits)] = bits

        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        writer = cv2.VideoWriter(output_video, fourcc, fps, (cls.WIDTH, cls.HEIGHT))

        for f_idx in range(total_frames):
            frame_grid = np.zeros((grid_h, grid_w, 3), dtype=np.uint8)

            # 1. رسم حدود المعايرة (أبيض وأسود متناوب لضبط الـ Threshold ديناميكياً عند القراءة)
            frame_grid[0:2, :, :] = 255  # أعلى أبيض
            frame_grid[-2:, :, :] = 30   # أسفل داكن (لتجنب القص الكامل في نطاق YUV المحدود)
            frame_grid[:, 0:2, :] = 255  # يسار أبيض
            frame_grid[:, -2:, :] = 30   # يمين داكن

            # 2. تعبئة البيانات في القلب
            chunk = padded_bits[f_idx * bits_per_frame: (f_idx + 1) * bits_per_frame]
            chunk_2d = chunk.reshape((data_rows, data_cols))

            # نستخدم القيم 35 (للصفر) و 220 (للواحد) لتفادي تشبع الألوان (Clipping) في ضغط TV-Range YUV420p
            val_grid = np.where(chunk_2d == 1, 220, 35).astype(np.uint8)
            frame_grid[2:-2, 2:-2, 0] = val_grid
            frame_grid[2:-2, 2:-2, 1] = val_grid
            frame_grid[2:-2, 2:-2, 2] = val_grid

            # تكبير المصفوفة إلى دقة 1080x1920 بدون تنعيم حواف (Nearest Neighbor)
            full_frame = cv2.resize(frame_grid, (cls.WIDTH, cls.HEIGHT), interpolation=cv2.INTER_NEAREST)
            writer.write(full_frame)

        writer.release()
        return {
            "resolution": f"{cls.WIDTH}x{cls.HEIGHT}",
            "total_frames": total_frames,
            "duration_sec": round(total_frames / fps, 2),
            "capacity_per_frame_bytes": bits_per_frame // 8
        }

    @classmethod
    def decode(cls, video_path: str, password: str, ecc_symbols: int = 128) -> bytes:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise FileNotFoundError(f"فشل فتح الفيديو: {video_path}")

        grid_w = cls.WIDTH // cls.BLOCK_SIZE
        grid_h = cls.HEIGHT // cls.BLOCK_SIZE
        extracted_bits = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            # إعادة ضبط الحجم في حال قام إنستغرام بتصغير الفيديو إلى 720p مثلاً
            if frame.shape[1] != cls.WIDTH or frame.shape[0] != cls.HEIGHT:
                frame = cv2.resize(frame, (cls.WIDTH, cls.HEIGHT), interpolation=cv2.INTER_LINEAR)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # أخذ عينات من مركز كل مربع 16x16 فقط (المنطقة الآمنة 8x8 بالمنتصف بعيداً عن تداخل الحواف)
            half = cls.BLOCK_SIZE // 2
            centers = gray[half::cls.BLOCK_SIZE, half::cls.BLOCK_SIZE]

            # معايرة ديناميكية للسطوع من حدود المزامنة في نفس الإطار
            white_ref = np.mean(centers[0:2, :])
            black_ref = np.mean(centers[-2:, :])
            dynamic_thresh = (white_ref + black_ref) / 2.0

            data_zone = centers[2:-2, 2:-2]
            frame_bits = (data_zone > dynamic_thresh).astype(np.uint8).flatten()
            extracted_bits.append(frame_bits)

        cap.release()
        if not extracted_bits:
            raise ValueError("لم يتم قراءة أي إطارات من الفيديو.")

        all_bits = np.concatenate(extracted_bits)
        return VaultCore.unpack_payload(all_bits, password, ecc_symbols=ecc_symbols)


# =====================================================================
# 4. المحرك الثالث: المودم الصوتي المضاد لضغط AAC (Acoustic FSK Engine)
# =====================================================================
class AcousticFSKEngine:
    """
    يحول البيانات إلى إشارات صوتية بترددات مسموعة آمنة (1500Hz و 2700Hz)
    لا يقوم ضغط الصوت في إنستغرام (AAC) بحذفها.
    """
    SAMPLE_RATE = 44100
    BAUD_RATE = 150  # 150 بت في الثانية (آمن جداً ضد الصدى وضغط AAC)
    FREQ_0 = 1500.0
    FREQ_1 = 2700.0
    SYNC_FREQ = 900.0

    @classmethod
    def encode_wav(cls, output_wav: str, payload: bytes, password: str, ecc_symbols: int = 64) -> dict:
        bits = VaultCore.pack_payload(payload, password, ecc_symbols=ecc_symbols)
        samples_per_bit = cls.SAMPLE_RATE // cls.BAUD_RATE
        t_bit = np.linspace(0, 1.0 / cls.BAUD_RATE, samples_per_bit, endpoint=False)

        # نافذة تنعيم (Hanning Window) طفيفة عند الأطراف لمنع طقطقة الصوت وتشوه الترددات
        envelope = np.ones_like(t_bit)
        fade = max(1, samples_per_bit // 10)
        envelope[:fade] = np.linspace(0.2, 1.0, fade)
        envelope[-fade:] = np.linspace(1.0, 0.2, fade)

        wave_0 = (np.sin(2 * np.pi * cls.FREQ_0 * t_bit) * envelope).astype(np.float32)
        wave_1 = (np.sin(2 * np.pi * cls.FREQ_1 * t_bit) * envelope).astype(np.float32)

        # نغمة بداية (Preamble) بطول 0.5 ثانية للمزامنة الدقيقة عند القراءة
        t_sync = np.linspace(0, 0.5, cls.SAMPLE_RATE // 2, endpoint=False)
        preamble = np.sin(2 * np.pi * cls.SYNC_FREQ * t_sync).astype(np.float32)
        silence = np.zeros(cls.SAMPLE_RATE // 4, dtype=np.float32)

        signal_parts = [silence, preamble]
        for b in bits:
            signal_parts.append(wave_1 if b == 1 else wave_0)
        signal_parts.append(silence)

        full_signal = np.concatenate(signal_parts)
        pcm_data = (full_signal * 28000).astype(np.int16)
        wavfile.write(output_wav, cls.SAMPLE_RATE, pcm_data)

        return {
            "duration_sec": round(len(full_signal) / cls.SAMPLE_RATE, 2),
            "baud_rate": cls.BAUD_RATE,
            "total_bits": len(bits)
        }

    @classmethod
    def _goertzel_mag(cls, samples: np.ndarray, target_freq: float) -> float:
        """حساب قوة تردد معين بسرعة فائقة (أدق وأسرع من FFT العادي للنغمات المحددة)"""
        n = len(samples)
        k = int(0.5 + (n * target_freq) / cls.SAMPLE_RATE)
        w = (2.0 * np.pi * k) / n
        cosine = np.cos(w)
        coeff = 2.0 * cosine
        q0, q1, q2 = 0.0, 0.0, 0.0
        for s in samples:
            q0 = coeff * q1 - q2 + s
            q2 = q1
            q1 = q0
        return q1 * q1 + q2 * q2 - q1 * q2 * coeff

    @classmethod
    def decode_media(cls, media_path: str, password: str, ecc_symbols: int = 64) -> bytes:
        temp_wav = None
        # إذا كان الملف فيديو MP4 تم تحميله من إنستغرام، نستخرج الصوت منه أولاً عبر ffmpeg
        if not media_path.lower().endswith(".wav"):
            temp_wav = "temp_extracted_audio.wav"
            cmd = ["ffmpeg", "-y", "-i", media_path, "-vn", "-ac", "1", "-ar", str(cls.SAMPLE_RATE), temp_wav]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            target_file = temp_wav
        else:
            target_file = media_path

        try:
            sr, data = wavfile.read(target_file)
            if data.ndim > 1:
                data = data[:, 0]
            data = data.astype(np.float32) / 32768.0

            samples_per_bit = sr // cls.BAUD_RATE
            step = samples_per_bit // 4

            # البحث عن نهاية نغمة المزامنة (900Hz) وبداية البيانات الفعلية
            sync_end_idx = 0
            in_sync = False
            for i in range(0, len(data) - samples_per_bit, step):
                chunk = data[i: i + samples_per_bit]
                p_sync = cls._goertzel_mag(chunk, cls.SYNC_FREQ)
                p_data = max(cls._goertzel_mag(chunk, cls.FREQ_0), cls._goertzel_mag(chunk, cls.FREQ_1))

                if p_sync > p_data * 3 and p_sync > 1.0:
                    in_sync = True
                elif in_sync and p_data > p_sync:
                    # وجدنا نقطة الانتقال الدقيقة من نغمة المزامنة إلى أول بت بيانات
                    sync_end_idx = i
                    break

            bits = []
            for pos in range(sync_end_idx, len(data) - samples_per_bit, samples_per_bit):
                chunk = data[pos: pos + samples_per_bit]
                mag0 = cls._goertzel_mag(chunk, cls.FREQ_0)
                mag1 = cls._goertzel_mag(chunk, cls.FREQ_1)
                bits.append(1 if mag1 > mag0 else 0)

            return VaultCore.unpack_payload(np.array(bits, dtype=np.uint8), password, ecc_symbols=ecc_symbols)
        finally:
            if temp_wav and os.path.exists(temp_wav):
                os.remove(temp_wav)


# =====================================================================
# 5. الواجهة الموحدة للمكتبة (InstaVault API)
# =====================================================================
class InstaVault:
    """الواجهة الرئيسية الموحدة لاستخدام كافة محركات التضمين والاسترجاع"""

    @staticmethod
    def hide_in_image(cover_image: str, output_image: str, secret_data: bytes, password: str) -> dict:
        return DCTImageEngine.embed(cover_image, output_image, secret_data, password)

    @staticmethod
    def recover_from_image(stego_image: str, password: str) -> bytes:
        return DCTImageEngine.extract(stego_image, password)

    @staticmethod
    def file_to_video(output_video: str, file_data: bytes, password: str) -> dict:
        return HyperGridVideoEngine.encode(output_video, file_data, password)

    @staticmethod
    def video_to_file(video_path: str, password: str) -> bytes:
        return HyperGridVideoEngine.decode(video_path, password)

    @staticmethod
    def data_to_audio(output_wav: str, secret_data: bytes, password: str) -> dict:
        return AcousticFSKEngine.encode_wav(output_wav, secret_data, password)

    @staticmethod
    def audio_to_data(media_path: str, password: str) -> bytes:
        return AcousticFSKEngine.decode_media(media_path, password)


# =====================================================================
# اختبار عملي تلقائي مع محاكاة ضغط إنستغرام العنيف (Instagram Attack Simulator)
# =====================================================================
if __name__ == "__main__":
    print("[*] جاري بدء اختبار مكتبة InstaVault مع محاكاة تدمير وضغط إنستغرام...\n")
    secret_pass = "Nayf_SuperSecret_2026"
    sample_message = "مرحباً نايف! هذه بيانات سرية مشفرة بـ AES-256 ومحمية بـ Reed-Solomon ضد ضغط إنستغرام.".encode('utf-8')

    # 1. اختبار الإخفاء الترددي داخل صورة (DCT Steganography)
    print("--- 1. اختبار الإخفاء غير المرئي داخل صورة (DCT Engine) ---")
    # إنشاء صورة غلاف طبيعية متدرجة الألوان للتجربة
    dummy_cover = np.zeros((1350, 1080, 3), dtype=np.uint8)
    for y in range(1350):
        dummy_cover[y, :, 0] = (y * 255) // 1350
        dummy_cover[y, :, 1] = 120
        dummy_cover[y, :, 2] = 255 - ((y * 255) // 1350)
    # إضافة بعض التفاصيل العشوائية لمحاكاة صورة حقيقية
    noise = np.random.randint(0, 35, (1350, 1080, 3), dtype=np.uint8)
    dummy_cover = cv2.add(dummy_cover, noise)
    cv2.imwrite("test_cover.jpg", dummy_cover)

    stats_img = InstaVault.hide_in_image("test_cover.jpg", "insta_ready.jpg", sample_message, secret_pass)
    print(f"[+] تم التضمين في الصورة بنجاح: {stats_img}")

    # محاكاة ضغط إنستغرام القاسي (إعادة حفظ الصورة بجودة JPEG منخفضة 65%)
    img_attacked = cv2.imread("insta_ready.jpg")
    cv2.imwrite("insta_downloaded_sim.jpg", img_attacked, [int(cv2.IMWRITE_JPEG_QUALITY), 65])

    recovered_msg = InstaVault.recover_from_image("insta_downloaded_sim.jpg", secret_pass)
    print(f"[+] النص المسترجع بعد ضغط JPEG القاسي (65%): {recovered_msg.decode('utf-8')}\n")

    # 2. اختبار تخزين ملف كامل داخل فيديو (HyperGrid Video)
    print("--- 2. اختبار الفيديو عالي السعة (HyperGrid Engine) ---")
    large_payload = os.urandom(15 * 1024)  # ملف عشوائي بحجم 15 كيلوبايت
    stats_vid = InstaVault.file_to_video("insta_reel.mp4", large_payload, secret_pass)
    print(f"[+] تم توليد الفيديو بنجاح: {stats_vid}")

    recovered_file = InstaVault.video_to_file("insta_reel.mp4", secret_pass)
    is_identical = (hashlib.sha256(large_payload).digest() == hashlib.sha256(recovered_file).digest())
    print(f"[+] تطابق بصمة الملف المسترجع (SHA-256) بنسبة 100%: {is_identical}\n")

    # 3. اختبار المودم الصوتي (Acoustic FSK)
    print("--- 3. اختبار المودم الصوتي (Acoustic FSK Engine) ---")
    stats_aud = InstaVault.data_to_audio("secret_audio.wav", sample_message, secret_pass)
    print(f"[+] تم تحويل البيانات إلى موجة صوتية: {stats_aud}")
    recovered_aud = InstaVault.audio_to_data("secret_audio.wav", secret_pass)
    print(f"[+] النص المسترجع من الصوت: {recovered_aud.decode('utf-8')}")

    # تنظيف ملفات الاختبار المؤقتة
    for f in ["test_cover.jpg", "insta_ready.jpg", "insta_downloaded_sim.jpg", "insta_reel.mp4", "secret_audio.wav"]:
        if os.path.exists(f):
            os.remove(f)
