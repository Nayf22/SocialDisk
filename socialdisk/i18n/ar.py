"""
SocialDisk — Arabic Language Dictionary (ar)
المعجم العربي لنصوص SocialDisk
"""
from __future__ import annotations

STRINGS: dict[str, str] = {
    # ── عام ──
    "app_name": "SocialDisk",
    "app_sub": "أداة إخفاء وتشفير البيانات متعددة المنصات",
    "btn_back": "↩️  العودة",
    "btn_back_to_menu": "↩️  العودة للقائمة الرئيسية",
    "btn_back_to_platform": "↩️  العودة لاختيار المنصة",
    "btn_refresh": "تحديث العرض",
    "op_cancelled": "↩️  تم إلغاء العملية والعودة.",
    "prompt_back_hint": "[أو 0 للرجوع]",
    "press_enter_to_return": "اضغط Enter للعودة إلى القائمة",
    "press_enter_to_back": "اضغط Enter للعودة",
    "interrupted_by_user": "⚠️  تم الإيقاف بواسطة المستخدم.",
    "thanks_for_using": "شكراً لاستخدامك SocialDisk 🛡️",
    "invalid_choice": "اختيار غير صالح.",
    "error_prefix": "خطأ:",
    "success_prefix": "نجاح:",
    "warning_prefix": "تنبيه:",
    "file_not_found": "الملف غير موجود:",
    "not_supported": "غير مدعوم:",

    # ── اختيار اللغة ──
    "lang_prompt_title": "🌍 الرجاء اختيار لغة العرض / Please select display language:",
    "lang_option_ar": "العربية (Arabic)",
    "lang_option_en": "English (الإنجليزية)",
    "lang_prompt_input": "اختر اللغة / Select language (1-2)",
    "lang_switched_success": "تم ضبط لغة العرض إلى: العربية",
    "lang_change_title": "🌐  تغيير لغة العرض",

    # ── القائمة الرئيسية ──
    "main_menu_title": "  القائمة الرئيسية  ",
    "menu_embed": "🚀  تضمين بيانات / إخفاء ملف",
    "menu_extract": "🔓  استخراج بيانات مُخفاة",
    "menu_platforms": "🌐  استعراض المنصات المدعومة",
    "menu_test": "🧪  تشغيل الاختبار التلقائي",
    "menu_help": "❓  مساعدة واستخدام الأوامر",
    "menu_lang": "🌐  تغيير اللغة / Change Language",
    "menu_exit": "🚪  خروج",
    "prompt_your_choice": "اختيارك",

    # ── اختيار المنصة ──
    "platform_select_title": "📱  اختر المنصة الاجتماعية",
    "platform_prompt_idx": "رقم المنصة",
    "platform_chosen": "المنصة المختارة:",
    "platform_invalid": "رقم غير صالح، تم اختيار Instagram افتراضياً.",
    "cap_photos": "📸 صور",
    "cap_video": "🎬 فيديو",
    "cap_audio": "🎵 صوت",

    # ── جدول المنصات ──
    "tbl_platforms_title": "المنصات المدعومة في SocialDisk v2.0",
    "tbl_col_num": "#",
    "tbl_col_platform": "المنصة",
    "tbl_col_images": "الصور",
    "tbl_col_video": "الفيديو",
    "tbl_col_audio": "الصوت",
    "tbl_col_jpeg_q": "JPEG جودة",
    "tbl_col_delta": "Delta DCT",
    "tbl_col_desc": "الوصف",

    # ── اختيار العملية ──
    "op_select_title": "⚙️   اختر العملية",
    "op_prompt_idx": "رقم العملية",
    "op_image_embed": "📸  إخفاء بيانات في صورة",
    "op_image_extract": "🔓  استخراج بيانات من صورة",
    "op_video_embed": "🎬  تحويل ملف إلى فيديو",
    "op_video_extract": "🎬  استخراج ملف من فيديو",
    "op_audio_embed": "🎵  تحويل بيانات إلى صوت (WAV)",
    "op_audio_extract": "🎵  استخراج بيانات من صوت",

    # ── مصدر البيانات ──
    "payload_source_title": "مصدر البيانات السرية:",
    "payload_source_text": "نص مباشر",
    "payload_source_file": "ملف",
    "payload_source_prompt": "اختر",
    "payload_file_prompt": "📂  مسار الملف",
    "payload_file_read_ok": "📦 تم قراءة الملف: {size:,} بايت",
    "payload_text_prompt": "✏️   النص السري",
    "payload_required_err": "يجب تحديد نص (-t) أو ملف (-f).",

    # ── تدفقات التضمين والاستخراج ──
    "prompt_cover_img": "📂  صورة الغلاف",
    "prompt_output_img": "💾  مسار حفظ الصورة المُعدَّلة",
    "prompt_password": "🔑  كلمة المرور",
    "spinner_image_embed": "⚙️  جارٍ التضمين في الصورة...",
    "image_embed_ready": "الصورة جاهزة:",
    "title_stats_image_embed": "📊  إحصائيات التضمين في الصورة",

    "prompt_image_extract": "📂  مسار الصورة (بعد التحميل من المنصة)",
    "prompt_save_or_display": "💾  مسار الحفظ (Enter = عرض النص)",
    "spinner_image_extract": "🔓  جارٍ الاستخراج من الصورة...",

    "prompt_video_source_file": "📂  مسار الملف المراد تخزينه",
    "prompt_video_output": "💾  مسار الفيديو الناتج (.mp4)",
    "video_file_size": "📦 حجم الملف: {size:,} بايت",
    "spinner_video_embed": "🎬  جارٍ توليد الفيديو...",
    "video_embed_ready": "الفيديو جاهز:",
    "title_stats_video": "📊  إحصائيات الفيديو",

    "prompt_video_extract": "📂  مسار الفيديو (بعد التحميل)",
    "prompt_video_out_file": "💾  مسار حفظ الملف المسترجع مع الامتداد (مثال: secret.zip أو data.pdf)",
    "auto_detected_ext": "تم اكتشاف نوع الملف تلقائياً: {ext}",
    "spinner_video_extract": "🎬  جارٍ استرجاع الملف...",
    "video_recovered_ok": "تم حفظ الملف:",

    "prompt_audio_output": "💾  مسار ملف الصوت الناتج (.wav)",
    "spinner_audio_embed": "🎵  جارٍ توليد الموجة الصوتية...",
    "audio_embed_ready": "الصوت جاهز:",
    "title_stats_audio": "📊  إحصائيات الملف الصوتي",

    "prompt_audio_extract": "📂  مسار الملف الصوتي / الفيديو",
    "spinner_audio_extract": "🎵  جارٍ تحليل الصوت...",

    # ── البيانات المستخرجة ──
    "extracted_data_title": "🔓  البيانات المستخرجة",
    "extracted_data_saved": "تم حفظ البيانات في:",
    "extracted_binary_warning": "البيانات ثنائية ({size:,} بايت).\nأضف [-o مسار_الحفظ] لتخزينها كملف.",

    # ── الإحصائيات ──
    "stat_table_title": "📊  إحصائيات العملية",
    "stat_table_param": "المعامل",
    "stat_table_val": "القيمة",
    "bytes_suffix": "بايت",
    "stat_dimensions": "📐  أبعاد الصورة",
    "stat_raw_size_bytes": "📦  حجم البيانات الأصلي",
    "stat_encoded_bits": "🔢  عدد البتات المُضمَّنة",
    "stat_total_blocks": "🔲  إجمالي الكتل 8×8",
    "stat_capacity_used_percent": "📊  نسبة استهلاك السعة",
    "stat_delta_used": "⚡  قوة الإشارة (Delta)",
    "stat_ecc_symbols": "🛡️   رموز Reed-Solomon",
    "stat_redundancy": "🔁  عامل التكرار المكاني",
    "stat_resolution": "🖥️   دقة الفيديو",
    "stat_total_frames": "🎞️   عدد الإطارات",
    "stat_duration_sec": "⏱️   المدة الزمنية",
    "stat_capacity_per_frame_bytes": "💾  سعة كل إطار",
    "stat_total_capacity_bytes": "💾  السعة الكلية",
    "stat_block_size": "🔲  حجم بلوك الفيديو",
    "stat_baud_rate": "📡  معدل البث (بود/ث)",
    "stat_total_bits": "🔢  إجمالي البتات الصوتية",
    "stat_freq_zero_hz": "〰️  تردد البت=0",
    "stat_freq_one_hz": "〰️  تردد البت=1",
    "stat_sync_freq_hz": "🔔  تردد المزامنة",

    # ── الاختبار التلقائي ──
    "test_panel_title": "🧪  الاختبار التلقائي",
    "test_panel_desc": "يختبر هذا الاختبار المحركات الثلاثة مع محاكاة ضغط المنصة:\n  📸 صورة DCT — محاكاة JPEG q=70\n  🎬 فيديو HyperGrid — ترميز واسترجاع مباشر\n  🎵 صوت FSK — ترميز واسترجاع WAV",
    "test_t1_label": "📸  اختبار الصورة (DCT Steganography) ...",
    "test_t2_label": "🎬  اختبار الفيديو (HyperGrid Engine) ...",
    "test_t3_label": "🎵  اختبار الصوت (Acoustic FSK Engine) ...",
    "test_results_title": "نتائج الاختبار",
    "test_col_engine": "المحرك",
    "test_col_status": "الحالة",
    "test_col_details": "التفاصيل",
    "test_status_success": "نجاح",
    "test_status_fail": "فشل",
    "test_all_ok": "✅  جميع الاختبارات نجحت! المكتبة تعمل بكفاءة 100%.",
    "test_some_failed": "⚠️  بعض الاختبارات فشلت.\nتأكد من تثبيت جميع المتطلبات:\n  pip install opencv-python scipy reedsolo cryptography numpy rich",

    # ── المساعدة ──
    "help_title": "❓  المساعدة",
    "help_desc": "socialdisk v2.0 — أداة تخفي وتشفير البيانات عبر المنصات الاجتماعية",
    "help_interactive_title": "الوضع التفاعلي (بدون معطيات):",
    "help_interactive_cmd": "python cli.py",
    "help_img_title": "أوامر الصور:",
    "help_vid_title": "أوامر الفيديو:",
    "help_aud_title": "أوامر الصوت:",
    "help_common_title": "خيارات مشتركة:",
    "help_tech_title": "التقنيات الأساسية:",

    # ── موجهات سطر الأوامر (CLI Args) ──
    "arg_platform_help": "المنصة المستهدفة (instagram, whatsapp, twitter, ...)",
    "arg_platforms_help": "عرض قائمة كل المنصات والخروج",
    "arg_lang_help": "لغة العرض (ar = العربية, en = English)",
    "cmd_no_command_warn": "لم يُحدَّد أمر. شغّل بدون معطيات للوضع التفاعلي، أو استخدم --help.",

    # ── رسائل الأخطاء الشائعة وحلولها ──
    "err_panel_title": "⚠️  خطأ في العملية",
    "err_wrong_password_msg": "فشل فك التشفير: كلمة المرور غير صحيحة، أو تم التعديل على الملف.",
    "err_wrong_password_hint": "💡 الحل المقترح: تأكد من كتابة كلمة المرور بدقة وبنفس حالة الأحرف (حساسة لحالة الأحرف).",
    "err_capacity_msg": "حجم البيانات أكبر من سعة وسيط الغلاف المحدد.",
    "err_capacity_hint": "💡 الحل المقترح: استخدم صورة ذات دقة وأبعاد أكبر (مثل 1920×1080 فأعلى) أو قلل نسبة رموز ECC.",
    "err_corruption_msg": "مستوى التلف مرتفع جداً: خوارزميات ضغط المنصة أتلفت أجزاء كبيرة من البتات وتجاوزت سعة التصحيح.",
    "err_corruption_hint": "💡 الحل المقترح: أعد التضمين مع رفع رموز تصحيح الأخطاء (--ecc 64 أو 96) وزيادة التكرار (--redundancy).",
    "err_ffmpeg_msg": "أداة ffmpeg غير مثبتة أو غير مضافة إلى مسار النظام (PATH).",
    "err_ffmpeg_hint": "💡 الحل المقترح: قم بتثبيت ffmpeg لإتاحة استخراج الصوت من ملفات الفيديو، أو استخدم ملف WAV صوتي مباشر.",
    "err_file_not_found_msg": "لم يتم العثور على الملف المحدد في المسار المدخل.",
    "err_file_not_found_hint": "💡 الحل المقترح: تأكد من صحة مسار الملف وامتداده، أو اسحب الملف وأفلته داخل الطرفية.",
    "err_no_audio_preamble_msg": "الملف الصوتي لا يحتوي على بيانات مخفية من SocialDisk.",
    "err_no_audio_preamble_hint": "💡 الحل المقترح: تأكد من أن الملف الصوتي تم إنشاؤه بواسطة SocialDisk ولم يتم قصه أو تعديل بدايته.",
    "err_no_video_frames_msg": "فشل قراءة إطارات مصفوفة الفيديو.",
    "err_no_video_frames_hint": "💡 الحل المقترح: تأكد من تطابق حجم البلوك (--block-size) مع ما تم استخدامه أثناء التشفير.",
    "err_corrupted_payload_msg": "فشل التحقق من سلامة البيانات: الملف تالف جزئياً أو غير مكتمل.",
    "err_corrupted_payload_hint": "💡 الحل المقترح: احرص على تنزيل الملف الأصلي بكامل جودته دون ضغط إضافي من المنصة.",
    "err_generic_hint": "💡 الحل المقترح: راجع رسالة الخطأ أو أعد المحاولة مع التأكد من صحة المدخلات.",
}
