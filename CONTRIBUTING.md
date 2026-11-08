# Contributing to SocialDisk

Thank you for your interest in contributing! 🎉

## How to Contribute

### Reporting Bugs
- Open an issue on GitHub
- Include your Python version (`python --version`)
- Include the platform you tested with
- Paste the full error traceback

### Suggesting Features
- Open an issue with the `enhancement` label
- Describe the use case clearly

### Pull Requests

1. **Fork** the repository
2. **Create a branch**: `git checkout -b feature/my-feature`
3. **Make changes** and ensure all tests pass: `python full_test.py`
4. **Commit**: `git commit -m "feat: add my feature"`
5. **Push**: `git push origin feature/my-feature`
6. **Open a Pull Request**

### Commit Message Format

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat:     New feature
fix:      Bug fix
docs:     Documentation change
refactor: Code refactoring (no logic change)
test:     Adding or updating tests
perf:     Performance improvement
```

### Code Style
- Follow existing code style
- Add docstrings to all public functions
- Keep Arabic/English comments as appropriate per version
- Run `python full_test.py` before submitting — all 5 tests must pass

### Adding a New Platform

Edit `socialdisk/platforms.py` and add a new entry to the `PLATFORMS` dict:

```python
"myplatform": Platform(
    name="MyPlatform",
    image=ImageProfile(
        max_quality=85,
        delta=40.0,
        ecc_symbols=64,
        redundancy=3,
    ),
    video=VideoProfile(
        block_size=16,
        ecc_symbols=96,
    ),
    audio=AudioProfile(
        sample_rate=44100,
        baud_rate=150,
        freq_zero=1500.0,
        freq_one=2700.0,
        sync_freq=900.0,
        ecc_symbols=64,
    ),
)
```

## Development Setup

```bash
git clone https://github.com/YOUR_USERNAME/SocialDisk.git
cd SocialDisk
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
python full_test.py          # Must show 5/5
```

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
