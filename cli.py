#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
socialdisk CLI v2.0 — واجهة سطر الأوامر الجميلة

الوضعان:
  1. التفاعلي   : python cli.py           (بدون معطيات → قائمة تفاعلية كاملة)
  2. المعطيات   : python cli.py <command> (للأتمتة والسكريبتات)

الأوامر المتاحة:
  hide-img     — إخفاء نص/ملف داخل صورة
  recover-img  — استخراج بيانات من صورة
  encode-vid   — تحويل ملف إلى فيديو
  decode-vid   — استخراج ملف من فيديو
  encode-aud   — تحويل بيانات إلى صوت
  decode-aud   — استخراج بيانات من صوت/فيديو

المتطلبات:
  pip install rich opencv-python scipy reedsolo cryptography numpy
"""
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tempfile
from typing import Optional

from rich import print as rprint
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

# ══════════════════════════════════════════════════════════════════════════
#  إعداد الـ Console والثيم
# ══════════════════════════════════════════════════════════════════════════

THEME = Theme(
    {
        "primary":    "bold cyan",
        "secondary":  "bold blue",
        "success":    "bold green",
        "error":      "bold red",
        "warning":    "bold yellow",
        "info":       "dim white",
        "platform":   "bold magenta",
        "stat_key":   "bold cyan",
        "stat_val":   "bold yellow",
        "title":      "bold white on dark_blue",
        "dim":        "dim",
    }
)

console = Console(theme=THEME, highlight=False)

VERSION = "2.0.0"

# ══════════════════════════════════════════════════════════════════════════
#  الشعار (ASCII Art Banner)
# ══════════════════════════════════════════════════════════════════════════

BANNER_LINES = [
    r" ██╗███╗  ██╗███████╗████████╗ █████╗ ██████╗ ██╗███████╗██╗  ██╗",
    r" ██║████╗ ██║██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██║██╔════╝██║ ██╔╝",
    r" ██║██╔██╗██║███████╗   ██║   ███████║██║  ██║██║███████╗█████╔╝ ",
    r" ██║██║╚████║╚════██║   ██║   ██╔══██║██║  ██║██║╚════██║██╔═██╗ ",
    r" ██║██║ ╚███║███████║   ██║   ██║  ██║██████╔╝██║███████║██║  ██╗",
    r" ╚═╝╚═╝  ╚══╝╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝╚═╝  ╚═╝",
]

BANNER_COLORS = ["bold cyan", "bold cyan", "bold blue", "bold blue", "bold magenta", "bold magenta"]


def print_banner(clear: bool = False) -> None:
    """طباعة الشعار بتدرج لوني جميل."""
    if clear:
        console.clear()
    console.print()
    for line, color in zip(BANNER_LINES, BANNER_COLORS):
        console.print(Align.center(f"[{color}]{line}[/]"))
    console.print()
    console.print(
        Align.center(
            Text.assemble(
                ("🛡️  ", "bold yellow"),
                ("Multi-Platform Steganography Suite", "bold white"),
                ("  🛡️", "bold yellow"),
            )
        )
    )
    console.print(
        Align.center(
            Text.assemble(
                ("  v", "dim"),
                (VERSION, "bold cyan"),
                ("  │  ", "dim"),
                ("AES-256-GCM", "bold green"),
                (" + ", "dim"),
                ("Reed-Solomon", "bold green"),
                (" + ", "dim"),
                ("DCT / HyperGrid / FSK", "bold green"),
                ("  ", "dim"),
            )
        )
    )
    console.print()


# ══════════════════════════════════════════════════════════════════════════
#  جدول المنصات
# ══════════════════════════════════════════════════════════════════════════

def print_platform_table() -> None:
    """طباعة جدول جميل بكل المنصات المدعومة وخصائصها."""
    from socialdisk.platforms import list_platforms

    table = Table(
        title="🌐  المنصات المدعومة",
        title_style="bold cyan",
        border_style="cyan",
        show_header=True,
        header_style="bold white on dark_blue",
        expand=True,
        padding=(0, 1),
    )
    table.add_column("#",         style="dim",        width=4,  justify="center")
    table.add_column("المنصة",   style="bold white",  min_width=18)
    table.add_column("صور 📸",   justify="center",    width=8)
    table.add_column("فيديو 🎬", justify="center",    width=8)
    table.add_column("صوت 🎵",   justify="center",    width=8)
    table.add_column("جودة JPEG", justify="center",   width=12)
    table.add_column("Delta DCT", justify="center",   width=10)
    table.add_column("الوصف",    style="dim",         min_width=28)

    for i, p in enumerate(list_platforms(), 1):
        jpeg_q  = str(p.image.jpeg_attack_quality) + "%" if p.image else "—"
        delta   = str(p.image.delta) if p.image else "—"
        table.add_row(
            str(i),
            f"{p.emoji}  {p.name}",
            "[success]✓[/]" if p.image else "[dim]—[/]",
            "[success]✓[/]" if p.video else "[dim]—[/]",
            "[success]✓[/]" if p.audio else "[dim]—[/]",
            jpeg_q,
            delta,
            p.description,
        )

    console.print()
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  شريط التقدم
# ══════════════════════════════════════════════════════════════════════════

def run_with_spinner(label: str, func, *args, **kwargs):
    """تشغيل دالة مع حلقة انتظار (spinner) جميلة."""
    with Progress(
        SpinnerColumn(style="bold cyan", spinner_name="dots"),
        TextColumn("[bold white]{task.description}"),
        TimeElapsedColumn(),
        console=console,
        transient=False,
    ) as progress:
        task = progress.add_task(f"  {label}", total=None)
        try:
            result = func(*args, **kwargs)
            progress.update(task, description=f"  [success]✅ {label}[/]")
            return result
        except Exception:
            progress.update(task, description=f"  [error]❌ {label}[/]")
            raise


# ══════════════════════════════════════════════════════════════════════════
#  عرض الإحصائيات
# ══════════════════════════════════════════════════════════════════════════

_STAT_LABELS: dict[str, str] = {
    "dimensions":               "📐  أبعاد الصورة",
    "raw_size_bytes":           "📦  حجم البيانات الأصلي",
    "encoded_bits":             "🔢  عدد البتات المُضمَّنة",
    "total_blocks":             "🔲  إجمالي الكتل 8×8",
    "capacity_used_percent":    "📊  نسبة استهلاك السعة",
    "delta_used":               "⚡  قوة الإشارة (Delta)",
    "ecc_symbols":              "🛡️   رموز Reed-Solomon",
    "redundancy":               "🔁  عامل التكرار المكاني",
    "resolution":               "🖥️   دقة الفيديو",
    "total_frames":             "🎞️   عدد الإطارات",
    "duration_sec":             "⏱️   المدة الزمنية",
    "capacity_per_frame_bytes": "💾  سعة كل إطار",
    "total_capacity_bytes":     "💾  السعة الكلية",
    "block_size":               "🔲  حجم بلوك الفيديو",
    "baud_rate":                "📡  معدل البث (بود/ث)",
    "total_bits":               "🔢  إجمالي البتات الصوتية",
    "freq_zero_hz":             "〰️  تردد البت=0",
    "freq_one_hz":              "〰️  تردد البت=1",
    "sync_freq_hz":             "🔔  تردد المزامنة",
}


def print_stats(stats: dict, title: str = "📊  إحصائيات العملية") -> None:
    """طباعة إحصائيات العملية بجدول جميل."""
    table = Table(
        title=title,
        title_style="bold green",
        border_style="green",
        show_header=False,
        expand=False,
        padding=(0, 2),
    )
    table.add_column("المعامل", style="stat_key", min_width=30)
    table.add_column("القيمة",  style="stat_val")

    for key, val in stats.items():
        label = _STAT_LABELS.get(key, key)
        if isinstance(val, float):
            display = f"{val:.2f}"
        elif isinstance(val, int) and "bytes" in key.lower():
            if val >= 1024 * 1024:
                display = f"{val:,} بايت  ({val / 1024 / 1024:.2f} MB)"
            elif val >= 1024:
                display = f"{val:,} بايت  ({val / 1024:.1f} KB)"
            else:
                display = f"{val:,} بايت"
        else:
            display = str(val)
        table.add_row(label, display)

    console.print()
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  معالجة البيانات المستخرجة
# ══════════════════════════════════════════════════════════════════════════

def handle_extracted(data: bytes, out_path: Optional[str]) -> None:
    """حفظ أو عرض البيانات المستخرجة."""
    if out_path:
        with open(out_path, "wb") as f:
            f.write(data)
        console.print(
            f"\n[success]✅ تم حفظ البيانات في:[/] [bold white]{out_path}[/]  "
            f"[dim]({len(data):,} بايت)[/]"
        )
    else:
        try:
            text = data.decode("utf-8")
            console.print()
            console.print(
                Panel(
                    f"[bold white]{escape(text)}[/]",
                    title="[bold green]🔓  البيانات المستخرجة[/]",
                    border_style="green",
                    padding=(1, 3),
                )
            )
        except UnicodeDecodeError:
            console.print(
                f"\n[warning]⚠️  البيانات ثنائية ({len(data):,} بايت).[/]\n"
                "أضف [-o مسار_الحفظ] لتخزينها كملف."
            )


def get_payload(text_arg: Optional[str], file_arg: Optional[str]) -> bytes:
    """تحويل مصدر البيانات (نص أو ملف) إلى bytes."""
    if text_arg:
        return text_arg.encode("utf-8")
    if file_arg:
        with open(file_arg, "rb") as f:
            return f.read()
    raise ValueError("يجب تحديد نص (-t) أو ملف (-f).")


# ══════════════════════════════════════════════════════════════════════════
#  الوضع التفاعلي
# ══════════════════════════════════════════════════════════════════════════

def interactive_select_platform() -> str:
    """اختيار المنصة بواجهة بطاقات جميلة."""
    from socialdisk.platforms import list_platforms

    platforms = list_platforms()
    console.print()
    console.print(Rule("[bold cyan]📱  اختر المنصة الاجتماعية[/]", style="blue"))
    console.print()

    # عرض كبطاقات (4 في الصف)
    cards = []
    for i, p in enumerate(platforms, 1):
        caps = []
        if p.image: caps.append("📸صور")
        if p.video: caps.append("🎬فيديو")
        if p.audio: caps.append("🎵صوت")
        cap_str = " ".join(caps) or "—"
        card_txt = Text.assemble(
            (f"  {i:2}. ", "bold yellow"),
            (f"{p.emoji} ", ""),
            (p.name + "\n", "bold white"),
            (f"      {cap_str}", "dim"),
        )
        cards.append(Panel(card_txt, border_style="blue", padding=(0, 1), expand=False))

    for row in range(0, len(cards), 4):
        console.print(Columns(cards[row : row + 4], equal=True))

    console.print()
    idx = IntPrompt.ask("[bold cyan]رقم المنصة[/]", default=1, console=console)
    if 1 <= idx <= len(platforms):
        chosen = platforms[idx - 1]
        console.print(
            f"\n[success]✅ المنصة المختارة:[/] [platform]{chosen.emoji}  {chosen.name}[/]\n"
        )
        return chosen.key
    console.print("[warning]رقم غير صالح، تم اختيار Instagram افتراضياً.[/]")
    return "instagram"


def interactive_select_operation(profile) -> str:
    """اختيار نوع العملية بناءً على ما تدعمه المنصة."""
    options: list[tuple[str, str, str]] = []
    if profile.image: options += [
        ("1", "📸  إخفاء بيانات في صورة",      "image_embed"),
        ("2", "🔓  استخراج بيانات من صورة",     "image_extract"),
    ]
    if profile.video: options += [
        ("3", "🎬  تحويل ملف إلى فيديو",        "video_embed"),
        ("4", "🎬  استخراج ملف من فيديو",       "video_extract"),
    ]
    if profile.audio: options += [
        ("5", "🎵  تحويل بيانات إلى صوت (WAV)", "audio_embed"),
        ("6", "🎵  استخراج بيانات من صوت",      "audio_extract"),
    ]

    console.print(Rule("[bold cyan]⚙️   اختر العملية[/]", style="blue"))
    console.print()
    for num, label, _ in options:
        console.print(f"   [bold yellow]{num}.[/]  {label}")
    console.print()

    choice = Prompt.ask("[bold cyan]رقم العملية[/]", default=options[0][0], console=console)
    for num, _, key in options:
        if choice == num:
            return key
    return options[0][2]


# ─── تدفقات التضمين ───────────────────────────────────────────────────────

def _prompt_payload() -> bytes:
    """سؤال المستخدم عن مصدر البيانات السرية."""
    console.print("\n[bold white]مصدر البيانات السرية:[/]")
    console.print("   [yellow]1.[/]  نص مباشر")
    console.print("   [yellow]2.[/]  ملف")
    src = Prompt.ask("[bold cyan]اختر[/]", default="1", console=console)
    if src == "2":
        fp = Prompt.ask("[bold cyan]📂  مسار الملف[/]", console=console)
        with open(fp, "rb") as f:
            data = f.read()
        console.print(f"[dim]📦 تم قراءة الملف: {len(data):,} بايت[/]")
        return data
    txt = Prompt.ask("[bold cyan]✏️   النص السري[/]", console=console)
    return txt.encode("utf-8")


def flow_image_embed(vault) -> None:
    cover    = Prompt.ask("[bold cyan]📂  صورة الغلاف[/]", console=console)
    output   = Prompt.ask("[bold cyan]💾  مسار حفظ الصورة المُعدَّلة[/]", console=console)
    payload  = _prompt_payload()
    password = Prompt.ask("[bold cyan]🔑  كلمة المرور[/]", password=True, console=console)
    console.print()
    try:
        stats = run_with_spinner("⚙️  جارٍ التضمين في الصورة...", vault.hide_in_image,
                                  cover, output, payload, password)
        console.print(f"\n[success]✅ الصورة جاهزة:[/] [bold white]{output}[/]")
        print_stats(stats, "📊  إحصائيات التضمين في الصورة")
    except Exception as e:
        console.print(f"\n[error]❌ خطأ: {escape(str(e))}[/]")


def flow_image_extract(vault) -> None:
    img      = Prompt.ask("[bold cyan]📂  مسار الصورة (بعد التحميل من المنصة)[/]", console=console)
    password = Prompt.ask("[bold cyan]🔑  كلمة المرور[/]", password=True, console=console)
    out      = Prompt.ask("[bold cyan]💾  مسار الحفظ (Enter = عرض النص)[/]", default="", console=console)
    console.print()
    try:
        data = run_with_spinner("🔓  جارٍ الاستخراج من الصورة...", vault.recover_from_image, img, password)
        handle_extracted(data, out or None)
    except Exception as e:
        console.print(f"\n[error]❌ خطأ: {escape(str(e))}[/]")


def flow_video_embed(vault) -> None:
    fp       = Prompt.ask("[bold cyan]📂  مسار الملف المراد تخزينه[/]", console=console)
    output   = Prompt.ask("[bold cyan]💾  مسار الفيديو الناتج (.mp4)[/]", console=console)
    password = Prompt.ask("[bold cyan]🔑  كلمة المرور[/]", password=True, console=console)
    with open(fp, "rb") as f:
        payload = f.read()
    console.print(f"[dim]📦 حجم الملف: {len(payload):,} بايت[/]\n")
    try:
        stats = run_with_spinner("🎬  جارٍ توليد الفيديو...", vault.file_to_video,
                                  output, payload, password)
        console.print(f"\n[success]✅ الفيديو جاهز:[/] [bold white]{output}[/]")
        print_stats(stats, "📊  إحصائيات الفيديو")
    except Exception as e:
        console.print(f"\n[error]❌ خطأ: {escape(str(e))}[/]")


def flow_video_extract(vault) -> None:
    vid      = Prompt.ask("[bold cyan]📂  مسار الفيديو (بعد التحميل)[/]", console=console)
    out      = Prompt.ask("[bold cyan]💾  مسار الملف المسترجع[/]", console=console)
    password = Prompt.ask("[bold cyan]🔑  كلمة المرور[/]", password=True, console=console)
    console.print()
    try:
        data = run_with_spinner("🎬  جارٍ استرجاع الملف...", vault.video_to_file, vid, password)
        with open(out, "wb") as f:
            f.write(data)
        console.print(
            f"\n[success]✅ تم حفظ الملف:[/] [bold white]{out}[/]  "
            f"[dim]({len(data):,} بايت)[/]"
        )
    except Exception as e:
        console.print(f"\n[error]❌ خطأ: {escape(str(e))}[/]")


def flow_audio_embed(vault) -> None:
    output   = Prompt.ask("[bold cyan]💾  مسار ملف الصوت الناتج (.wav)[/]", console=console)
    payload  = _prompt_payload()
    password = Prompt.ask("[bold cyan]🔑  كلمة المرور[/]", password=True, console=console)
    console.print()
    try:
        stats = run_with_spinner("🎵  جارٍ توليد الموجة الصوتية...", vault.data_to_audio,
                                  output, payload, password)
        console.print(f"\n[success]✅ الصوت جاهز:[/] [bold white]{output}[/]")
        print_stats(stats, "📊  إحصائيات الملف الصوتي")
    except Exception as e:
        console.print(f"\n[error]❌ خطأ: {escape(str(e))}[/]")


def flow_audio_extract(vault) -> None:
    media    = Prompt.ask("[bold cyan]📂  مسار الملف الصوتي / الفيديو[/]", console=console)
    password = Prompt.ask("[bold cyan]🔑  كلمة المرور[/]", password=True, console=console)
    out      = Prompt.ask("[bold cyan]💾  مسار الحفظ (Enter = عرض النص)[/]", default="", console=console)
    console.print()
    try:
        data = run_with_spinner("🎵  جارٍ تحليل الصوت...", vault.audio_to_data, media, password)
        handle_extracted(data, out or None)
    except Exception as e:
        console.print(f"\n[error]❌ خطأ: {escape(str(e))}[/]")


# ─── الاختبار التلقائي ────────────────────────────────────────────────────

def run_self_test() -> None:
    """اختبار تلقائي شامل للمحركات الثلاثة."""
    import cv2
    from socialdisk.engines.image import DCTImageEngine
    from socialdisk.engines.video import HyperGridVideoEngine
    from socialdisk.engines.audio import AcousticFSKEngine

    console.print()
    console.print(Panel(
        "[bold white]يختبر هذا الاختبار المحركات الثلاثة مع محاكاة ضغط المنصة:[/]\n"
        "  📸 صورة DCT — محاكاة JPEG q=70\n"
        "  🎬 فيديو HyperGrid — ترميز واسترجاع مباشر\n"
        "  🎵 صوت FSK — ترميز واسترجاع WAV",
        title="[bold cyan]🧪  الاختبار التلقائي[/]",
        border_style="cyan",
        padding=(0, 2),
    ))

    password = "socialdisk_AutoTest_2026"
    sample   = "مرحباً! هذا اختبار socialdisk v2.0 — جميع المحركات.".encode("utf-8")
    results: list[tuple[str, bool, str]] = []

    with Progress(
        SpinnerColumn(style="bold cyan", spinner_name="dots"),
        TextColumn("[bold white]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as prog:

        # ─── اختبار 1: صورة DCT ───────────────────────────────────────
        t1 = prog.add_task("📸  اختبار الصورة (DCT Steganography) ...", total=None)
        try:
            import numpy as _np
            dummy = _np.random.randint(60, 200, (1080, 1080, 3), dtype=_np.uint8)
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                cover_p = tf.name
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                stego_p = tf.name
            with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
                attack_p = tf.name

            cv2.imwrite(cover_p, dummy)
            stats_i = DCTImageEngine.embed(cover_p, stego_p, sample, password)

            # محاكاة ضغط المنصة (q=70)
            attacked = cv2.imread(stego_p)
            cv2.imwrite(attack_p, attacked, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

            recovered_i = DCTImageEngine.extract(attack_p, password)
            ok_i = recovered_i == sample
            detail = f"q=70  |  cap={stats_i.get('capacity_used_percent', '?')}%"
            results.append(("📸  DCT Image (simulated q=70)", ok_i, detail))
            for p_ in [cover_p, stego_p, attack_p]:
                if os.path.exists(p_): os.remove(p_)
        except Exception as exc:
            results.append(("📸  DCT Image", False, str(exc)[:80]))
        prog.update(t1, completed=1, total=1)

        # ─── اختبار 2: فيديو HyperGrid ────────────────────────────────
        t2 = prog.add_task("🎬  اختبار الفيديو (HyperGrid Engine) ...", total=None)
        try:
            large = os.urandom(10 * 1024)   # 10 KB عشوائية
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
                vid_p = tf.name
            stats_v = HyperGridVideoEngine.encode(vid_p, large, password)
            recovered_v = HyperGridVideoEngine.decode(vid_p, password)
            ok_v = (
                hashlib.sha256(large).digest() == hashlib.sha256(recovered_v).digest()
            )
            detail = f"إطارات={stats_v.get('total_frames', '?')}  |  {stats_v.get('resolution', '?')}"
            results.append(("🎬  HyperGrid Video", ok_v, detail))
            if os.path.exists(vid_p): os.remove(vid_p)
        except Exception as exc:
            results.append(("🎬  HyperGrid Video", False, str(exc)[:80]))
        prog.update(t2, completed=1, total=1)

        # ─── اختبار 3: صوت FSK ────────────────────────────────────────
        t3 = prog.add_task("🎵  اختبار الصوت (Acoustic FSK Engine) ...", total=None)
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
                wav_p = tf.name
            stats_a = AcousticFSKEngine.encode_wav(wav_p, sample, password)
            recovered_a = AcousticFSKEngine.decode_media(wav_p, password)
            ok_a = recovered_a == sample
            detail = f"مدة={stats_a.get('duration_sec', '?')}s  |  baud={stats_a.get('baud_rate', '?')}"
            results.append(("🎵  Acoustic FSK", ok_a, detail))
            if os.path.exists(wav_p): os.remove(wav_p)
        except Exception as exc:
            results.append(("🎵  Acoustic FSK", False, str(exc)[:80]))
        prog.update(t3, completed=1, total=1)

    # ─── جدول النتائج
    res_table = Table(
        title="نتائج الاختبار",
        title_style="bold cyan",
        border_style="blue",
        header_style="bold white",
    )
    res_table.add_column("المحرك",   style="bold white", min_width=28)
    res_table.add_column("الحالة",   justify="center",   width=12)
    res_table.add_column("التفاصيل", style="dim",        min_width=35)

    all_ok = True
    for name, ok, detail in results:
        status = "[success]✅ نجاح[/]" if ok else "[error]❌ فشل[/]"
        res_table.add_row(name, status, detail)
        if not ok:
            all_ok = False

    console.print()
    console.print(res_table)
    console.print()

    if all_ok:
        console.print(Panel(
            "[bold green]✅  جميع الاختبارات نجحت! المكتبة تعمل بكفاءة 100%.[/]",
            border_style="green",
            padding=(0, 2),
        ))
    else:
        console.print(Panel(
            "[bold red]⚠️  بعض الاختبارات فشلت.\n"
            "تأكد من تثبيت جميع المتطلبات:\n"
            "  pip install opencv-python scipy reedsolo cryptography numpy rich[/]",
            border_style="red",
            padding=(0, 2),
        ))


# ─── صفحة المساعدة ───────────────────────────────────────────────────────

def show_help() -> None:
    console.print()
    console.print(Panel(
        "[bold cyan]socialdisk v2.0[/] — أداة تخفي وتشفير البيانات عبر المنصات الاجتماعية\n\n"
        "[bold white]الوضع التفاعلي (بدون معطيات):[/]\n"
        "  [cyan]python cli.py[/]\n\n"
        "[bold white]أوامر الصور:[/]\n"
        "  [cyan]python cli.py hide-img    -i cover.jpg -o out.jpg -p pass -t \"سر\" --platform instagram[/]\n"
        "  [cyan]python cli.py recover-img -i img.jpg   -p pass              --platform instagram[/]\n\n"
        "[bold white]أوامر الفيديو:[/]\n"
        "  [cyan]python cli.py encode-vid -f secret.zip -o reel.mp4 -p pass --platform tiktok[/]\n"
        "  [cyan]python cli.py decode-vid -v reel.mp4   -o out.zip  -p pass --platform tiktok[/]\n\n"
        "[bold white]أوامر الصوت:[/]\n"
        "  [cyan]python cli.py encode-aud -t \"رسالة\" -o audio.wav -p pass --platform whatsapp[/]\n"
        "  [cyan]python cli.py decode-aud -m audio.wav -p pass              --platform whatsapp[/]\n\n"
        "[bold white]خيارات مشتركة:[/]\n"
        "  [cyan]--platform  -P[/]  المنصة (instagram, whatsapp, twitter, tiktok, youtube, ...)\n"
        "  [cyan]--platforms[/]     عرض قائمة كل المنصات\n"
        "  [cyan]--ecc N[/]         تجاوز عدد رموز Reed-Solomon\n"
        "  [cyan]--delta F[/]       تجاوز قوة إشارة DCT (للصور فقط)\n\n"
        "[bold white]التقنيات الأساسية:[/]\n"
        "  🔐 [green]AES-256-GCM[/]        — تشفير عسكري المستوى\n"
        "  🛡️  [green]Reed-Solomon ECC[/]   — تصحيح أخطاء الضغط\n"
        "  🔀 [green]Interleaving[/]        — مقاومة أخطاء الحزمة\n"
        "  📐 [green]Differential DCT[/]    — إخفاء لاحصائي في الصور\n"
        "  🎬 [green]HyperGrid Video[/]     — مصفوفة بصرية للملفات الكبيرة\n"
        "  🎵 [green]Acoustic FSK+FFT[/]    — مودم صوتي مقاوم لـ AAC/Opus",
        title="[bold cyan]❓  المساعدة[/]",
        border_style="cyan",
        padding=(1, 2),
    ))


# ─── القائمة الرئيسية التفاعلية ──────────────────────────────────────────

def interactive_mode() -> None:
    """الوضع التفاعلي الكامل بقائمة رئيسية."""
    from socialdisk.api import SocialVault

    print_banner(clear=True)

    while True:
        console.print(Rule("[bold cyan]  القائمة الرئيسية  [/]", style="blue"))
        console.print()

        menu = [
            ("1", "🚀  تضمين بيانات / إخفاء ملف",    "embed"),
            ("2", "🔓  استخراج بيانات مُخفاة",         "extract"),
            ("3", "🌐  استعراض المنصات المدعومة",      "platforms"),
            ("4", "🧪  تشغيل الاختبار التلقائي",       "test"),
            ("5", "❓  مساعدة واستخدام الأوامر",        "help"),
            ("0", "🚪  خروج",                           "exit"),
        ]
        for num, label, _ in menu:
            clr = "bold red" if num == "0" else "bold white"
            console.print(f"   [bold yellow]{num}.[/]   [{clr}]{label}[/]")

        console.print()
        choice = Prompt.ask("[bold cyan]اختيارك[/]", default="1", console=console)
        console.print()

        if choice == "0":
            console.print(Panel(
                "[bold cyan]شكراً لاستخدامك socialdisk 🛡️[/]",
                border_style="cyan", padding=(0, 3),
            ))
            break

        elif choice == "1":
            platform_key = interactive_select_platform()
            vault = SocialVault(platform_key)
            op    = interactive_select_operation(vault.profile)
            console.print()

            dispatch = {
                "image_embed":   flow_image_embed,
                "image_extract": flow_image_extract,
                "video_embed":   flow_video_embed,
                "video_extract": flow_video_extract,
                "audio_embed":   flow_audio_embed,
                "audio_extract": flow_audio_extract,
            }
            dispatch.get(op, lambda v: None)(vault)
            console.print()
            Prompt.ask("[dim]اضغط Enter للعودة إلى القائمة[/]", default="", console=console)
            print_banner(clear=True)

        elif choice == "2":
            platform_key = interactive_select_platform()
            vault = SocialVault(platform_key)
            op    = interactive_select_operation(vault.profile)
            if not op.endswith("_extract"):
                # حوّل التضمين إلى استخراج
                op = op.replace("_embed", "_extract")
            console.print()
            dispatch = {
                "image_extract": flow_image_extract,
                "video_extract": flow_video_extract,
                "audio_extract": flow_audio_extract,
            }
            dispatch.get(op, lambda v: None)(vault)
            console.print()
            Prompt.ask("[dim]اضغط Enter للعودة[/]", default="", console=console)
            print_banner(clear=True)

        elif choice == "3":
            print_platform_table()
            console.print()
            Prompt.ask("[dim]اضغط Enter للعودة[/]", default="", console=console)
            print_banner(clear=True)

        elif choice == "4":
            run_self_test()
            console.print()
            Prompt.ask("[dim]اضغط Enter للعودة[/]", default="", console=console)
            print_banner(clear=True)

        elif choice == "5":
            show_help()
            console.print()
            Prompt.ask("[dim]اضغط Enter للعودة[/]", default="", console=console)
            print_banner(clear=True)

        else:
            console.print("[warning]اختيار غير صالح.[/]\n")


# ══════════════════════════════════════════════════════════════════════════
#  وضع سطر الأوامر (CLI Args)
# ══════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description="🛡️ socialdisk v2.0 — Multi-Platform Steganography Suite",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=True,
    )
    parser.add_argument(
        "--platform", "-P", default="instagram", metavar="PLATFORM",
        help="المنصة المستهدفة\n"
             "القيم: instagram, whatsapp, twitter, tiktok, youtube,\n"
             "        telegram, discord, facebook, snapchat, reddit,\n"
             "        linkedin, pinterest, mastodon, signal\n"
             "الافتراضي: instagram",
    )
    parser.add_argument(
        "--platforms", action="store_true",
        help="عرض قائمة كل المنصات والخروج",
    )

    sub = parser.add_subparsers(dest="command")

    # ── hide-img ──────────────────────────────────────────────────────────
    p_hi = sub.add_parser("hide-img", help="إخفاء نص أو ملف داخل صورة")
    p_hi.add_argument("-i", "--image",    required=True, help="صورة الغلاف الأصلية")
    p_hi.add_argument("-o", "--out",      required=True, help="الصورة المُعدَّلة (ناتج)")
    p_hi.add_argument("-p", "--password", required=True, help="كلمة المرور")
    p_hi.add_argument("-t", "--text",     help="نص سري مباشر")
    p_hi.add_argument("-f", "--file",     help="مسار ملف للإخفاء")
    p_hi.add_argument("--delta",    type=float, help="قوة إشارة DCT (يتجاوز إعداد المنصة)")
    p_hi.add_argument("--ecc",      type=int,   help="رموز Reed-Solomon")
    p_hi.add_argument("--redundancy", type=int, help="عامل التكرار المكاني")

    # ── recover-img ───────────────────────────────────────────────────────
    p_ri = sub.add_parser("recover-img", help="استرجاع بيانات من صورة مُحمَّلة")
    p_ri.add_argument("-i", "--image",    required=True, help="الصورة المُحمَّلة من المنصة")
    p_ri.add_argument("-p", "--password", required=True, help="كلمة المرور")
    p_ri.add_argument("-o", "--out",      help="مسار حفظ الناتج (فارغ = طباعة النص)")
    p_ri.add_argument("--ecc",      type=int, help="رموز Reed-Solomon")
    p_ri.add_argument("--redundancy", type=int, help="عامل التكرار")

    # ── encode-vid ────────────────────────────────────────────────────────
    p_ev = sub.add_parser("encode-vid", help="تحويل ملف إلى فيديو مُشفَّر")
    p_ev.add_argument("-f", "--file",     required=True, help="الملف المصدر")
    p_ev.add_argument("-o", "--out",      required=True, help="الفيديو الناتج (.mp4)")
    p_ev.add_argument("-p", "--password", required=True, help="كلمة المرور")
    p_ev.add_argument("--ecc",        type=int, help="رموز Reed-Solomon")
    p_ev.add_argument("--block-size", type=int, help="حجم بلوك الفيديو (بكسل)")

    # ── decode-vid ────────────────────────────────────────────────────────
    p_dv = sub.add_parser("decode-vid", help="استرجاع ملف من فيديو مُحمَّل")
    p_dv.add_argument("-v", "--video",    required=True, help="الفيديو المُحمَّل من المنصة")
    p_dv.add_argument("-o", "--out",      required=True, help="مسار الملف المسترجع")
    p_dv.add_argument("-p", "--password", required=True, help="كلمة المرور")
    p_dv.add_argument("--ecc",        type=int, help="رموز Reed-Solomon")
    p_dv.add_argument("--block-size", type=int, help="حجم بلوك الفيديو (بكسل)")

    # ── encode-aud ────────────────────────────────────────────────────────
    p_ea = sub.add_parser("encode-aud", help="تحويل بيانات إلى ملف صوتي WAV")
    p_ea.add_argument("-o", "--out",      required=True, help="ملف الصوت الناتج (.wav)")
    p_ea.add_argument("-p", "--password", required=True, help="كلمة المرور")
    p_ea.add_argument("-t", "--text",     help="نص لتحويله")
    p_ea.add_argument("-f", "--file",     help="ملف لتحويله")
    p_ea.add_argument("--ecc", type=int,  help="رموز Reed-Solomon")

    # ── decode-aud ────────────────────────────────────────────────────────
    p_da = sub.add_parser("decode-aud", help="استرجاع بيانات من صوت أو فيديو")
    p_da.add_argument("-m", "--media",    required=True, help="الملف الصوتي (.wav) أو الفيديو")
    p_da.add_argument("-p", "--password", required=True, help="كلمة المرور")
    p_da.add_argument("-o", "--out",      help="مسار الحفظ (فارغ = طباعة النص)")
    p_da.add_argument("--ecc", type=int,  help="رموز Reed-Solomon")

    return parser


def cli_mode(args: argparse.Namespace) -> None:
    """تنفيذ أمر CLI من المعطيات مع عرض جميل بـ Rich."""
    from socialdisk.api import SocialVault

    print_banner()

    if args.platforms:
        print_platform_table()
        return

    if not args.command:
        console.print(
            "[warning]لم يُحدَّد أمر. شغّل بدون معطيات للوضع التفاعلي، أو استخدم --help.[/]"
        )
        return

    vault   = SocialVault(args.platform)
    profile = vault.profile

    console.print(
        Panel(
            Text.assemble(
                (f"{profile.emoji}  {profile.name}", "platform"),
                ("   │   أمر: ", "dim"),
                (args.command, "bold white"),
            ),
            border_style="cyan",
            title="[bold cyan]socialdisk[/]",
            padding=(0, 2),
        )
    )
    console.print()

    try:
        if args.command == "hide-img":
            payload  = get_payload(args.text, args.file)
            kw: dict = {}
            if getattr(args, "delta", None):      kw["delta"]      = args.delta
            if getattr(args, "ecc", None):         kw["ecc_symbols"] = args.ecc
            if getattr(args, "redundancy", None):  kw["redundancy"]  = args.redundancy
            stats = run_with_spinner("⚙️  جارٍ التضمين...",
                                     vault.hide_in_image, args.image, args.out, payload, args.password, **kw)
            console.print(f"\n[success]✅ الصورة جاهزة:[/] [bold white]{args.out}[/]")
            print_stats(stats)

        elif args.command == "recover-img":
            kw = {}
            if getattr(args, "ecc", None):         kw["ecc_symbols"] = args.ecc
            if getattr(args, "redundancy", None):  kw["redundancy"]  = args.redundancy
            data = run_with_spinner("🔓  جارٍ الاستخراج...",
                                    vault.recover_from_image, args.image, args.password, **kw)
            handle_extracted(data, getattr(args, "out", None))

        elif args.command == "encode-vid":
            with open(args.file, "rb") as fh:
                payload = fh.read()
            kw = {}
            if getattr(args, "ecc", None):        kw["ecc_symbols"] = args.ecc
            if getattr(args, "block_size", None): kw["block_size"]  = args.block_size
            stats = run_with_spinner("🎬  جارٍ توليد الفيديو...",
                                     vault.file_to_video, args.out, payload, args.password, **kw)
            console.print(f"\n[success]✅ الفيديو جاهز:[/] [bold white]{args.out}[/]")
            print_stats(stats)

        elif args.command == "decode-vid":
            kw = {}
            if getattr(args, "ecc", None):        kw["ecc_symbols"] = args.ecc
            if getattr(args, "block_size", None): kw["block_size"]  = args.block_size
            data = run_with_spinner("🎬  جارٍ استرجاع الملف...",
                                    vault.video_to_file, args.video, args.password, **kw)
            with open(args.out, "wb") as fh:
                fh.write(data)
            console.print(
                f"\n[success]✅ تم حفظ الملف:[/] [bold white]{args.out}[/]  "
                f"[dim]({len(data):,} بايت)[/]"
            )

        elif args.command == "encode-aud":
            payload = get_payload(args.text, args.file)
            kw = {}
            if getattr(args, "ecc", None): kw["ecc_symbols"] = args.ecc
            stats = run_with_spinner("🎵  جارٍ توليد الصوت...",
                                     vault.data_to_audio, args.out, payload, args.password, **kw)
            console.print(f"\n[success]✅ الصوت جاهز:[/] [bold white]{args.out}[/]")
            print_stats(stats)

        elif args.command == "decode-aud":
            kw = {}
            if getattr(args, "ecc", None): kw["ecc_symbols"] = args.ecc
            data = run_with_spinner("🎵  جارٍ تحليل الصوت...",
                                    vault.audio_to_data, args.media, args.password, **kw)
            handle_extracted(data, getattr(args, "out", None))

    except FileNotFoundError as exc:
        console.print(f"\n[error]❌ الملف غير موجود:[/] {escape(str(exc))}")
        sys.exit(1)
    except NotImplementedError as exc:
        console.print(f"\n[error]❌ غير مدعوم:[/] {escape(str(exc))}")
        sys.exit(1)
    except Exception as exc:
        console.print(f"\n[error]❌ خطأ:[/] {escape(str(exc))}")
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
#  نقطة الدخول
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    if len(sys.argv) == 1:
        # لا توجد معطيات → وضع تفاعلي
        try:
            interactive_mode()
        except KeyboardInterrupt:
            console.print("\n\n[warning]⚠️  تم الإيقاف بواسطة المستخدم.[/]")
        return

    parser = _build_parser()
    args   = parser.parse_args()
    cli_mode(args)


if __name__ == "__main__":
    main()
