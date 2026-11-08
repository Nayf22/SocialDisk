"""
SocialVault API — Unified interface for all embedding and extraction engines

Quick example:
    from socialdisk import SocialVault

    # Working with Instagram
    vault = SocialVault("instagram")
    stats = vault.hide_in_image("cover.jpg", "stego.jpg", b"secret", "password123")
    data  = vault.recover_from_image("downloaded.jpg", "password123")

    # Working with WhatsApp
    vault = SocialVault("whatsapp")
    stats = vault.file_to_video("reel.mp4", open("file.pdf","rb").read(), "pass")
    data  = vault.video_to_file("downloaded.mp4", "pass")

    # Direct usage without an object (Static API)
    SocialVault.list_platforms()   # list of all platforms
"""
from __future__ import annotations

from socialdisk.platforms import PlatformProfile, get_platform, list_platforms
from socialdisk.engines.image import DCTImageEngine
from socialdisk.engines.video import HyperGridVideoEngine
from socialdisk.engines.audio import AcousticFSKEngine


class SocialVault:
    """
    Simplified interface for working with a specific social platform.

    Optimal parameters (delta, ecc_symbols, redundancy, ...) are selected
    automatically based on the documented compression characteristics of each platform.

    Example:
        vault = SocialVault("whatsapp")

        # Embedding
        stats = vault.hide_in_image("in.jpg", "out.jpg", payload, password)

        # Extraction
        data = vault.recover_from_image("downloaded.jpg", password)
    """

    def __init__(self, platform: str = "instagram"):
        """
        Args:
            platform: Platform key (instagram, whatsapp, twitter, ...).
                      Case-insensitive.
        """
        self.platform_key: str = platform.lower().strip()
        self.profile: PlatformProfile = get_platform(self.platform_key)

    def __repr__(self) -> str:
        return f"SocialVault(platform='{self.platform_key}')"

    # ================================================================== #
    #  Images — DCT Steganography
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
        Hide data inside an image using differential DCT steganography.

        Args:
            cover_image:  Path to the original cover image.
            output_image: Path to save the modified image (ready for upload).
            secret_data:  Secret data (bytes).
            password:     Password.
            **kwargs:     Additional parameters (delta, ecc_symbols, redundancy).

        Returns:
            dict of embedding statistics.

        Raises:
            NotImplementedError: If the platform does not support image embedding.
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
        Recover data from an image downloaded from the platform.

        Args:
            stego_image: Path to the downloaded image (after platform compression).
            password:    Password.
            **kwargs:    Additional parameters (ecc_symbols, redundancy).

        Returns:
            Original data (bytes).
        """
        self._require("image")
        return DCTImageEngine.extract(
            stego_image, password, profile=self.profile.image, **kwargs,
        )

    # ================================================================== #
    #  Video — HyperGrid Engine
    # ================================================================== #

    def file_to_video(
        self,
        output_video: str,
        file_data: bytes,
        password: str,
        **kwargs,
    ) -> dict:
        """
        Convert any file into an encrypted video using a visual matrix.

        Args:
            output_video: Path to the output video (.mp4).
            file_data:    File contents as bytes.
            password:     Password.
            **kwargs:     Additional parameters (fps, block_size, ecc_symbols).

        Returns:
            dict of video statistics.

        Raises:
            NotImplementedError: If the platform does not support video.
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
        Recover the original file from a video downloaded from the platform.

        Args:
            video_path: Path to the downloaded video.
            password:   Password.
            **kwargs:   Additional parameters (block_size, ecc_symbols).

        Returns:
            Original file contents (bytes).
        """
        self._require("video")
        return HyperGridVideoEngine.decode(
            video_path, password, profile=self.profile.video, **kwargs,
        )

    # ================================================================== #
    #  Audio — Acoustic FSK Engine
    # ================================================================== #

    def data_to_audio(
        self,
        output_wav: str,
        secret_data: bytes,
        password: str,
        **kwargs,
    ) -> dict:
        """
        Convert data into a WAV audio file encoded with FSK.

        Args:
            output_wav:  Path to the output audio file (.wav).
            secret_data: Secret data (bytes).
            password:    Password.
            **kwargs:    Additional parameters (ecc_symbols).

        Returns:
            dict of audio file statistics.

        Raises:
            NotImplementedError: If the platform does not support audio.
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
        Recover data from a WAV audio file or video.

        Args:
            media_path: Path to the audio file (.wav) or video (.mp4/...).
            password:   Password.
            **kwargs:   Additional parameters (ecc_symbols).

        Returns:
            Original data (bytes).
        """
        self._require("audio")
        return AcousticFSKEngine.decode_media(
            media_path, password, profile=self.profile.audio, **kwargs,
        )

    # ================================================================== #
    #  Helpers
    # ================================================================== #

    def _require(self, medium: str) -> None:
        """Raise a clear exception if the platform does not support the requested medium."""
        pf = getattr(self.profile, medium, None)
        if pf is None:
            raise NotImplementedError(
                f"Platform {self.profile.emoji} {self.profile.name} "
                f"does not support embedding in {medium}.\n"
                f"Choose a different platform or medium."
            )

    @staticmethod
    def list_platforms() -> list[PlatformProfile]:
        """Return a list of all supported platforms."""
        return list_platforms()

    @staticmethod
    def get_platform(key: str) -> PlatformProfile:
        """Retrieve a platform configuration profile by its key."""
        return get_platform(key)
