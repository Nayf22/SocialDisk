"""
InstaVault API — الواجهة الموحدة لجميع محركات التضمين والاستخراج

مثال سريع:
    from instadisk import InstaVault

    # للعمل مع إنستغرام
    vault = InstaVault("instagram")
    stats = vault.hide_in_image("cover.jpg", "stego.jpg", b"سر", "password123")
    data  = vault.recover_from_image("downloaded.jpg", "password123")

    # للعمل مع واتساب
    vault = InstaVault("whatsapp")
    stats = vault.file_to_video("reel.mp4", open("file.pdf","rb").read(), "pass")
    data  = vault.video_to_file("downloaded.mp4", "pass")

    # للاستخدام المباشر بدون كائن (Static API)
    InstaVault.list_platforms()   # قائمة بكل المنصات
"""
from __future__ import annotations

from instadisk.platforms import PlatformProfile, get_platform, list_platforms
from instadisk.engines.image import DCTImageEngine
from instadisk.engines.video import HyperGridVideoEngine
from instadisk.engines.audio import AcousticFSKEngine


class InstaVault:
    """
    واجهة مبسطة للعمل مع منصة اجتماعية محددة.

    تُختار المعاملات الأمثل (delta, ecc_symbols, redundancy, ...)
    تلقائياً بناءً على خصائص الضغط المُوثَّقة لكل منصة.

    Example:
        vault = InstaVault("whatsapp")

        # تضمين
        stats = vault.hide_in_image("in.jpg", "out.jpg", payload, password)

        # استخراج
        data = vault.recover_from_image("downloaded.jpg", password)
    """

    def __init__(self, platform: str = "instagram"):
        """
        Args:
            platform: مفتاح المنصة (instagram, whatsapp, twitter, ...).
                      غير حساس لحالة الأحرف.
        """
        self.platform_key: str = platform.lower().strip()
        self.profile: PlatformProfile = get_platform(self.platform_key)

    def __repr__(self) -> str:
        return f"InstaVault(platform='{self.platform_key}')"

    # ================================================================== #
    #  الصور — DCT Steganography
    # ================================================================== #

    def hide_in_image(
        self,
        cover_image: str,
        output_image: str,
        secret_data: bytes,
        password: str,
        **kwargs,
    ) -> dict:
        """
        إخفاء بيانات داخل صورة بطريقة DCT الفارقية.

        Args:
            cover_image:  مسار صورة الغلاف الأصلية.
            output_image: مسار حفظ الصورة المُعدَّلة (جاهزة للرفع).
            secret_data:  البيانات السرية (bytes).
            password:     كلمة المرور.
            **kwargs:     معاملات إضافية (delta, ecc_symbols, redundancy).

        Returns:
            dict إحصائيات التضمين.

        Raises:
            NotImplementedError: إن لم تدعم المنصة التضمين في الصور.
        """
        self._require("image")
        return DCTImageEngine.embed(
            cover_image, output_image, secret_data, password,
            profile=self.profile.image, **kwargs,
        )

    def recover_from_image(
        self,
        stego_image: str,
        password: str,
        **kwargs,
    ) -> bytes:
        """
        استرجاع البيانات من صورة مُحمَّلة من المنصة.

        Args:
            stego_image: مسار الصورة المُحمَّلة (بعد ضغط المنصة).
            password:    كلمة المرور.
            **kwargs:    معاملات إضافية (ecc_symbols, redundancy).

        Returns:
            البيانات الأصلية (bytes).
        """
        self._require("image")
        return DCTImageEngine.extract(
            stego_image, password, profile=self.profile.image, **kwargs,
        )

    # ================================================================== #
    #  الفيديو — HyperGrid Engine
    # ================================================================== #

    def file_to_video(
        self,
        output_video: str,
        file_data: bytes,
        password: str,
        **kwargs,
    ) -> dict:
        """
        تحويل أي ملف إلى فيديو مُشفَّر بمصفوفة بصرية.

        Args:
            output_video: مسار الفيديو الناتج (.mp4).
            file_data:    محتوى الملف كـ bytes.
            password:     كلمة المرور.
            **kwargs:     معاملات إضافية (fps, block_size, ecc_symbols).

        Returns:
            dict إحصائيات الفيديو.

        Raises:
            NotImplementedError: إن لم تدعم المنصة الفيديو.
        """
        self._require("video")
        return HyperGridVideoEngine.encode(
            output_video, file_data, password,
            profile=self.profile.video, **kwargs,
        )

    def video_to_file(
        self,
        video_path: str,
        password: str,
        **kwargs,
    ) -> bytes:
        """
        استرجاع الملف الأصلي من فيديو مُحمَّل من المنصة.

        Args:
            video_path: مسار الفيديو المُحمَّل.
            password:   كلمة المرور.
            **kwargs:   معاملات إضافية (block_size, ecc_symbols).

        Returns:
            محتوى الملف الأصلي (bytes).
        """
        self._require("video")
        return HyperGridVideoEngine.decode(
            video_path, password, profile=self.profile.video, **kwargs,
        )

    # ================================================================== #
    #  الصوت — Acoustic FSK Engine
    # ================================================================== #

    def data_to_audio(
        self,
        output_wav: str,
        secret_data: bytes,
        password: str,
        **kwargs,
    ) -> dict:
        """
        تحويل بيانات إلى ملف صوتي WAV بتشفير FSK.

        Args:
            output_wav:  مسار ملف الصوت الناتج (.wav).
            secret_data: البيانات السرية (bytes).
            password:    كلمة المرور.
            **kwargs:    معاملات إضافية (ecc_symbols).

        Returns:
            dict إحصائيات الملف الصوتي.

        Raises:
            NotImplementedError: إن لم تدعم المنصة الصوت.
        """
        self._require("audio")
        return AcousticFSKEngine.encode_wav(
            output_wav, secret_data, password,
            profile=self.profile.audio, **kwargs,
        )

    def audio_to_data(
        self,
        media_path: str,
        password: str,
        **kwargs,
    ) -> bytes:
        """
        استرجاع البيانات من ملف صوتي WAV أو فيديو.

        Args:
            media_path: مسار الملف الصوتي (.wav) أو الفيديو (.mp4/...).
            password:   كلمة المرور.
            **kwargs:   معاملات إضافية (ecc_symbols).

        Returns:
            البيانات الأصلية (bytes).
        """
        self._require("audio")
        return AcousticFSKEngine.decode_media(
            media_path, password, profile=self.profile.audio, **kwargs,
        )

    # ================================================================== #
    #  مساعدات
    # ================================================================== #

    def _require(self, medium: str) -> None:
        """رفع استثناء واضح إن لم تدعم المنصة الوسيط المطلوب."""
        pf = getattr(self.profile, medium, None)
        if pf is None:
            raise NotImplementedError(
                f"منصة {self.profile.emoji} {self.profile.name} "
                f"لا تدعم التضمين في {medium}.\n"
                f"اختر منصة أخرى أو وسيطاً مختلفاً."
            )

    @staticmethod
    def list_platforms() -> list[PlatformProfile]:
        """إرجاع قائمة بكل المنصات المدعومة."""
        return list_platforms()

    @staticmethod
    def get_platform(key: str) -> PlatformProfile:
        """استرجاع ملف إعداد منصة بمفتاحها."""
        return get_platform(key)
