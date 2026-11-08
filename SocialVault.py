# SocialVault.py — Backward Compatibility Wrapper (v1.x → v2.0)
# ══════════════════════════════════════════════════════════════════════════
# هذا الملف يحافظ على التوافق مع الكود القديم الذي يستورد مباشرة من SocialVault.
# جميع الفئات والواجهات موجودة الآن في حزمة socialdisk/ المُطوَّرة.
#
# الاستخدام القديم (لا يزال يعمل):
#   from SocialVault import SocialVault, DCTImageEngine, VaultCore
#
# الاستخدام الجديد الموصى به:
#   from socialdisk import SocialVault
#   from socialdisk.engines.image import DCTImageEngine
#   from socialdisk.core import VaultCore
# ══════════════════════════════════════════════════════════════════════════

from socialdisk.core            import VaultCore
from socialdisk.engines.image   import DCTImageEngine
from socialdisk.engines.video   import HyperGridVideoEngine
from socialdisk.engines.audio   import AcousticFSKEngine
from socialdisk.api             import SocialVault

__all__ = [
    "VaultCore",
    "DCTImageEngine",
    "HyperGridVideoEngine",
    "AcousticFSKEngine",
    "SocialVault",
]
