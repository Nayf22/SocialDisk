#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SocialDisk CLI v2.0 — Multi-Platform Steganography Suite
واجهة سطر الأوامر الجميلة وثنائية اللغة (عربي / English)

Modes:
  1. Interactive : python cli.py           (No arguments → full interactive menu)
  2. Command line: python cli.py <command> (Scripting & automation)

Commands:
  hide-img     — Hide text/file inside an image (DCT)
  recover-img  — Extract data from an image
  encode-vid   — Encode a file into a video (HyperGrid)
  decode-vid   — Extract a file from a video
  encode-aud   — Encode data into an audio file (Acoustic FSK)
  decode-aud   — Extract data from audio/video
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

from socialdisk.i18n import (
    get_available_languages,
    get_language,
    get_stat_label,
    init_language,
    is_first_run,
    parse_error_details,
    set_language,
    t,
)

# ══════════════════════════════════════════════════════════════════════════
#  Theme & Console Setup
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

# ══════════════════════════════════════════════════════════════════════════
#  Bidi-Safe Prompt (RTL/LTR Cursor & Layout Alignment)
# ══════════════════════════════════════════════════════════════════════════

class SocialPrompt(Prompt):
    """Bidi-safe Prompt that locks line base direction to LTR using Unicode markers.
    
    Prevents terminal cursor jumping and input characters appearing on the opposite side
    when typing in Arabic or mixed LTR/RTL modes on Windows PowerShell / Terminal.
    """
    prompt_suffix = "\u200e: "

    def make_prompt(self, default) -> Text:
        prompt = super().make_prompt(default)
        wrapped = Text("\u200e")
        wrapped.append(prompt)
        return wrapped

Prompt = SocialPrompt

VERSION = "2.0.0"

# ══════════════════════════════════════════════════════════════════════════
#  ASCII Art Banner (Spells: SOCIALDISK)
# ══════════════════════════════════════════════════════════════════════════

BANNER_LINES = [
    r" ███████╗ ██████╗  ██████╗██╗ █████╗ ██╗     ██████╗ ██╗███████╗██╗  ██╗",
    r" ██╔════╝██╔═══██╗██╔════╝██║██╔══██╗██║     ██╔══██╗██║██╔════╝██║ ██╔╝",
    r" ███████╗██║   ██║██║     ██║███████║██║     ██║  ██║██║███████╗█████╔╝ ",
    r" ╚════██║██║   ██║██║     ██║██╔══██║██║     ██║  ██║██║╚════██║██╔═██╗ ",
    r" ███████║╚██████╔╝╚██████╗██║██║  ██║███████╗██████╔╝██║███████║██║  ██╗",
    r" ╚══════╝ ╚═════╝  ╚═════╝╚═╝╚═╝  ╚═╝╚══════╝╚═════╝ ╚═╝╚══════╝╚═╝  ╚═╝",
]

BANNER_COLORS = ["bold cyan", "bold cyan", "bold blue", "bold blue", "bold magenta", "bold magenta"]


def print_banner(clear: bool = False) -> None:
    """Print the SocialDisk banner."""
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
                (t("app_sub"), "bold white"),
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
#  Language Selection & Switching
# ══════════════════════════════════════════════════════════════════════════

def check_first_run_language() -> None:
    """Prompt the user on first launch to select display language."""
    if is_first_run():
        console.print()
        console.print(
            Panel(
                "[bold cyan]🌍 الرجاء اختيار لغة العرض / Please select display language:[/]\n\n"
                "   [bold yellow]1.[/]  [bold white]العربية (Arabic)[/]\n"
                "   [bold yellow]2.[/]  [bold white]English (الإنجليزية)[/]",
                title="[bold yellow]🌐 Language Selection / اختيار اللغة[/]",
                border_style="cyan",
                padding=(1, 3),
            )
        )
        console.print()
        choice = Prompt.ask(
            "[bold cyan]اختر / Select (1/2)[/]",
            choices=["1", "2"],
            default="1",
            console=console,
        )
        chosen_lang = "ar" if choice == "1" else "en"
        set_language(chosen_lang, persist=True)
        console.print(f"\n[success]✅ {t('lang_switched_success')}[/]\n")


def flow_change_language() -> None:
    """Allow switching language anytime during interactive mode."""
    console.print()
    console.print(Rule(f"[bold cyan]{t('lang_change_title')}[/]", style="blue"))
    console.print()
    console.print("   [bold yellow]1.[/]  [bold white]العربية (Arabic)[/]")
    console.print("   [bold yellow]2.[/]  [bold white]English (الإنجليزية)[/]")
    console.print(f"   [bold yellow]0.[/]  [bold red]{t('btn_back')}[/]")
    console.print()
    cur = "1" if get_language() == "ar" else "2"
    choice = Prompt.ask(
        f"[bold cyan]{t('lang_prompt_input')} {t('prompt_back_hint')}[/]",
        default=cur,
        console=console,
    )
    if choice.strip() in ("0", "b", "back", "q"):
        console.print(f"\n[dim]{t('op_cancelled')}[/]")
        return
    new_lang = "en" if choice.strip() == "2" else "ar"
    set_language(new_lang, persist=True)
    console.print(f"\n[success]✅ {t('lang_switched_success')}[/]")


# ══════════════════════════════════════════════════════════════════════════
#  Platform Table Display
# ══════════════════════════════════════════════════════════════════════════

def print_platform_table() -> None:
    """Display supported social platforms."""
    from socialdisk.platforms import list_platforms

    table = Table(
        title=t("tbl_platforms_title"),
        title_style="bold cyan",
        border_style="blue",
        header_style="bold white",
    )
    table.add_column(t("tbl_col_num"), justify="center", width=4)
    table.add_column(t("tbl_col_platform"), style="bold white", min_width=18)
    table.add_column(t("tbl_col_images"), justify="center", width=8)
    table.add_column(t("tbl_col_video"), justify="center", width=8)
    table.add_column(t("tbl_col_audio"), justify="center", width=8)
    table.add_column(t("tbl_col_jpeg_q"), justify="center", width=12)
    table.add_column(t("tbl_col_delta"), justify="center", width=10)
    table.add_column(t("tbl_col_desc"), style="dim", min_width=28)

    for i, p in enumerate(list_platforms(), 1):
        jpeg_q = str(p.image.jpeg_attack_quality) + "%" if p.image else "—"
        delta = str(p.image.delta) if p.image else "—"
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
#  Spinner Runner
# ══════════════════════════════════════════════════════════════════════════

def run_with_spinner(label: str, func, *args, **kwargs):
    """Run a callable inside a spinner."""
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
#  Statistics Display
# ══════════════════════════════════════════════════════════════════════════

def print_stats(stats: dict, title: Optional[str] = None) -> None:
    """Print operation statistics in a clean table."""
    table_title = title or t("stat_table_title")
    table = Table(
        title=table_title,
        title_style="bold green",
        border_style="green",
        show_header=False,
        expand=False,
        padding=(0, 2),
    )
    table.add_column(t("stat_table_param"), style="stat_key", min_width=30)
    table.add_column(t("stat_table_val"), style="stat_val")

    bytes_sfx = t("bytes_suffix")
    for key, val in stats.items():
        label = get_stat_label(key)
        if isinstance(val, float):
            display = f"{val:.2f}"
        elif isinstance(val, int) and "bytes" in key.lower():
            if val >= 1024 * 1024:
                display = f"{val:,} {bytes_sfx}  ({val / 1024 / 1024:.2f} MB)"
            elif val >= 1024:
                display = f"{val:,} {bytes_sfx}  ({val / 1024:.1f} KB)"
            else:
                display = f"{val:,} {bytes_sfx}"
        else:
            display = str(val)
        table.add_row(label, display)

    console.print()
    console.print(table)


# ══════════════════════════════════════════════════════════════════════════
#  Extracted Data Handler
# ══════════════════════════════════════════════════════════════════════════

def detect_file_extension(data: bytes) -> str:
    """Guess file extension from header magic bytes."""
    if data.startswith(b"PK\x03\x04") or data.startswith(b"PK\x05\x06"):
        return ".zip"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if data.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if data.startswith(b"%PDF"):
        return ".pdf"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return ".gif"
    if data.startswith(b"7z\xbc\xaf\x27\x1c"):
        return ".7z"
    if data.startswith(b"\x1f\x8b"):
        return ".tar.gz"
    if data.startswith(b"Rar!\x1a\x07"):
        return ".rar"
    if any(data.startswith(sig) for sig in [b"\x00\x00\x00 ftyp", b"\x00\x00\x00\x18ftyp", b"\x00\x00\x00\x14ftyp"]):
        return ".mp4"
    if data.startswith(b"RIFF") and b"WAVE" in data[:12]:
        return ".wav"
    try:
        data[:1024].decode("utf-8")
        return ".txt"
    except UnicodeDecodeError:
        return ".bin"


def handle_extracted(data: bytes, out_path: Optional[str]) -> None:
    """Save or print extracted payload."""
    bytes_sfx = t("bytes_suffix")
    if out_path:
        save_path = out_path.strip()
        if not os.path.splitext(save_path)[1]:
            ext = detect_file_extension(data)
            save_path += ext
            console.print(f"[dim]💡 {t('auto_detected_ext', ext=ext)} -> [bold white]{save_path}[/][/]")
        with open(save_path, "wb") as f:
            f.write(data)
        console.print(
            f"\n[success]✅ {t('extracted_data_saved')}[/] [bold white]{save_path}[/]  "
            f"[dim]({len(data):,} {bytes_sfx})[/]"
        )
    else:
        try:
            text = data.decode("utf-8")
            console.print()
            console.print(
                Panel(
                    f"[bold white]{escape(text)}[/]",
                    title=f"[bold green]{t('extracted_data_title')}[/]",
                    border_style="green",
                    padding=(1, 3),
                )
            )
        except UnicodeDecodeError:
            console.print(
                f"\n[warning]⚠️  {t('extracted_binary_warning', size=len(data))}[/]"
            )


def get_payload(text_arg: Optional[str], file_arg: Optional[str]) -> bytes:
    """Convert CLI text or file arguments to bytes."""
    if text_arg:
        return text_arg.encode("utf-8")
    if file_arg:
        with open(file_arg, "rb") as f:
            return f.read()
    raise ValueError(t("payload_required_err"))


# ══════════════════════════════════════════════════════════════════════════
#  Interactive Mode
# ══════════════════════════════════════════════════════════════════════════

def get_optimal_grid_columns() -> int:
    """حساب عدد الأعمدة تلقائياً بحسب عرض النافذة الحالي."""
    try:
        import shutil
        width = shutil.get_terminal_size((90, 25)).columns
    except Exception:
        width = 90

    if width >= 125:
        return 4
    elif width >= 90:
        return 3
    elif width >= 58:
        return 2
    else:
        return 1


def interactive_select_platform() -> Optional[str]:
    """Select platform via responsive cards with dynamic resize and back options."""
    from socialdisk.platforms import list_platforms

    platforms = list_platforms()

    while True:
        cols = get_optimal_grid_columns()
        console.print()
        console.print(Rule(f"[bold cyan]{t('platform_select_title')}[/]", style="blue"))
        console.print()

        grid = Table.grid(expand=True, padding=(0, 1))
        for _ in range(cols):
            grid.add_column(ratio=1)

        cards = []
        for i, p in enumerate(platforms, 1):
            caps = []
            if p.image: caps.append(t("cap_photos"))
            if p.video: caps.append(t("cap_video"))
            if p.audio: caps.append(t("cap_audio"))
            sep = "   " if cols <= 2 else "  "
            cap_str = sep.join(caps) if caps else "—"
            card_txt = Text.assemble(
                (f"{i}. ", "bold yellow"),
                (f"{p.emoji} ", ""),
                (f"{p.name}\n", "bold white"),
                (cap_str, "cyan"),
            )
            card_txt.justify = "center"
            cards.append(Panel(card_txt, border_style="blue", height=4, padding=(0, 0)))

        for i in range(0, len(cards), cols):
            row = cards[i : i + cols]
            while len(row) < cols:
                row.append(Text(""))
            grid.add_row(*row)

        console.print(grid)

        console.print()
        action_grid = Table.grid(expand=True, padding=(0, 1))
        action_grid.add_column(ratio=1)
        action_grid.add_column(ratio=1)
        p_back = Panel(
            Text.from_markup(f"[bold red]0.[/]  [bold white]{t('btn_back_to_menu')}[/]", justify="center"),
            border_style="red",
            height=3,
            padding=(0, 0),
        )
        p_refresh = Panel(
            Text.from_markup(f"[bold cyan]r.[/]  [bold white]🔄  {t('btn_refresh')}[/]", justify="center"),
            border_style="blue",
            height=3,
            padding=(0, 0),
        )
        action_grid.add_row(p_back, p_refresh)
        console.print(action_grid)
        console.print()
        choice = Prompt.ask(
            f"[bold cyan]{t('platform_prompt_idx')} {t('prompt_back_hint')}[/]",
            default="1",
            console=console,
        )
        choice_clean = choice.strip().lower()
        if choice_clean in ("r", "refresh"):
            print_banner(clear=True)
            continue

        if choice_clean in ("0", "b", "back", "q", "exit"):
            return None
        try:
            idx = int(choice_clean)
            if 1 <= idx <= len(platforms):
                chosen = platforms[idx - 1]
                console.print(
                    f"\n[success]✅ {t('platform_chosen')}[/] [platform]{chosen.emoji}  {chosen.name}[/]\n"
                )
                return chosen.key
        except ValueError:
            pass
        console.print(f"[warning]{t('platform_invalid')}[/]")
        return "instagram"


def interactive_select_operation(profile) -> Optional[str]:
    """Select operation based on platform profile with dynamic 1..N numbering and back option."""
    raw_ops: list[tuple[str, str]] = []
    if profile.image:
        raw_ops.append((t("op_image_embed"),   "image_embed"))
        raw_ops.append((t("op_image_extract"), "image_extract"))
    if profile.video:
        raw_ops.append((t("op_video_embed"),   "video_embed"))
        raw_ops.append((t("op_video_extract"), "video_extract"))
    if profile.audio:
        raw_ops.append((t("op_audio_embed"),   "audio_embed"))
        raw_ops.append((t("op_audio_extract"), "audio_extract"))

    # Dynamically number available operations from 1 to N
    options: list[tuple[str, str, str]] = [
        (str(i), label, key) for i, (label, key) in enumerate(raw_ops, 1)
    ]

    console.print(Rule(f"[bold cyan]{t('op_select_title')}[/]", style="blue"))
    console.print()
    for num, label, _ in options:
        console.print(f"   [bold yellow]{num}.[/]  {label}")
    console.print()
    console.print(
        Panel(
            Text.from_markup(f"[bold red]0.[/]  [bold white]{t('btn_back_to_platform')}[/]", justify="center"),
            border_style="red",
            height=3,
            padding=(0, 0),
        )
    )
    console.print()

    choice = Prompt.ask(
        f"[bold cyan]{t('op_prompt_idx')} {t('prompt_back_hint')}[/]",
        default="1",
        console=console,
    )
    choice_clean = choice.strip().lower()
    if choice_clean in ("0", "b", "back", "q"):
        return None
    for num, _, key in options:
        if choice_clean == num:
            return key
    return options[0][2]


# ─── Embedding & Extracting Flows ─────────────────────────────────────────

def _prompt_payload() -> Optional[bytes]:
    """Prompt user for secret data source (supports back/cancel)."""
    console.print(f"\n[bold white]{t('payload_source_title')}[/]")
    console.print(f"   [yellow]1.[/]  {t('payload_source_text')}")
    console.print(f"   [yellow]2.[/]  {t('payload_source_file')}")
    console.print(f"   [yellow]0.[/]  [bold red]{t('btn_back')}[/]")
    src = Prompt.ask(f"[bold cyan]{t('payload_source_prompt')}[/]", default="1", console=console)
    src_clean = src.strip().lower()
    if src_clean in ("0", "b", "back", "q"):
        return None
    if src_clean == "2":
        fp = Prompt.ask(f"[bold cyan]{t('payload_file_prompt')} {t('prompt_back_hint')}[/]", console=console)
        if not fp.strip() or fp.strip().lower() in ("0", "b", "back"):
            return None
        with open(fp.strip(), "rb") as f:
            data = f.read()
        console.print(f"[dim]{t('payload_file_read_ok', size=len(data))}[/]")
        return data
    txt = Prompt.ask(f"[bold cyan]{t('payload_text_prompt')} {t('prompt_back_hint')}[/]", console=console)
    if not txt.strip() or txt.strip().lower() in ("0", "b", "back"):
        return None
    return txt.encode("utf-8")


def print_user_error(exc: Exception) -> None:
    """عرض رسالة الخطأ للمستخدم بشكل أنيق وواضح مع حل مقترح وتفاصيل تقنية."""
    msg, hint, raw = parse_error_details(exc)
    console.print()
    content = Text.assemble(
        ("❌  ", "bold red"),
        (f"{msg}\n\n", "bold red"),
        (f"{hint}", "bold yellow"),
    )
    if raw and raw != msg:
        content.append(f"\n\n🔍 {raw}", style="dim")

    console.print(
        Panel(
            content,
            title=f"[bold red]{t('err_panel_title')}[/]",
            border_style="red",
            padding=(1, 2),
        )
    )


def flow_image_embed(vault) -> None:
    cover = Prompt.ask(f"[bold cyan]{t('prompt_cover_img')} {t('prompt_back_hint')}[/]", console=console)
    if not cover.strip() or cover.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    output = Prompt.ask(f"[bold cyan]{t('prompt_output_img')} {t('prompt_back_hint')}[/]", console=console)
    if not output.strip() or output.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    payload = _prompt_payload()
    if payload is None:
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    password = Prompt.ask(f"[bold cyan]{t('prompt_password')} {t('prompt_back_hint')}[/]", password=True, console=console)
    if not password or password.lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    console.print()
    try:
        stats = run_with_spinner(t("spinner_image_embed"), vault.hide_in_image,
                                 cover.strip(), output.strip(), payload, password)
        console.print(f"\n[success]✅ {t('image_embed_ready')}[/] [bold white]{output.strip()}[/]")
        print_stats(stats, t("title_stats_image_embed"))
    except Exception as e:
        print_user_error(e)


def flow_image_extract(vault) -> None:
    img = Prompt.ask(f"[bold cyan]{t('prompt_image_extract')} {t('prompt_back_hint')}[/]", console=console)
    if not img.strip() or img.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    password = Prompt.ask(f"[bold cyan]{t('prompt_password')} {t('prompt_back_hint')}[/]", password=True, console=console)
    if not password or password.lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    out = Prompt.ask(f"[bold cyan]{t('prompt_save_or_display')}[/]", default="", console=console)
    console.print()
    try:
        data = run_with_spinner(t("spinner_image_extract"), vault.recover_from_image, img.strip(), password)
        handle_extracted(data, out.strip() or None)
    except Exception as e:
        print_user_error(e)


def flow_video_embed(vault) -> None:
    fp = Prompt.ask(f"[bold cyan]{t('prompt_video_source_file')} {t('prompt_back_hint')}[/]", console=console)
    if not fp.strip() or fp.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    output = Prompt.ask(f"[bold cyan]{t('prompt_video_output')} {t('prompt_back_hint')}[/]", console=console)
    if not output.strip() or output.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    password = Prompt.ask(f"[bold cyan]{t('prompt_password')} {t('prompt_back_hint')}[/]", password=True, console=console)
    if not password or password.lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    with open(fp.strip(), "rb") as f:
        payload = f.read()
    console.print(f"[dim]{t('video_file_size', size=len(payload))}[/]\n")
    try:
        stats = run_with_spinner(t("spinner_video_embed"), vault.file_to_video,
                                 output.strip(), payload, password)
        console.print(f"\n[success]✅ {t('video_embed_ready')}[/] [bold white]{output.strip()}[/]")
        print_stats(stats, t("title_stats_video"))
    except Exception as e:
        print_user_error(e)


def flow_video_extract(vault) -> None:
    vid = Prompt.ask(f"[bold cyan]{t('prompt_video_extract')} {t('prompt_back_hint')}[/]", console=console)
    if not vid.strip() or vid.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    out = Prompt.ask(f"[bold cyan]{t('prompt_video_out_file')} {t('prompt_back_hint')}[/]", console=console)
    if not out.strip() or out.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    password = Prompt.ask(f"[bold cyan]{t('prompt_password')} {t('prompt_back_hint')}[/]", password=True, console=console)
    if not password or password.lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    console.print()
    try:
        data = run_with_spinner(t("spinner_video_extract"), vault.video_to_file, vid.strip(), password)
        save_path = out.strip()
        if not os.path.splitext(save_path)[1]:
            ext = detect_file_extension(data)
            save_path += ext
            console.print(f"[dim]💡 {t('auto_detected_ext', ext=ext)} -> [bold white]{save_path}[/][/]")
        with open(save_path, "wb") as f:
            f.write(data)
        bytes_sfx = t("bytes_suffix")
        console.print(
            f"\n[success]✅ {t('video_recovered_ok')}[/] [bold white]{save_path}[/]"
            f" [dim]({len(data):,} {bytes_sfx})[/]"
        )
    except Exception as e:
        print_user_error(e)


def flow_audio_embed(vault) -> None:
    output = Prompt.ask(f"[bold cyan]{t('prompt_audio_output')} {t('prompt_back_hint')}[/]", console=console)
    if not output.strip() or output.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    payload = _prompt_payload()
    if payload is None:
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    password = Prompt.ask(f"[bold cyan]{t('prompt_password')} {t('prompt_back_hint')}[/]", password=True, console=console)
    if not password or password.lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    console.print()
    try:
        stats = run_with_spinner(t("spinner_audio_embed"), vault.data_to_audio,
                                 output.strip(), payload, password)
        console.print(f"\n[success]✅ {t('audio_embed_ready')}[/] [bold white]{output.strip()}[/]")
        print_stats(stats, t("title_stats_audio"))
    except Exception as e:
        print_user_error(e)


def flow_audio_extract(vault) -> None:
    media = Prompt.ask(f"[bold cyan]{t('prompt_audio_extract')} {t('prompt_back_hint')}[/]", console=console)
    if not media.strip() or media.strip().lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    password = Prompt.ask(f"[bold cyan]{t('prompt_password')} {t('prompt_back_hint')}[/]", password=True, console=console)
    if not password or password.lower() in ("0", "b", "back"):
        console.print(f"\n[warning]{t('op_cancelled')}[/]")
        return
    out = Prompt.ask(f"[bold cyan]{t('prompt_save_or_display')}[/]", default="", console=console)
    console.print()
    try:
        data = run_with_spinner(t("spinner_audio_extract"), vault.audio_to_data, media.strip(), password)
        handle_extracted(data, out.strip() or None)
    except Exception as e:
        print_user_error(e)


# ─── Automated Self-Test ──────────────────────────────────────────────────

def run_self_test() -> None:
    """Run automated self-test of all 3 engines."""
    import cv2
    from socialdisk.engines.image import DCTImageEngine
    from socialdisk.engines.video import HyperGridVideoEngine
    from socialdisk.engines.audio import AcousticFSKEngine

    console.print()
    console.print(Panel(
        f"[bold white]{t('test_panel_desc')}[/]",
        title=f"[bold cyan]{t('test_panel_title')}[/]",
        border_style="cyan",
        padding=(0, 2),
    ))

    password = "socialdisk_AutoTest_2026"
    sample   = "SocialDisk v2.0 Multi-Engine Self-Test.".encode("utf-8")
    results: list[tuple[str, bool, str]] = []

    with Progress(
        SpinnerColumn(style="bold cyan", spinner_name="dots"),
        TextColumn("[bold white]{task.description}"),
        TimeElapsedColumn(),
        console=console,
    ) as prog:
        # ── Test 1: DCT Image
        t1 = prog.add_task(f"  {t('test_t1_label')}", total=None)
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

            # Simulate JPEG q=70
            attacked = cv2.imread(stego_p)
            cv2.imwrite(attack_p, attacked, [int(cv2.IMWRITE_JPEG_QUALITY), 70])

            recovered_i = DCTImageEngine.extract(attack_p, password)
            ok_i = recovered_i == sample
            detail = f"q=70  |  cap={stats_i.get('capacity_used_percent', '?')}%"
            results.append(("📸  DCT Image (q=70)", ok_i, detail))
            for p_ in [cover_p, stego_p, attack_p]:
                if os.path.exists(p_): os.remove(p_)
        except Exception as exc:
            results.append(("📸  DCT Image", False, str(exc)[:80]))
        prog.update(t1, completed=1, total=1)

        # ── Test 2: HyperGrid Video
        t2 = prog.add_task(f"  {t('test_t2_label')}", total=None)
        try:
            large = os.urandom(10 * 1024)
            with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tf:
                vid_p = tf.name
            stats_v = HyperGridVideoEngine.encode(vid_p, large, password)
            recovered_v = HyperGridVideoEngine.decode(vid_p, password)
            ok_v = (
                hashlib.sha256(large).digest() == hashlib.sha256(recovered_v).digest()
            )
            detail = f"frames={stats_v.get('total_frames', '?')}  |  {stats_v.get('resolution', '?')}"
            results.append(("🎬  HyperGrid Video", ok_v, detail))
            if os.path.exists(vid_p): os.remove(vid_p)
        except Exception as exc:
            results.append(("🎬  HyperGrid Video", False, str(exc)[:80]))
        prog.update(t2, completed=1, total=1)

        # ── Test 3: Acoustic FSK
        t3 = prog.add_task(f"  {t('test_t3_label')}", total=None)
        try:
            fd, wav_p = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            stats_a = AcousticFSKEngine.encode_wav(wav_p, sample, password)
            recovered_a = AcousticFSKEngine.decode_media(wav_p, password)
            ok_a = recovered_a == sample
            detail = f"dur={stats_a.get('duration_sec', '?')}s  |  baud={stats_a.get('baud_rate', '?')}"
            results.append(("🎵  Acoustic FSK", ok_a, detail))
            if os.path.exists(wav_p): os.remove(wav_p)
        except Exception as exc:
            results.append(("🎵  Acoustic FSK", False, str(exc)[:80]))
        prog.update(t3, completed=1, total=1)

    # Results Table
    res_table = Table(
        title=t("test_results_title"),
        title_style="bold cyan",
        border_style="blue",
        header_style="bold white",
    )
    res_table.add_column(t("test_col_engine"),   style="bold white", min_width=28)
    res_table.add_column(t("test_col_status"),   justify="center",   width=12)
    res_table.add_column(t("test_col_details"),  style="dim",        min_width=35)

    all_ok = True
    pass_txt = t("test_status_success")
    fail_txt = t("test_status_fail")
    for name, ok, detail in results:
        status = f"[success]✅ {pass_txt}[/]" if ok else f"[error]❌ {fail_txt}[/]"
        res_table.add_row(name, status, detail)
        if not ok:
            all_ok = False

    console.print()
    console.print(res_table)
    console.print()

    if all_ok:
        console.print(Panel(
            f"[bold green]{t('test_all_ok')}[/]",
            border_style="green",
            padding=(0, 2),
        ))
    else:
        console.print(Panel(
            f"[bold red]{t('test_some_failed')}[/]",
            border_style="red",
            padding=(0, 2),
        ))


# ─── Help Display ─────────────────────────────────────────────────────────

def show_help() -> None:
    """Display comprehensive help in active language."""
    console.print()
    console.print(Panel(
        f"[bold cyan]SocialDisk v{VERSION}[/] — {t('help_desc')}\n\n"
        f"[bold white]{t('help_interactive_title')}[/]\n"
        "  [cyan]python cli.py[/]\n\n"
        f"[bold white]{t('help_img_title')}[/]\n"
        "  [cyan]python cli.py hide-img    -i cover.jpg -o out.jpg -p pass -t \"secret\" --platform instagram[/]\n"
        "  [cyan]python cli.py recover-img -i img.jpg   -p pass              --platform instagram[/]\n\n"
        f"[bold white]{t('help_vid_title')}[/]\n"
        "  [cyan]python cli.py encode-vid -f secret.zip -o reel.mp4 -p pass --platform tiktok[/]\n"
        "  [cyan]python cli.py decode-vid -v reel.mp4   -o out.zip  -p pass --platform tiktok[/]\n\n"
        f"[bold white]{t('help_aud_title')}[/]\n"
        "  [cyan]python cli.py encode-aud -t \"message\" -o audio.wav -p pass --platform whatsapp[/]\n"
        "  [cyan]python cli.py decode-aud -m audio.wav  -p pass              --platform whatsapp[/]\n\n"
        f"[bold white]{t('help_common_title')}[/]\n"
        "  [cyan]--lang [ar|en][/]  Display language / لغة العرض\n"
        "  [cyan]--platform -P[/]   Platform (instagram, whatsapp, twitter, tiktok, youtube, ...)\n"
        "  [cyan]--platforms[/]      List all supported platforms\n"
        "  [cyan]--ecc N[/]          Override Reed-Solomon symbols\n"
        "  [cyan]--delta F[/]        Override DCT signal strength\n\n"
        f"[bold white]{t('help_tech_title')}[/]\n"
        "  🔐 [green]AES-256-GCM[/]        — Military-grade authenticated encryption\n"
        "  🛡️  [green]Reed-Solomon ECC[/]   — Multi-symbol error correction\n"
        "  🔀 [green]Interleaving[/]        — Burst error resistance\n"
        "  📐 [green]Differential DCT[/]    — Frequency-domain imperceptible image stego\n"
        "  🎬 [green]HyperGrid Video[/]     — Resilient visual matrix for large payloads\n"
        "  🎵 [green]Acoustic FSK+FFT[/]    — Acoustic modem surviving AAC/Opus compression",
        title=f"[bold cyan]{t('help_title')}[/]",
        border_style="cyan",
        padding=(1, 2),
    ))


# ─── Interactive Main Menu ────────────────────────────────────────────────

def interactive_mode() -> None:
    """Full interactive menu loop with instant language switching."""
    from socialdisk.api import SocialVault

    check_first_run_language()
    print_banner(clear=True)

    while True:
        console.print(Rule(f"[bold cyan]{t('main_menu_title')}[/]", style="blue"))
        console.print()

        menu = [
            ("1", t("menu_embed"),     "embed"),
            ("2", t("menu_extract"),   "extract"),
            ("3", t("menu_platforms"), "platforms"),
            ("4", t("menu_test"),      "test"),
            ("5", t("menu_help"),      "help"),
            ("6", t("menu_lang"),      "lang"),
            ("0", t("menu_exit"),      "exit"),
        ]
        for num, label, _ in menu:
            clr = "bold red" if num == "0" else "bold white"
            console.print(f"   [bold yellow]{num}.[/]   [{clr}]{label}[/]")

        console.print()
        choice = Prompt.ask(f"[bold cyan]{t('prompt_your_choice')}[/]", default="1", console=console)
        console.print()

        if choice == "0" or choice.lower() in ("exit", "quit", "q"):
            console.print(Panel(
                f"[bold cyan]{t('thanks_for_using')}[/]",
                border_style="cyan", padding=(0, 3),
            ))
            break

        elif choice == "1":
            while True:
                platform_key = interactive_select_platform()
                if not platform_key:
                    break
                vault = SocialVault(platform_key)
                op    = interactive_select_operation(vault.profile)
                if not op:
                    continue
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
                Prompt.ask(f"[dim]{t('press_enter_to_return')}[/]", show_default=False, default="", console=console)
                break
            print_banner(clear=True)

        elif choice == "2":
            while True:
                platform_key = interactive_select_platform()
                if not platform_key:
                    break
                vault = SocialVault(platform_key)
                op    = interactive_select_operation(vault.profile)
                if not op:
                    continue
                if not op.endswith("_extract"):
                    op = op.replace("_embed", "_extract")
                console.print()
                dispatch = {
                    "image_extract": flow_image_extract,
                    "video_extract": flow_video_extract,
                    "audio_extract": flow_audio_extract,
                }
                dispatch.get(op, lambda v: None)(vault)
                console.print()
                Prompt.ask(f"[dim]{t('press_enter_to_back')}[/]", show_default=False, default="", console=console)
                break
            print_banner(clear=True)

        elif choice == "3":
            print_platform_table()
            console.print()
            Prompt.ask(f"[dim]{t('press_enter_to_back')}[/]", show_default=False, default="", console=console)
            print_banner(clear=True)

        elif choice == "4":
            run_self_test()
            console.print()
            Prompt.ask(f"[dim]{t('press_enter_to_back')}[/]", show_default=False, default="", console=console)
            print_banner(clear=True)

        elif choice == "5":
            show_help()
            console.print()
            Prompt.ask(f"[dim]{t('press_enter_to_back')}[/]", show_default=False, default="", console=console)
            print_banner(clear=True)

        elif choice == "6" or choice.lower() in ("lang", "language", "l"):
            flow_change_language()
            console.print()
            Prompt.ask(f"[dim]{t('press_enter_to_return')}[/]", show_default=False, default="", console=console)
            print_banner(clear=True)

        else:
            console.print(f"[warning]{t('invalid_choice')}[/]\n")


# ══════════════════════════════════════════════════════════════════════════
#  Command Line Mode (CLI Args)
# ══════════════════════════════════════════════════════════════════════════

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description=f"🛡️ SocialDisk v{VERSION} — Multi-Platform Steganography Suite",
        formatter_class=argparse.RawTextHelpFormatter,
        add_help=True,
    )
    parser.add_argument(
        "--lang", choices=["ar", "en"], default=None,
        help="لغة العرض / Display language (ar = Arabic, en = English)",
    )
    parser.add_argument(
        "--platform", "-P", default="instagram", metavar="PLATFORM",
        help="Target platform (instagram, whatsapp, twitter, tiktok, youtube, ...)\n"
             "Default: instagram",
    )
    parser.add_argument(
        "--platforms", action="store_true",
        help="List all supported platforms and exit",
    )

    sub = parser.add_subparsers(dest="command")

    # ── hide-img
    p_hi = sub.add_parser("hide-img", help="Hide text or file inside image (DCT)")
    p_hi.add_argument("-i", "--image",    required=True, help="Original cover image")
    p_hi.add_argument("-o", "--out",      required=True, help="Output stego image")
    p_hi.add_argument("-p", "--password", required=True, help="Encryption password")
    p_hi.add_argument("-t", "--text",     help="Secret text payload")
    p_hi.add_argument("-f", "--file",     help="Secret file payload path")
    p_hi.add_argument("--delta",    type=float, help="DCT strength override")
    p_hi.add_argument("--ecc",      type=int,   help="Reed-Solomon ECC symbols override")
    p_hi.add_argument("--redundancy", type=int, help="Spatial redundancy factor")

    # ── recover-img
    p_ri = sub.add_parser("recover-img", help="Recover hidden data from an image")
    p_ri.add_argument("-i", "--image",    required=True, help="Downloaded stego image")
    p_ri.add_argument("-p", "--password", required=True, help="Decryption password")
    p_ri.add_argument("-o", "--out",      help="Save path (blank = print text)")
    p_ri.add_argument("--ecc",      type=int, help="Reed-Solomon symbols")
    p_ri.add_argument("--redundancy", type=int, help="Redundancy factor")

    # ── encode-vid
    p_ev = sub.add_parser("encode-vid", help="Encode a file into a video (HyperGrid)")
    p_ev.add_argument("-f", "--file",     required=True, help="Source payload file")
    p_ev.add_argument("-o", "--out",      required=True, help="Output video path (.mp4)")
    p_ev.add_argument("-p", "--password", required=True, help="Encryption password")
    p_ev.add_argument("--ecc",        type=int, help="Reed-Solomon symbols")
    p_ev.add_argument("--block-size", type=int, help="Video block size (px)")

    # ── decode-vid
    p_dv = sub.add_parser("decode-vid", help="Extract file from a video")
    p_dv.add_argument("-v", "--video",    required=True, help="Downloaded video file")
    p_dv.add_argument("-o", "--out",      required=True, help="Recovered file output path")
    p_dv.add_argument("-p", "--password", required=True, help="Decryption password")
    p_dv.add_argument("--ecc",        type=int, help="Reed-Solomon symbols")
    p_dv.add_argument("--block-size", type=int, help="Video block size")

    # ── encode-aud
    p_ea = sub.add_parser("encode-aud", help="Encode data into audio WAV (Acoustic FSK)")
    p_ea.add_argument("-o", "--out",      required=True, help="Output WAV audio path")
    p_ea.add_argument("-p", "--password", required=True, help="Encryption password")
    p_ea.add_argument("-t", "--text",     help="Text to encode")
    p_ea.add_argument("-f", "--file",     help="File to encode")
    p_ea.add_argument("--ecc", type=int,  help="Reed-Solomon symbols")

    # ── decode-aud
    p_da = sub.add_parser("decode-aud", help="Extract data from audio/video")
    p_da.add_argument("-m", "--media",    required=True, help="Audio (.wav) or video file")
    p_da.add_argument("-p", "--password", required=True, help="Decryption password")
    p_da.add_argument("-o", "--out",      help="Save path (blank = print text)")
    p_da.add_argument("--ecc", type=int,  help="Reed-Solomon symbols")

    return parser


def cli_mode(args: argparse.Namespace) -> None:
    """Execute command-line invocation."""
    from socialdisk.api import SocialVault

    if args.lang:
        set_language(args.lang, persist=False)

    print_banner()

    if args.platforms:
        print_platform_table()
        return

    if not args.command:
        console.print(f"[warning]{t('cmd_no_command_warn')}[/]")
        return

    vault   = SocialVault(args.platform)
    profile = vault.profile

    console.print(
        Panel(
            Text.assemble(
                (f"{profile.emoji}  {profile.name}", "platform"),
                ("   │   Command: ", "dim"),
                (args.command, "bold white"),
            ),
            border_style="cyan",
            title="[bold cyan]SocialDisk[/]",
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
            stats = run_with_spinner(t("spinner_image_embed"),
                                     vault.hide_in_image, args.image, args.out, payload, args.password, **kw)
            console.print(f"\n[success]✅ {t('image_embed_ready')}[/] [bold white]{args.out}[/]")
            print_stats(stats)

        elif args.command == "recover-img":
            kw = {}
            if getattr(args, "ecc", None):         kw["ecc_symbols"] = args.ecc
            if getattr(args, "redundancy", None):  kw["redundancy"]  = args.redundancy
            data = run_with_spinner(t("spinner_image_extract"),
                                    vault.recover_from_image, args.image, args.password, **kw)
            handle_extracted(data, getattr(args, "out", None))

        elif args.command == "encode-vid":
            with open(args.file, "rb") as fh:
                payload = fh.read()
            kw = {}
            if getattr(args, "ecc", None):        kw["ecc_symbols"] = args.ecc
            if getattr(args, "block_size", None): kw["block_size"]  = args.block_size
            stats = run_with_spinner(t("spinner_video_embed"),
                                     vault.file_to_video, args.out, payload, args.password, **kw)
            console.print(f"\n[success]✅ {t('video_embed_ready')}[/] [bold white]{args.out}[/]")
            print_stats(stats)

        elif args.command == "decode-vid":
            kw = {}
            if getattr(args, "ecc", None):        kw["ecc_symbols"] = args.ecc
            if getattr(args, "block_size", None): kw["block_size"]  = args.block_size
            data = run_with_spinner(t("spinner_video_extract"),
                                    vault.video_to_file, args.video, args.password, **kw)
            with open(args.out, "wb") as fh:
                fh.write(data)
            bytes_sfx = t("bytes_suffix")
            console.print(
                f"\n[success]✅ {t('video_recovered_ok')}[/] [bold white]{args.out}[/]  "
                f"[dim]({len(data):,} {bytes_sfx})[/]"
            )

        elif args.command == "encode-aud":
            payload = get_payload(args.text, args.file)
            kw = {}
            if getattr(args, "ecc", None): kw["ecc_symbols"] = args.ecc
            stats = run_with_spinner(t("spinner_audio_embed"),
                                     vault.data_to_audio, args.out, payload, args.password, **kw)
            console.print(f"\n[success]✅ {t('audio_embed_ready')}[/] [bold white]{args.out}[/]")
            print_stats(stats)

        elif args.command == "decode-aud":
            kw = {}
            if getattr(args, "ecc", None): kw["ecc_symbols"] = args.ecc
            data = run_with_spinner(t("spinner_audio_extract"),
                                    vault.audio_to_data, args.media, args.password, **kw)
            handle_extracted(data, getattr(args, "out", None))

    except Exception as exc:
        print_user_error(exc)
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════
#  Main Entry Point
# ══════════════════════════════════════════════════════════════════════════

def main() -> None:
    # Check if a custom language is specified anywhere in CLI arguments
    for i, arg in enumerate(sys.argv):
        if arg == "--lang" and i + 1 < len(sys.argv):
            set_language(sys.argv[i + 1], persist=False)
            break

    if len(sys.argv) == 1:
        try:
            interactive_mode()
        except (KeyboardInterrupt, EOFError):
            console.print(f"\n\n[warning]{t('interrupted_by_user')}[/]")
        return

    parser = _build_parser()
    args   = parser.parse_args()
    cli_mode(args)


if __name__ == "__main__":
    main()
