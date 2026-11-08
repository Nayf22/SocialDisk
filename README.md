<div align="center">

<img src="https://img.shields.io/badge/SocialDisk-v2.0.0-6C63FF?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Platforms-14%2B-F59E0B?style=for-the-badge"/>
<img src="https://img.shields.io/badge/Tests-5%2F5%20Passing-22C55E?style=for-the-badge"/>

<br/>

```
  ____             _       _ ____  _     _
 / ___|  ___   ___(_) __ _| |  _ \(_)___| | __
 \___ \ / _ \ / __| |/ _` | | | | | / __| |/ /
  ___) | (_) | (__| | (_| | | |_| | \__ \   <
 |____/ \___/ \___|_|\__,_|_|____/|_|___/_|\_\
```

**Hide & encrypt data inside images, video, and audio — survives social media compression**

[English](#english) · [العربية](#arabic)

</div>

---

<a id="english"></a>
## 🇬🇧 English

### What is SocialDisk?

SocialDisk is a **multi-platform steganography suite** that lets you hide encrypted data inside ordinary media files (images, videos, audio). The hidden data survives the aggressive compression applied by social media platforms like Instagram, WhatsApp, TikTok, YouTube, Twitter, and more.

Under the hood, every piece of data goes through a **5-layer protection pipeline**:

```
Raw Data → LZMA-9 Compression → AES-256-GCM Encryption
        → Reed-Solomon ECC → Interleaving → Steganography
```

### ✨ Features

| Feature | Detail |
|---------|--------|
| 🔒 **AES-256-GCM encryption** | Military-grade authenticated encryption |
| 🧬 **Reed-Solomon ECC** | Corrects up to 50% bit errors |
| 🗜️ **LZMA-9 compression** | Maximum compression before encryption |
| 🔀 **Burst-error interleaving** | Spreads errors to maximize ECC recovery |
| 📸 **DCT Image engine** | Hides data in JPEG frequency coefficients |
| 🎬 **HyperGrid Video engine** | Embeds data in visual pixel grids across frames |
| 🎵 **Acoustic FSK Audio engine** | Encodes data as audio tones (survives AAC/Opus) |
| 🌍 **14+ platform profiles** | Pre-tuned for each platform's compression |
| 🖥️ **Beautiful CLI** | Interactive menu + command-line mode with Rich UI |

### 🌍 Supported Platforms

| Platform | Image | Video | Audio |
|----------|-------|-------|-------|
| Instagram | ✅ | ✅ | ✅ |
| WhatsApp | ✅ | ✅ | ✅ |
| TikTok | — | ✅ | ✅ |
| YouTube | — | ✅ | ✅ |
| Twitter/X | ✅ | ✅ | — |
| Discord | ✅ | ✅ | ✅ |
| Telegram | ✅ | ✅ | ✅ |
| Facebook | ✅ | ✅ | — |
| LinkedIn | ✅ | — | — |
| Snapchat | ✅ | ✅ | — |
| Signal | ✅ | — | ✅ |
| WeChat | ✅ | — | — |
| Reddit | ✅ | — | — |
| iMessage | ✅ | — | ✅ |

### 🚀 Quick Start

#### Installation

```bash
git clone https://github.com/YOUR_USERNAME/SocialDisk.git
cd SocialDisk
pip install -r requirements.txt
```

#### Interactive CLI (recommended)

```bash
python cli.py
```

Launches a beautiful interactive menu — no arguments needed.

#### Command-line Mode

```bash
# Hide a file inside an image (Instagram profile)
python cli.py hide --platform instagram --input secret.txt --cover photo.jpg --output stego.jpg

# Extract hidden data
python cli.py extract --platform instagram --input stego.jpg --output recovered.txt

# List all supported platforms
python cli.py --platforms

# Show help
python cli.py --help
```

#### Python API

```python
from socialdisk import SocialVault

vault = SocialVault(password="my_secret_password")

# Hide data in an image
vault.hide(
    cover="photo.jpg",
    output="stego.jpg",
    data=b"My secret message",
    platform="instagram"
)

# Extract data
secret = vault.extract(
    stego="stego.jpg",
    platform="instagram"
)
print(secret)  # b"My secret message"
```

### 🔬 How It Works

#### Image Engine (DCT Steganography)
Modifies DCT (Discrete Cosine Transform) frequency coefficients in JPEG blocks. Changes are imperceptible to the human eye but survive JPEG recompression at any quality setting ≥ platform threshold.

#### Video Engine (HyperGrid)
Embeds data as a visual pixel grid in specific video frames. The grid uses error-correcting codes (Reed-Solomon) to survive video codec compression (H.264/H.265).

#### Audio Engine (Acoustic FSK)
Encodes data as audio tones using Frequency Shift Keying (FSK):
- `bit=0` → 1500 Hz tone
- `bit=1` → 2700 Hz tone
- Preamble sync at 900 Hz

Tones are chosen to survive AAC (128 kbps) and Opus (32 kbps) compression. A 32-bit embedded header stores the exact bit count, eliminating sync detection errors.

### 🧪 Running Tests

```bash
python full_test.py
```

Expected output:
```
✅ [1/5] VaultCore pack/unpack roundtrip   — OK
✅ [2/5] DCT Image — Instagram (q=70)      — OK
✅ [3/5] DCT Image — WhatsApp (q=70, 5×)   — OK
✅ [4/5] HyperGrid Video — 10 KB file      — OK
✅ [5/5] Acoustic FSK — Arabic text        — OK

Result: 5/5 — SocialDisk v2.0 — 100% efficiency ✨
```

### 📁 Project Structure

```
SocialDisk/
├── socialdisk/                # Core Python package
│   ├── __init__.py
│   ├── core.py                # VaultCore: AES-256-GCM + Reed-Solomon + LZMA
│   ├── platforms.py           # Platform profiles (14+ platforms)
│   ├── api.py                 # Unified SocialVault API
│   └── engines/
│       ├── image.py           # DCT steganography engine
│       ├── video.py           # HyperGrid video engine
│       └── audio.py           # Acoustic FSK engine
├── cli.py                     # Beautiful CLI (Rich UI)
├── full_test.py               # 5-test comprehensive suite
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── LICENSE                    # MIT License
└── README.md                  # This file
```

### 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `numpy` | ≥1.24 | Array operations, FFT |
| `scipy` | ≥1.10 | WAV I/O, signal resampling |
| `opencv-python` | ≥4.7 | Image/video processing |
| `cryptography` | ≥41.0 | AES-256-GCM encryption |
| `reedsolo` | ≥1.7 | Reed-Solomon error correction |
| `rich` | ≥13.0 | Beautiful terminal UI |

### ⚠️ Legal Disclaimer

SocialDisk is intended for **privacy protection, security research, and educational purposes only**. Users are responsible for complying with the terms of service of any platform they use and all applicable laws. The authors are not responsible for misuse.

---

<a id="arabic"></a>
## 🇸🇦 العربية

### ما هو SocialDisk؟

**SocialDisk** هي أداة إخفاء وتشفير البيانات متعددة المنصات. تتيح لك إخفاء بيانات مشفرة داخل ملفات وسائط عادية (صور، فيديو، صوت)، وتظل البيانات المخفية سليمة حتى بعد الضغط الشديد الذي تُطبّقه منصات التواصل الاجتماعي كإنستغرام وواتساب وتيك توك ويوتيوب وغيرها.

### ✨ المميزات

- 🔒 **تشفير AES-256-GCM** — تشفير عسكري المستوى
- 🧬 **تصحيح أخطاء Reed-Solomon** — يصحح حتى 50% من الأخطاء
- 📸 **محرك الصور DCT** — إخفاء في معاملات JPEG الترددية
- 🎬 **محرك الفيديو HyperGrid** — تضمين في شبكة بكسل بصرية
- 🎵 **محرك الصوت Acoustic FSK** — ترميز النغمات الصوتية
- 🌍 **14+ منصة** — ملفات إعداد مُعايَرة لكل منصة
- 🖥️ **واجهة CLI جميلة** — قائمة تفاعلية بتصميم غني

### 🚀 التثبيت والاستخدام

```bash
git clone https://github.com/YOUR_USERNAME/SocialDisk.git
cd SocialDisk
pip install -r requirements.txt

# تشغيل القائمة التفاعلية
python cli.py

# إخفاء ملف
python cli.py hide --platform instagram --input سري.txt --cover صورة.jpg --output مخفي.jpg

# استخراج ملف
python cli.py extract --platform instagram --input مخفي.jpg --output مسترجع.txt
```

### 🧪 تشغيل الاختبارات

```bash
python full_test.py
```

### 🌍 المنصات المدعومة

إنستغرام · واتساب · تيك توك · يوتيوب · تويتر/X · ديسكورد · تيليغرام · فيسبوك · لينكدإن · سناب شات · سيغنال · ويشات · ريدت · iMessage

---

<div align="center">

**Made with ❤️ — SocialDisk v2.0.0**

[⬆ Back to top](#)

</div>
