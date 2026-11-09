"""
SocialDisk — Multi-Platform Steganography Suite
Setup configuration
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="socialdisk",
    version="2.0.0",
    author="SocialDisk Contributors",
    description="Multi-platform steganography suite — hide & encrypt data inside images, video, and audio that survive social media compression",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Nayf22/SocialDisk.git",
    packages=find_packages(exclude=["tests*", "debug_*"]),
    py_modules=["cli", "SocialVault"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Security :: Cryptography",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
        "Topic :: Multimedia :: Graphics",
    ],
    python_requires=">=3.9",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "socialdisk=cli:main",
        ],
    },
)
