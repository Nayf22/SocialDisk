import os
import sys
import argparse
from instavault import InstaVault, DCTImageEngine

def main():
    parser = argparse.ArgumentParser(
        description="🛡️ InstaVault CLI - أداة تخزين واسترجاع البيانات عبر إنستغرام",
        formatter_class=argparse.RawTextHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", required=True, help="الأوامر المتاحة")

    # ---------------- 1. أمر الإخفاء في صورة ----------------
    img_hide = subparsers.add_parser("hide-img", help="إخفاء نص أو ملف صغير داخل صورة عادية (DCT)")
    img_hide.add_argument("-i", "--image", required=True, help="مسار الصورة الأصلية")
    img_hide.add_argument("-o", "--out", required=True, help="مسار حفظ الصورة الجاهزة للرفع")
    img_hide.add_argument("-p", "--password", required=True, help="كلمة المرور للتشفير")
    img_hide.add_argument("-t", "--text", help="النص السري المراد إخفاؤه مباشرة")
    img_hide.add_argument("-f", "--file", help="أو مسار ملف صغير لإخفائه (بدلاً من النص)")
    img_hide.add_argument("--delta", type=float, default=42.0, help="قوة المناعة ضد الضغط (الافتراضي: 42.0)")

    # ---------------- 2. أمر الاسترجاع من صورة ----------------
    img_rec = subparsers.add_parser("recover-img", help="استرجاع البيانات من صورة محملة من إنستغرام")
    img_rec.add_argument("-i", "--image", required=True, help="مسار الصورة المحملة من إنستغرام")
    img_rec.add_argument("-p", "--password", required=True, help="كلمة المرور")
    img_rec.add_argument("-o", "--out", help="مسار حفظ الملف المسترجع (إن لم تحدده سيطبع النص في الشاشة)")

    # ---------------- 3. أمر تحويل ملف إلى فيديو ----------------
    vid_enc = subparsers.add_parser("encode-vid", help="تحويل أي ملف كبير إلى فيديو مقاوم للضغط (HyperGrid)")
    vid_enc.add_argument("-f", "--file", required=True, help="مسار الملف المراد تخزينه (ZIP, PDF, EXE, الخ)")
    vid_enc.add_argument("-o", "--out", required=True, help="مسار حفظ الفيديو الناتج (مثلاً reel.mp4)")
    vid_enc.add_argument("-p", "--password", required=True, help="كلمة المرور للتشفير")

    # ---------------- 4. أمر استرجاع ملف من فيديو ----------------
    vid_dec = subparsers.add_parser("decode-vid", help="استرجاع الملف الأصلي من فيديو محمل من إنستغرام")
    vid_dec.add_argument("-v", "--video", required=True, help="مسار الفيديو المحمل من إنستغرام")
    vid_dec.add_argument("-o", "--out", required=True, help="مسار واسم الملف المسترجع (مثلاً restored.zip)")
    vid_dec.add_argument("-p", "--password", required=True, help="كلمة المرور")

    # ---------------- 5. أمر تحويل بيانات إلى صوت ----------------
    aud_enc = subparsers.add_parser("encode-aud", help="تحويل ملف أو نص إلى موجة صوتية (FSK Audio)")
    aud_enc.add_argument("-o", "--out", required=True, help="مسار حفظ الصوت (output.wav)")
    aud_enc.add_argument("-p", "--password", required=True, help="كلمة المرور")
    aud_enc.add_argument("-t", "--text", help="نص لتحويله لصوت")
    aud_enc.add_argument("-f", "--file", help="أو ملف لتحويله لصوت")

    # ---------------- 6. أمر استرجاع بيانات من صوت/فيديو ----------------
    aud_dec = subparsers.add_parser("decode-aud", help="استرجاع البيانات من ملف صوتي أو فيديو")
    aud_dec.add_argument("-m", "--media", required=True, help="مسار الصوت أو الفيديو")
    aud_dec.add_argument("-p", "--password", required=True, help="كلمة المرور")
    aud_dec.add_argument("-o", "--out", help="مسار حفظ الملف المسترجع (اختياري للنصوص)")

    args = parser.parse_args()

    try:
        # تنفيذ أوامر الصور
        if args.command == "hide-img":
            payload = _get_payload(args.text, args.file)
            stats = DCTImageEngine.embed(args.image, args.out, payload, args.password, delta=args.delta)
            print(f"✅ تم التضمين بنجاح داخل الصورة: {args.out}")
            print(f"📊 الإحصائيات: الأبعاد={stats['dimensions']} | استهلاك السعة={stats['capacity_used_percent']}%")

        elif args.command == "recover-img":
            data = InstaVault.recover_from_image(args.image, args.password)
            _save_or_print(data, args.out)

        # تنفيذ أوامر الفيديو
        elif args.command == "encode-vid":
            with open(args.file, "rb") as f:
                payload = f.read()
            stats = InstaVault.file_to_video(args.out, payload, args.password)
            print(f"✅ تم تحويل الملف إلى فيديو بنجاح: {args.out}")
            print(f"📊 الإحصائيات: عدد الإطارات={stats['total_frames']} | المدة={stats['duration_sec']} ثانية")

        elif args.command == "decode-vid":
            data = InstaVault.video_to_file(args.video, args.password)
            with open(args.out, "wb") as f:
                f.write(data)
            print(f"✅ تم استرجاع الملف بنجاح وحفظه في: {args.out} (الحجم: {len(data)} بايت)")

        # تنفيذ أوامر الصوت
        elif args.command == "encode-aud":
            payload = _get_payload(args.text, args.file)
            stats = InstaVault.data_to_audio(args.out, payload, args.password)
            print(f"✅ تم توليد الملف الصوتي بنجاح: {args.out} (المدة: {stats['duration_sec']} ثانية)")

        elif args.command == "decode-aud":
            data = InstaVault.audio_to_data(args.media, args.password)
            _save_or_print(data, args.out)

    except Exception as e:
        print(f"❌ خطأ: {e}", file=sys.stderr)
        sys.exit(1)

def _get_payload(text_arg, file_arg) -> bytes:
    if text_arg:
        return text_arg.encode("utf-8")
    elif file_arg:
        with open(file_arg, "rb") as f:
            return f.read()
    else:
        raise ValueError("يجب تحديد نص عبر (-t) أو ملف عبر (-f).")

def _save_or_print(data: bytes, out_path: str):
    if out_path:
        with open(out_path, "wb") as f:
            f.write(data)
        print(f"✅ تم استرجاع البيانات وحفظها في الملف: {out_path}")
    else:
        try:
            print(f"\n🔓 الرسالة المسترجعة:\n{data.decode('utf-8')}\n")
        except UnicodeDecodeError:
            print("⚠️ البيانات المسترجعة عبارة عن ملف ثنائي (Binary) وليست نصاً، يرجى إضافة -o لتحديد مسار حفظ الملف.")

if __name__ == "__main__":
    main()
