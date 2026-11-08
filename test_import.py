"""اختبار سريع لاستيراد socialdisk وفحص المنصات"""
from socialdisk import SocialVault, VaultCore
from socialdisk.platforms import list_platforms
from socialdisk.engines.image import DCTImageEngine
from socialdisk.engines.video import HyperGridVideoEngine
from socialdisk.engines.audio import AcousticFSKEngine

print('✅ socialdisk package — imported OK')

platforms = list_platforms()
print(f'✅ platforms — {len(platforms)} منصة مدعومة:')
for p in platforms:
    caps = []
    if p.image: caps.append('صور')
    if p.video: caps.append('فيديو')
    if p.audio: caps.append('صوت')
    sep = " + "
    print(f'   {p.emoji}  {p.name:12} -> {sep.join(caps)}')

from SocialVault import SocialVault as IV_legacy
print()
print('✅ SocialVault.py compat wrapper — OK')

secret = 'مرحباً socialdisk v2.0!'.encode()
bits = VaultCore.pack_payload(secret, 'testpass', ecc_symbols=32)
recovered = VaultCore.unpack_payload(bits, 'testpass', ecc_symbols=32)
assert recovered == secret, 'VaultCore FAIL!'
print('✅ VaultCore pack/unpack roundtrip — OK')
print()
print('🎉 جميع الاختبارات نجحت — socialdisk v2.0 جاهز!')
