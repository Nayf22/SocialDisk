"""
SocialDisk — English Language Dictionary (en)
English dictionary for SocialDisk texts
"""
from __future__ import annotations

STRINGS: dict[str, str] = {
    # ── General ──
    "app_name": "SocialDisk",
    "app_sub": "Multi-Platform Steganography Suite",
    "btn_back": "↩️  Back",
    "btn_back_to_menu": "↩️  Back to Main Menu",
    "btn_back_to_platform": "↩️  Back to Platform Selection",
    "btn_refresh": "Refresh display",
    "op_cancelled": "↩️  Operation cancelled, returning.",
    "prompt_back_hint": "[or 0 to go back]",
    "press_enter_to_return": "Press Enter to return to main menu",
    "press_enter_to_back": "Press Enter to return",
    "interrupted_by_user": "⚠️  Interrupted by user.",
    "thanks_for_using": "Thank you for using SocialDisk 🛡️",
    "invalid_choice": "Invalid choice.",
    "error_prefix": "Error:",
    "success_prefix": "Success:",
    "warning_prefix": "Warning:",
    "file_not_found": "File not found:",
    "not_supported": "Not supported:",

    # ── Language Selection ──
    "lang_prompt_title": "🌍 الرجاء اختيار لغة العرض / Please select display language:",
    "lang_option_ar": "العربية (Arabic)",
    "lang_option_en": "English (الإنجليزية)",
    "lang_prompt_input": "اختر اللغة / Select language (1-2)",
    "lang_switched_success": "Display language set to: English",
    "lang_change_title": "🌐  Change Display Language",

    # ── Main Menu ──
    "main_menu_title": "  Main Menu  ",
    "menu_embed": "🚀  Embed data / hide file",
    "menu_extract": "🔓  Extract hidden data",
    "menu_platforms": "🌐  Browse supported platforms",
    "menu_test": "🧪  Run automated self-test",
    "menu_help": "❓  Help & command usage",
    "menu_lang": "🌐  Change Language / تغيير اللغة",
    "menu_exit": "🚪  Exit",
    "prompt_your_choice": "Your choice",

    # ── Platform Selection ──
    "platform_select_title": "📱  Select Social Platform",
    "platform_prompt_idx": "Platform number",
    "platform_chosen": "Selected platform:",
    "platform_invalid": "Invalid number, Instagram selected by default.",
    "cap_photos": "📸Photos",
    "cap_video": "🎬Video",
    "cap_audio": "🎵Audio",

    # ── Platforms Table ──
    "tbl_platforms_title": "Supported Platforms in SocialDisk v2.0",
    "tbl_col_num": "#",
    "tbl_col_platform": "Platform",
    "tbl_col_images": "Photos",
    "tbl_col_video": "Video",
    "tbl_col_audio": "Audio",
    "tbl_col_jpeg_q": "JPEG Quality",
    "tbl_col_delta": "DCT Delta",
    "tbl_col_desc": "Description",

    # ── Operation Selection ──
    "op_select_title": "⚙️   Select Operation",
    "op_prompt_idx": "Operation number",
    "op_image_embed": "📸  Hide data inside image",
    "op_image_extract": "🔓  Extract data from image",
    "op_video_embed": "🎬  Encode file to video",
    "op_video_extract": "🎬  Extract file from video",
    "op_audio_embed": "🎵  Encode data to audio (WAV)",
    "op_audio_extract": "🎵  Extract data from audio",

    # ── Payload Source ──
    "payload_source_title": "Secret data source:",
    "payload_source_text": "Direct text",
    "payload_source_file": "File",
    "payload_source_prompt": "Select",
    "payload_file_prompt": "📂  File path",
    "payload_file_read_ok": "📦 File loaded: {size:,} bytes",
    "payload_text_prompt": "✏️   Secret text",
    "payload_required_err": "Must specify direct text (-t) or file (-f).",

    # ── Embed & Extract Flows ──
    "prompt_cover_img": "📂  Cover image path",
    "prompt_output_img": "💾  Output stego image path",
    "prompt_password": "🔑  Password",
    "spinner_image_embed": "⚙️  Embedding data in image...",
    "image_embed_ready": "Image ready:",
    "title_stats_image_embed": "📊  Image Embedding Statistics",

    "prompt_image_extract": "📂  Image path (downloaded from platform)",
    "prompt_save_or_display": "💾  Save path (Enter = display text)",
    "spinner_image_extract": "🔓  Extracting data from image...",

    "prompt_video_source_file": "📂  Source file to embed",
    "prompt_video_output": "💾  Output video path (.mp4)",
    "video_file_size": "📦 File size: {size:,} bytes",
    "spinner_video_embed": "🎬  Generating video...",
    "video_embed_ready": "Video ready:",
    "title_stats_video": "📊  Video Statistics",

    "prompt_video_extract": "📂  Video path (downloaded)",
    "prompt_video_out_file": "💾  Save path for extracted file with extension (e.g. secret.zip or data.pdf)",
    "auto_detected_ext": "Auto-detected file type: {ext}",
    "spinner_video_extract": "🎬  Recovering file from video...",
    "video_recovered_ok": "File successfully saved:",

    "prompt_audio_output": "💾  Output audio path (.wav)",
    "spinner_audio_embed": "🎵  Generating acoustic waveform...",
    "audio_embed_ready": "Audio ready:",
    "title_stats_audio": "📊  Audio File Statistics",

    "prompt_audio_extract": "📂  Audio/video file path",
    "spinner_audio_extract": "🎵  Analyzing audio waveform...",

    # ── Extracted Data ──
    "extracted_data_title": "🔓  Extracted Data",
    "extracted_data_saved": "Data successfully saved to:",
    "extracted_binary_warning": "Data is binary ({size:,} bytes).\nAdd [-o output_path] to save as a file.",

    # ── Statistics ──
    "stat_table_title": "📊  Operation Statistics",
    "stat_table_param": "Parameter",
    "stat_table_val": "Value",
    "bytes_suffix": "bytes",
    "stat_dimensions": "📐  Image Dimensions",
    "stat_raw_size_bytes": "📦  Original Data Size",
    "stat_encoded_bits": "🔢  Embedded Bits Count",
    "stat_total_blocks": "🔲  Total 8×8 Blocks",
    "stat_capacity_used_percent": "📊  Capacity Used Ratio",
    "stat_delta_used": "⚡  Signal Strength (Delta)",
    "stat_ecc_symbols": "🛡️   Reed-Solomon Symbols",
    "stat_redundancy": "🔁  Spatial Redundancy",
    "stat_resolution": "🖥️   Video Resolution",
    "stat_total_frames": "🎞️   Total Frames",
    "stat_duration_sec": "⏱️   Duration",
    "stat_capacity_per_frame_bytes": "💾  Capacity per Frame",
    "stat_total_capacity_bytes": "💾  Total Capacity",
    "stat_block_size": "🔲  Video Block Size",
    "stat_baud_rate": "📡  Baud Rate (baud/s)",
    "stat_total_bits": "🔢  Total Audio Bits",
    "stat_freq_zero_hz": "〰️  Bit=0 Frequency",
    "stat_freq_one_hz": "〰️  Bit=1 Frequency",
    "stat_sync_freq_hz": "🔔  Sync Frequency",

    # ── Automated Self-Test ──
    "test_panel_title": "🧪  Automated Self-Test",
    "test_panel_desc": "This test verifies all 3 engines with simulated platform compression:\n  📸 DCT Image — simulated JPEG q=70\n  🎬 HyperGrid Video — direct encode and recover\n  🎵 FSK Audio — WAV encode and decode",
    "test_t1_label": "📸  Testing Image Engine (DCT Steganography) ...",
    "test_t2_label": "🎬  Testing Video Engine (HyperGrid) ...",
    "test_t3_label": "🎵  Testing Audio Engine (Acoustic FSK) ...",
    "test_results_title": "Test Results",
    "test_col_engine": "Engine",
    "test_col_status": "Status",
    "test_col_details": "Details",
    "test_status_success": "Pass",
    "test_status_fail": "Fail",
    "test_all_ok": "✅  All tests passed! Library is working with 100% efficiency.",
    "test_some_failed": "⚠️  Some tests failed.\nEnsure all dependencies are installed:\n  pip install opencv-python scipy reedsolo cryptography numpy rich",

    # ── Help ──
    "help_title": "❓  Help & Usage",
    "help_desc": "socialdisk v2.0 — Multi-platform steganography & encryption suite",
    "help_interactive_title": "Interactive mode (no arguments):",
    "help_interactive_cmd": "python cli.py",
    "help_img_title": "Image commands:",
    "help_vid_title": "Video commands:",
    "help_aud_title": "Audio commands:",
    "help_common_title": "Common options:",
    "help_tech_title": "Core technologies:",

    # ── CLI Arguments ──
    "arg_platform_help": "Target platform (instagram, whatsapp, twitter, ...)",
    "arg_platforms_help": "List all supported platforms and exit",
    "arg_lang_help": "Display language (ar = Arabic, en = English)",
    "cmd_no_command_warn": "No command specified. Run without arguments for interactive mode, or use --help.",

    # ── Error Messages & Hints ──
    "err_panel_title": "⚠️  Operation Error",
    "err_wrong_password_msg": "Decryption failed: Incorrect password or the data was modified.",
    "err_wrong_password_hint": "💡 Suggested Fix: Verify your password carefully (passwords are case-sensitive).",
    "err_capacity_msg": "Data size exceeds the capacity of the cover media.",
    "err_capacity_hint": "💡 Suggested Fix: Use a higher-resolution image (e.g. 1920×1080+) or reduce ECC symbols.",
    "err_corruption_msg": "Corruption level too high: Platform compression exceeded recovery threshold.",
    "err_corruption_hint": "💡 Suggested Fix: Re-embed with higher ECC symbols (--ecc 64 or 96) and higher redundancy.",
    "err_ffmpeg_msg": "ffmpeg is not installed or not found in system PATH.",
    "err_ffmpeg_hint": "💡 Suggested Fix: Install ffmpeg to enable audio extraction from video, or provide a WAV audio file directly.",
    "err_file_not_found_msg": "The specified file was not found at the given path.",
    "err_file_not_found_hint": "💡 Suggested Fix: Verify the file path and extension, or drag and drop the file into the terminal.",
    "err_no_audio_preamble_msg": "Audio file does not contain a SocialDisk sync tone.",
    "err_no_audio_preamble_hint": "💡 Suggested Fix: Ensure the audio file was generated by SocialDisk and was not trimmed.",
    "err_no_video_frames_msg": "Failed to decode video matrix frames.",
    "err_no_video_frames_hint": "💡 Suggested Fix: Ensure the --block-size parameter matches the one used during encoding.",
    "err_corrupted_payload_msg": "Data integrity check failed: Packet is internally corrupted.",
    "err_corrupted_payload_hint": "💡 Suggested Fix: Ensure you download the original file without additional platform compression.",
    "err_generic_hint": "💡 Suggested Fix: Check the error details above or try again with valid inputs.",
}
