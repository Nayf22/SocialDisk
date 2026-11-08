"""
فحص جميع بيئات Python على الجهاز وإيجاد cv2 / reedsolo
"""
import sys, os, subprocess

CURRENT = sys.executable
TARGET_PACKAGES = ['cv2', 'reedsolo']

# ── مسارات مرشحة (Python مباشر + venvs + Conda) ──────────────────────────
candidates = [
    # Python standard installs
    r'C:\Users\pc\AppData\Local\Programs\Python\Python311\python.exe',
    r'C:\Users\pc\AppData\Local\Programs\Python\Python312\python.exe',
    r'C:\Users\pc\AppData\Local\Programs\Python\Python310\python.exe',
    r'C:\Users\pc\AppData\Local\Programs\Python\Python39\python.exe',
    r'C:\Users\pc\AppData\Local\Programs\Python\Python38\python.exe',
    # Anaconda / Miniconda (user)
    r'C:\Users\pc\anaconda3\python.exe',
    r'C:\Users\pc\miniconda3\python.exe',
    r'C:\Users\pc\Anaconda3\python.exe',
    # Conda (system)
    r'C:\ProgramData\anaconda3\python.exe',
    r'C:\ProgramData\miniconda3\python.exe',
    # PyCharm project venvs (شائعة)
    r'C:\Users\pc\Desktop\instaDisk\.venv\Scripts\python.exe',
    r'C:\Users\pc\Desktop\instaDisk\venv\Scripts\python.exe',
    r'C:\Users\pc\Desktop\instaDisk\env\Scripts\python.exe',
    # مشاريع PyCharm الأخرى
    r'C:\Users\pc\PycharmProjects',
    r'C:\Users\pc\.virtualenvs',
]

# ── توسيع مجلدات venvs ────────────────────────────────────────────────────
real_exes = set()
for path in candidates:
    if os.path.isfile(path):
        real_exes.add(path)
    elif os.path.isdir(path):
        try:
            for sub in os.listdir(path):
                for variant in [
                    os.path.join(sub, 'Scripts', 'python.exe'),
                    os.path.join(sub, '.venv', 'Scripts', 'python.exe'),
                    os.path.join(sub, 'venv', 'Scripts', 'python.exe'),
                    os.path.join(sub, 'env', 'Scripts', 'python.exe'),
                ]:
                    full = os.path.join(path, variant)
                    if os.path.isfile(full):
                        real_exes.add(full)
        except Exception:
            pass

# ── الفحص ─────────────────────────────────────────────────────────────────
def check_pkg(exe, pkg):
    try:
        r = subprocess.run(
            [exe, '-c', 'import ' + pkg + '; print("OK")'],
            capture_output=True, text=True, timeout=6
        )
        return 'OK' in r.stdout
    except Exception:
        return False

all_envs = [CURRENT] + sorted(p for p in real_exes if p != CURRENT)
found_envs = []

print('=' * 65)
print(' 🔍  فحص بيئات Python — البحث عن cv2 و reedsolo')
print('=' * 65)

for exe in all_envs:
    if not os.path.isfile(exe):
        continue
    label = '⭐ [بيئة CLI الحالية]' if exe == CURRENT else '🐍 بيئة أخرى'
    pkgs_ok = [p for p in TARGET_PACKAGES if check_pkg(exe, p)]
    pkgs_no = [p for p in TARGET_PACKAGES if p not in pkgs_ok]

    folder = os.path.basename(os.path.dirname(os.path.dirname(exe)))
    print(f'\n{label}  ({folder})')
    print(f'   المسار : {exe}')
    for p in pkgs_ok:
        print(f'   ✅  {p}  — مثبّتة')
    for p in pkgs_no:
        print(f'   ❌  {p}  — غير موجودة')

    if set(TARGET_PACKAGES).issubset(set(pkgs_ok)):
        found_envs.append(exe)

print()
print('=' * 65)
if found_envs:
    print(f'\n✅  وُجدت كلتا الحزمتَين في {len(found_envs)} بيئة:')
    for e in found_envs:
        print(f'   • {e}')
    print('\n💡  يمكنك تشغيل المشروع مباشرة بهذه البيئة:')
    print(f'   {found_envs[0]} cli.py')
else:
    print('\n❌  لم تُوجد الحزم في أي بيئة. يلزم التثبيت:')
    print('   pip install opencv-python reedsolo')
