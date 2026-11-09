"""
Full test suite — 5 engines with real platform compression simulation
اختبار شامل للمحركات الثلاثة مع محاكاة ضغط المنصة
"""
# Ensure UTF-8 output on all platforms (critical for Windows CI)
import sys, os, hashlib, tempfile
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import numpy as np
import cv2

from socialdisk.core import VaultCore
from socialdisk.engines.image import DCTImageEngine
from socialdisk.engines.video import HyperGridVideoEngine
from socialdisk.engines.audio import AcousticFSKEngine
from socialdisk.platforms import get_platform

PASSWORD = "socialdisk_Test_2026"
SECRET_TEXT = "مرحباً! هذا اختبار socialdisk v2.0 — AES-256-GCM + Reed-Solomon.".encode("utf-8")
SECRET_FILE = os.urandom(10 * 1024)   # 10 KB عشوائية

PASS_MARK = "✅ نجح"
FAIL_MARK = "❌ فشل"

results = []

# ══════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print(" 🧪  socialdisk v2.0 — الاختبار الشامل")
print("═" * 60)

# ─────────────────────────────────────────────────────────────
# 1. VaultCore — ضغط + تشفير + ECC
# ─────────────────────────────────────────────────────────────
print("\n📦  [1/5] VaultCore — pack/unpack roundtrip")
try:
    bits = VaultCore.pack_payload(SECRET_TEXT, PASSWORD, ecc_symbols=64)
    out  = VaultCore.unpack_payload(bits, PASSWORD, ecc_symbols=64)
    ok = (out == SECRET_TEXT)
    print(f"   {PASS_MARK if ok else FAIL_MARK}  البيانات متطابقة 100%")
    print(f"   📊  حجم بتات الحزمة: {len(bits):,} بت")
    results.append(("VaultCore roundtrip", ok))
except Exception as e:
    print(f"   {FAIL_MARK}  {e}")
    results.append(("VaultCore roundtrip", False))

# ─────────────────────────────────────────────────────────────
# 2. DCT Image — Instagram (قياس q=70)
# ─────────────────────────────────────────────────────────────
print("\n📸  [2/5] DCT Image — Instagram (محاكاة JPEG q=70)")
try:
    profile = get_platform("instagram").image

    # صورة غلاف عشوائية واقعية
    cover = np.random.randint(40, 220, (1080, 1080, 3), dtype=np.uint8)
    # إضافة ضوضاء طبيعية لتجنب الكتل المنتظمة تماماً
    noise = np.random.randint(0, 30, cover.shape, dtype=np.uint8)
    cover = cv2.add(cover, noise)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        cover_path = tf.name
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        stego_path = tf.name
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        attack_path = tf.name

    cv2.imwrite(cover_path, cover)
    stats = DCTImageEngine.embed(cover_path, stego_path, SECRET_TEXT, PASSWORD, profile=profile)
    print(f"   📊  أبعاد: {stats['dimensions']}  |  استهلاك: {stats['capacity_used_percent']}%  |  Delta: {stats['delta_used']}")

    # محاكاة ضغط إنستغرام (q=70)
    img_att = cv2.imread(stego_path)
    cv2.imwrite(attack_path, img_att, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

    recovered = DCTImageEngine.extract(attack_path, PASSWORD, profile=profile)
    ok = (recovered == SECRET_TEXT)
    print(f"   {PASS_MARK if ok else FAIL_MARK}  الاسترجاع بعد JPEG q=70")
    results.append(("DCT Image (q=70)", ok))

    for p in [cover_path, stego_path, attack_path]:
        if os.path.exists(p): os.remove(p)
except Exception as e:
    print(f"   {FAIL_MARK}  {e}")
    results.append(("DCT Image (q=70)", False))

# ─────────────────────────────────────────────────────────────
# 3. DCT Image — WhatsApp (أشد ضغطاً q=70, redundancy=5)
# ─────────────────────────────────────────────────────────────
print("\n💬  [3/5] DCT Image — WhatsApp (محاكاة JPEG q=70, redundancy=5)")
try:
    profile_wa = get_platform("whatsapp").image

    cover2 = np.random.randint(40, 220, (1200, 1200, 3), dtype=np.uint8)
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        c2 = tf.name
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        s2 = tf.name
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        a2 = tf.name

    cv2.imwrite(c2, cover2)
    stats2 = DCTImageEngine.embed(c2, s2, SECRET_TEXT, PASSWORD, profile=profile_wa)
    print(f"   📊  أبعاد: {stats2['dimensions']}  |  Redundancy: {stats2['redundancy']}x  |  Delta: {stats2['delta_used']}")

    img2 = cv2.imread(s2)
    cv2.imwrite(a2, img2, [int(cv2.IMWRITE_JPEG_QUALITY), 70])
    rec2 = DCTImageEngine.extract(a2, PASSWORD, profile=profile_wa)
    ok2 = (rec2 == SECRET_TEXT)
    print(f"   {PASS_MARK if ok2 else FAIL_MARK}  الاسترجاع بعد WhatsApp compression")
    results.append(("DCT Image WhatsApp", ok2))

    for p in [c2, s2, a2]:
        if os.path.exists(p): os.remove(p)
except Exception as e:
    print(f"   {FAIL_MARK}  {e}")
    results.append(("DCT Image WhatsApp", False))

# ─────────────────────────────────────────────────────────────
# 4. HyperGrid Video — ملف 10KB
# ─────────────────────────────────────────────────────────────
print("\n🎬  [4/5] HyperGrid Video — ملف 10 KB عشوائي")
try:
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
        vid_path = tf.name

    vstats = HyperGridVideoEngine.encode(vid_path, SECRET_FILE, PASSWORD)
    print(f"   📊  دقة: {vstats['resolution']}  |  إطارات: {vstats['total_frames']}  |  مدة: {vstats['duration_sec']}s")

    recovered_file = HyperGridVideoEngine.decode(vid_path, PASSWORD)
    sha_orig = hashlib.sha256(SECRET_FILE).hexdigest()[:16]
    sha_recv = hashlib.sha256(recovered_file).hexdigest()[:16]
    ok_v = (sha_orig == sha_recv)
    print(f"   {PASS_MARK if ok_v else FAIL_MARK}  SHA-256 orig={sha_orig}...  recv={sha_recv}...")
    results.append(("HyperGrid Video", ok_v))

    if os.path.exists(vid_path): os.remove(vid_path)
except Exception as e:
    print(f"   {FAIL_MARK}  {e}")
    results.append(("HyperGrid Video", False))

# ─────────────────────────────────────────────────────────────
# 5. Acoustic FSK — نص عربي
# ─────────────────────────────────────────────────────────────
print("\n🎵  [5/5] Acoustic FSK — ترميز/فك ترميز صوتي")
try:
    # على Windows: NamedTemporaryFile يبقى مقفلاً — نستخدم mkstemp بدلاً منه
    fd, wav_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)  # نغلق المقبض فوراً حتى تستطيع المكتبات الكتابة والقراءة بحرية

    astats = AcousticFSKEngine.encode_wav(wav_path, SECRET_TEXT, PASSWORD)
    print(f"   📊  مدة: {astats['duration_sec']}s  |  معدل: {astats['baud_rate']} baud  |  بتات: {astats['total_bits']}")

    recovered_aud = AcousticFSKEngine.decode_media(wav_path, PASSWORD)
    ok_a = (recovered_aud == SECRET_TEXT)
    print(f"   {PASS_MARK if ok_a else FAIL_MARK}  البيانات الصوتية متطابقة")
    results.append(("Acoustic FSK", ok_a))

    if os.path.exists(wav_path): os.remove(wav_path)
except Exception as e:
    print(f"   {FAIL_MARK}  {e}")
    results.append(("Acoustic FSK", False))

# ══════════════════════════════════════════════════════════════
# النتيجة النهائية
# ══════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print(" 📋  ملخص النتائج")
print("═" * 60)
total = len(results)
passed = sum(1 for _, ok in results if ok)
for name, ok in results:
    mark = "✅" if ok else "❌"
    print(f"   {mark}  {name}")
print("─" * 60)
print(f"   النتيجة: {passed}/{total} اختبار نجح")
if passed == total:
    print("   🎉  socialdisk v2.0 — كفاءة 100% ✨")
else:
    print("   ⚠️  بعض الاختبارات فشلت — راجع السجل أعلاه")
print("═" * 60 + "\n")
