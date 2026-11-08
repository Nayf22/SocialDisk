"""
ملفات إعداد المنصات الاجتماعية — Platform Profiles

كل منصة تحدد معاملات دقيقة مبنية على تحليل آلية الضغط الفعلية:

  ImageProfile:
    jpeg_attack_quality  — جودة JPEG التي تُطبّقها المنصة عند الرفع
    max_width            — أقصى عرض قبل إعادة التحجيم التلقائي
    strips_exif          — هل تُزيل المنصة بيانات EXIF؟
    delta                — قوة إشارة DCT (يجب >> خطوة التكميم عند جودة الهجوم)
    ecc_symbols          — رموز Reed-Solomon (أكثر ضغطاً → أكثر رموزاً)
    redundancy           — مرات تكرار كل بت مكانياً (أكثر ضغطاً → أكثر تكراراً)

  VideoProfile:
    max_width/height     — أقصى دقة تقبلها المنصة
    fps                  — معدل الإطارات الموصى به
    block_size           — حجم مربع البيانات (بكسل) — أكبر من ماكروبلوك H.264=16
    ecc_symbols, redundancy

  AudioProfile:
    freq_zero/one        — ترددات FSK الآمنة من ضغط AAC/Opus
    sync_freq            — تردد نغمة المزامنة (أقل → أوضح للكشف)
    baud_rate            — معدل بث البتات (بود/ثانية)
    sample_rate          — معدل أخذ العينات
    ecc_symbols

حساب Delta الأمثل لكل منصة:
  معامل تكميم JPEG للموضع (3,2) ≈ 22 (من جدول الإضاءة القياسي)
  عند جودة q: خطوة ≈ 22 × (100-q)/50
  لضمان البقاء: delta > خطوة × 2.5 (هامش أمان ×2.5)

  q=90 → خطوة≈4.4  → delta≥11  (نستخدم 20)
  q=85 → خطوة≈6.6  → delta≥17  (نستخدم 32)
  q=80 → خطوة≈8.8  → delta≥22  (نستخدم 38)
  q=75 → خطوة≈11   → delta≥28  (نستخدم 44)
  q=70 → خطوة≈13.2 → delta≥33  (نستخدم 50)
  q=65 → خطوة≈15.4 → delta≥39  (نستخدم 55)
  q=60 → خطوة≈17.6 → delta≥44  (نستخدم 60)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ======================================================================
#  تعريفات ملفات الإعداد
# ======================================================================

@dataclass
class ImageProfile:
    """إعداد التضمين في الصور."""
    jpeg_attack_quality: int    # جودة JPEG التي تُطبّقها المنصة
    max_width: int              # أقصى عرض (بكسل)
    strips_exif: bool           # هل تُزيل المنصة بيانات EXIF؟
    delta: float                # قوة إشارة DCT (يجب > خطوة التكميم × 2.5)
    ecc_symbols: int            # رموز تصحيح Reed-Solomon
    redundancy: int = 3         # تكرار كل بت مكانياً


@dataclass
class VideoProfile:
    """إعداد التضمين في الفيديو."""
    max_width: int              # أقصى عرض (بكسل)
    max_height: int             # أقصى ارتفاع (بكسل)
    fps: int                    # معدل الإطارات الموصى به
    block_size: int             # حجم مربع البيانات (بكسل) ≥ 16
    ecc_symbols: int
    redundancy: int = 1


@dataclass
class AudioProfile:
    """إعداد التضمين في الصوت (Acoustic FSK)."""
    freq_zero: float            # تردد البت=0 (Hz)
    freq_one: float             # تردد البت=1 (Hz)
    sync_freq: float            # تردد نغمة المزامنة (Hz)
    baud_rate: int              # بتات في الثانية
    sample_rate: int            # معدل أخذ العينات (Hz)
    ecc_symbols: int
    redundancy: int = 1


@dataclass
class PlatformProfile:
    """ملف الإعداد الكامل لمنصة اجتماعية."""
    key: str                             # المفتاح الداخلي
    name: str                            # الاسم للعرض
    emoji: str                           # رمز تعبيري
    description: str                     # وصف مختصر
    image: Optional[ImageProfile] = None
    video: Optional[VideoProfile] = None
    audio: Optional[AudioProfile] = None


# ======================================================================
#  جدول المنصات — 14 منصة مدعومة
# ======================================================================

PLATFORMS: dict[str, PlatformProfile] = {

    # ═══════════════════════════════════════════════════════════════
    # Instagram — JPEG 65-80% | H.264 | AAC 128k
    # الصور: ضغط قوي | الفيديو: H.264 بـ 30fps | الصوت: AAC 128k
    # ═══════════════════════════════════════════════════════════════
    "instagram": PlatformProfile(
        key="instagram", name="Instagram", emoji="📸",
        description="منصة الصور والريلز | ضغط JPEG متوسط-قوي (q≈70)",
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
    # ضغط صور قوي جداً | صوت Opus يقطع < 400Hz و > 4000Hz
    # ═══════════════════════════════════════════════════════════════
    "whatsapp": PlatformProfile(
        key="whatsapp", name="WhatsApp", emoji="💬",
        description="تطبيق المراسلة | ضغط صور قوي (q≈70) | Opus للصوت",
        image=ImageProfile(
            jpeg_attack_quality=70, max_width=1600,
            strips_exif=True, delta=55.0, ecc_symbols=96, redundancy=5,
        ),
        video=VideoProfile(
            max_width=1280, max_height=720, fps=25,
            block_size=16, ecc_symbols=150, redundancy=1,
        ),
        audio=AudioProfile(
            # Opus آمن في نطاق 400-7700 Hz عند 32kbps
            freq_zero=1200.0, freq_one=2400.0, sync_freq=700.0,
            baud_rate=100, sample_rate=44100, ecc_symbols=80,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Twitter / X — JPEG 85% | H.264 | AAC 128k
    # ضغط صور خفيف نسبياً | الفيديو حتى 60fps و 1080p
    # ═══════════════════════════════════════════════════════════════
    "twitter": PlatformProfile(
        key="twitter", name="Twitter / X", emoji="🐦",
        description="منصة التدوين المصغر | ضغط صور خفيف (q≈85)",
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
    # TikTok — فيديو فقط | H.264 ضغط قوي جداً | AAC 128k
    # لا يدعم تحميل الصور كـ post مستقل بنفس الطريقة
    # ═══════════════════════════════════════════════════════════════
    "tiktok": PlatformProfile(
        key="tiktok", name="TikTok", emoji="🎵",
        description="منصة الفيديو القصير | ضغط فيديو قوي جداً | 9:16 فقط",
        video=VideoProfile(
            max_width=1080, max_height=1920, fps=30,
            block_size=20,   # أكبر من 16 لتجاوز ضغط الماكروبلوك القوي
            ecc_symbols=160, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=2700.0, sync_freq=900.0,
            baud_rate=120, sample_rate=44100, ecc_symbols=80,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # YouTube — H.264/VP9 ضغط خفيف | AAC 128-384k
    # يحافظ على جودة أعلى خصوصاً بدقات 1080p+
    # ═══════════════════════════════════════════════════════════════
    "youtube": PlatformProfile(
        key="youtube", name="YouTube", emoji="▶️",
        description="منصة الفيديو الطويل | ضغط خفيف بدقات عالية",
        video=VideoProfile(
            max_width=3840, max_height=2160, fps=60,
            block_size=12,   # يمكن استخدام بلوكات أصغر لأن الضغط خفيف
            ecc_symbols=64, redundancy=1,
        ),
        audio=AudioProfile(
            freq_zero=1500.0, freq_one=3000.0, sync_freq=800.0,
            baud_rate=300, sample_rate=44100, ecc_symbols=48,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Telegram — JPEG 85% (كصورة) أو لا ضغط (كملف) | MP3/AAC
    # يمكن إرسال الصور كـ "file" لتجنب الضغط الكامل
    # ═══════════════════════════════════════════════════════════════
    "telegram": PlatformProfile(
        key="telegram", name="Telegram", emoji="✈️",
        description="تطبيق مراسلة | ضغط معتدل كـ photo، أو لا ضغط كـ file",
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
    # ضغط صور خفيف نسبياً مقارنة بالمنصات الأخرى
    # ═══════════════════════════════════════════════════════════════
    "discord": PlatformProfile(
        key="discord", name="Discord", emoji="🎮",
        description="منصة المجتمعات | ضغط صور خفيف (q≈90) | Opus للصوت",
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
    # يغير EXIF ويُصغّر الصور إلى 2048px
    # ═══════════════════════════════════════════════════════════════
    "facebook": PlatformProfile(
        key="facebook", name="Facebook", emoji="👥",
        description="منصة التواصل الاجتماعي | ضغط صور متوسط (q≈80)",
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
    # ضغط صور قوي وتُصغّر إلى 1080px
    # ═══════════════════════════════════════════════════════════════
    "snapchat": PlatformProfile(
        key="snapchat", name="Snapchat", emoji="👻",
        description="تطبيق الصور المؤقتة | ضغط صور قوي (q≈72)",
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
        description="منصة المجتمعات والمناقشات | ضغط صور معتدل (q≈85)",
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
        description="منصة التوظيف والأعمال | ضغط متوسط (q≈85)",
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
    # يُحسَّن للصور العمودية (2:3)
    # ═══════════════════════════════════════════════════════════════
    "pinterest": PlatformProfile(
        key="pinterest", name="Pinterest", emoji="📌",
        description="منصة الصور الإلهامية | ضغط متوسط للصور (q≈82)",
        image=ImageProfile(
            jpeg_attack_quality=82, max_width=1200,
            strips_exif=True, delta=38.0, ecc_symbols=75, redundancy=3,
        ),
    ),

    # ═══════════════════════════════════════════════════════════════
    # Mastodon — شبكة مفتوحة | ضغط خفيف جداً
    # ═══════════════════════════════════════════════════════════════
    "mastodon": PlatformProfile(
        key="mastodon", name="Mastodon", emoji="🐘",
        description="شبكة اجتماعية مفتوحة المصدر | ضغط خفيف جداً",
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
    # Signal — ضغط صور قوي جداً لتوفير البيانات (q≈65-70)
    # ═══════════════════════════════════════════════════════════════
    "signal": PlatformProfile(
        key="signal", name="Signal", emoji="🔒",
        description="تطبيق المراسلة المشفر | ضغط صور قوي جداً (q≈65)",
        image=ImageProfile(
            jpeg_attack_quality=65, max_width=1600,
            strips_exif=True, delta=60.0, ecc_symbols=100, redundancy=5,
        ),
        audio=AudioProfile(
            # Opus في Signal يقطع الترددات < 400Hz و > 4000Hz
            freq_zero=1200.0, freq_one=2400.0, sync_freq=700.0,
            baud_rate=80, sample_rate=44100, ecc_symbols=96,
        ),
    ),
}


# ======================================================================
#  دوال المساعدة
# ======================================================================

def get_platform(key: str) -> PlatformProfile:
    """استرجاع ملف إعداد المنصة أو رفع استثناء واضح."""
    key = key.lower().strip()
    if key not in PLATFORMS:
        available = ", ".join(PLATFORMS.keys())
        raise KeyError(
            f"المنصة '{key}' غير معروفة.\n"
            f"المنصات المتاحة: {available}"
        )
    return PLATFORMS[key]


def list_platforms() -> list[PlatformProfile]:
    """إرجاع قائمة بكل المنصات المدعومة."""
    return list(PLATFORMS.values())
