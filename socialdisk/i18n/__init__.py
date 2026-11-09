"""
SocialDisk — Internationalization (i18n) Engine
محرك التدويل ودعم اللغات المتعددة

يوفر واجهة برمجية موحدة وخفيفة ومستقلة تماماً لاسترجاع النصوص
بلغات متعددة (العربية والإنجليزية)، صالحة للاستخدام في الـ CLI
وأي واجهة رسومية مستقبلية (Desktop GUI / Web UI / API).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Optional

from socialdisk.i18n.ar import STRINGS as AR_STRINGS
from socialdisk.i18n.en import STRINGS as EN_STRINGS

SUPPORTED_LANGUAGES: dict[str, dict[str, str]] = {
    "ar": AR_STRINGS,
    "en": EN_STRINGS,
}

_CURRENT_LANG: str = "ar"
_INITIALIZED: bool = False

def _get_config_path(for_write: bool = False) -> Path:
    """تحديد المسار الصالح لملف الإعدادات بناءً على صلاحيات النظام."""
    # 1. فحص مجلد المشروع المحلي أولاً
    project_root = Path(__file__).resolve().parent.parent.parent
    local_cfg = project_root / ".socialdisk_config.json"

    # 2. مجلد المستخدم العام
    appdata = os.environ.get("APPDATA")
    user_cfg = None
    if appdata:
        user_cfg = Path(appdata) / "SocialDisk" / "config.json"
    else:
        try:
            user_cfg = Path.home() / ".socialdisk" / "config.json"
        except Exception:
            user_cfg = None

    if for_write:
        # إذا كنا نريد الكتابة، نحاول في مجلد المستخدم، وإن فشل فنستخدم الملف المحلي
        if user_cfg:
            try:
                user_cfg.parent.mkdir(parents=True, exist_ok=True)
                # تجربة إمكانية الكتابة
                test_file = user_cfg.parent / ".write_test"
                test_file.touch()
                test_file.unlink()
                return user_cfg
            except Exception:
                pass
        return local_cfg
    else:
        # عند القراءة، نقرأ من أيهما موجود
        if user_cfg and user_cfg.is_file():
            return user_cfg
        return local_cfg


def _load_config() -> dict[str, Any]:
    """قراءة ملف الإعدادات بهدوء ودون إثارة استثناءات."""
    cfg_path = _get_config_path(for_write=False)
    if not cfg_path.is_file():
        return {}
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_config(data: dict[str, Any]) -> None:
    """حفظ ملف الإعدادات بهدوء."""
    cfg_path = _get_config_path(for_write=True)
    try:
        cfg_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def init_language(fallback: str = "ar") -> None:
    """تهيئة اللغة من ملف الإعدادات أو القيمة الافتراضية."""
    global _CURRENT_LANG, _INITIALIZED
    cfg = _load_config()
    saved = cfg.get("language")
    if saved in SUPPORTED_LANGUAGES:
        _CURRENT_LANG = saved
    else:
        _CURRENT_LANG = fallback if fallback in SUPPORTED_LANGUAGES else "ar"
    _INITIALIZED = True


def is_first_run() -> bool:
    """هل هذه أول مرة يتم تشغيل الأداة فيها (لم يتم حفظ لغة مفضلة بعد)؟"""
    cfg = _load_config()
    return "language" not in cfg or cfg["language"] not in SUPPORTED_LANGUAGES


def get_language() -> str:
    """إرجاع كود اللغة النشطة حالياً (ar أو en)."""
    global _INITIALIZED
    if not _INITIALIZED:
        init_language()
    return _CURRENT_LANG


def set_language(lang: str, persist: bool = True) -> bool:
    """
    تغيير اللغة النشطة وتخزين التفضيل.
    
    Args:
        lang: كود اللغة ('ar' أو 'en').
        persist: حفظ التفضيل في ملف الإعدادات للمرات القادمة.
    """
    global _CURRENT_LANG, _INITIALIZED
    lang = lang.lower().strip()
    if lang not in SUPPORTED_LANGUAGES:
        return False
    _CURRENT_LANG = lang
    _INITIALIZED = True
    if persist:
        cfg = _load_config()
        cfg["language"] = lang
        _save_config(cfg)
    return True


def t(key: str, **kwargs: Any) -> str:
    """
    استرجاع النص المترجم بحسب اللغة النشطة.

    Args:
        key: مفتاح النص
        kwargs: متغيرات للتعويض داخل النص إن وجدت مثل {size}
    """
    global _INITIALIZED
    if not _INITIALIZED:
        init_language()

    lang_dict = SUPPORTED_LANGUAGES.get(_CURRENT_LANG, AR_STRINGS)
    text = lang_dict.get(key)

    if text is None:
        # البحث في البديل (العربية ثم الإنجليزية)
        text = AR_STRINGS.get(key, EN_STRINGS.get(key, key))

    if kwargs and isinstance(text, str):
        try:
            return text.format(**kwargs)
        except Exception:
            return text

    return text


def get_stat_label(stat_key: str) -> str:
    """استرجاع المسمى المترجم لمعاملات الإحصائيات."""
    dict_key = f"stat_{stat_key}"
    label = t(dict_key)
    if label != dict_key:
        return label
    return stat_key


def get_available_languages() -> list[tuple[str, str, str]]:
    """قائمة اللغات المتاحة: [(كود, اسم محلي, اسم إنجليزي)]."""
    return [
        ("ar", "العربية", "Arabic"),
        ("en", "English", "English"),
    ]


def parse_error_details(exc: Exception) -> tuple[str, str, str]:
    """
    تحليل الاستثناء وإرجاع:
    1. رسالة ودية وواضحة للمستخدم بلغته الحالية.
    2. حل مقترح عملي ومباشر.
    3. التفاصيل التقنية الأصلية للمطورين.
    """
    exc_str = str(exc)
    exc_type = type(exc).__name__
    raw_lower = f"{exc_type}: {exc_str}".lower()

    if any(k in raw_lower for k in ["wrong password", "decryption failed", "invalidtag", "fingerprint mismatch"]):
        return t("err_wrong_password_msg"), t("err_wrong_password_hint"), exc_str

    if any(k in raw_lower for k in ["larger than image capacity", "capacity", "not enough blocks"]):
        return t("err_capacity_msg"), t("err_capacity_hint"), exc_str

    if any(k in raw_lower for k in ["reed-solomon", "reedsolomon", "corruption level", "ecc_symbols"]):
        return t("err_corruption_msg"), t("err_corruption_hint"), exc_str

    if any(k in raw_lower for k in ["ffmpeg", "extract audio from video"]):
        return t("err_ffmpeg_msg"), t("err_ffmpeg_hint"), exc_str

    if isinstance(exc, FileNotFoundError) or any(k in raw_lower for k in ["file not found", "no such file", "failed to open"]):
        return t("err_file_not_found_msg"), t("err_file_not_found_hint"), exc_str

    if any(k in raw_lower for k in ["preamble", "sync tone", "audio file is too short"]):
        return t("err_no_audio_preamble_msg"), t("err_no_audio_preamble_hint"), exc_str

    if any(k in raw_lower for k in ["no valid frames", "block_size"]):
        return t("err_no_video_frames_msg"), t("err_no_video_frames_hint"), exc_str

    if any(k in raw_lower for k in ["crc32", "lzma", "packet size"]):
        return t("err_corrupted_payload_msg"), t("err_corrupted_payload_hint"), exc_str

    generic_msg = f"{t('error_prefix')} {exc_str}" if exc_str else t("error_prefix")
    return generic_msg, t("err_generic_hint"), exc_str


__all__ = [
    "t",
    "get_language",
    "set_language",
    "init_language",
    "is_first_run",
    "get_available_languages",
    "get_stat_label",
    "parse_error_details",
    "SUPPORTED_LANGUAGES",
]
