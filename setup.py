from setuptools import setup, find_packages

setup(
    name="voxtool",
    version="0.1.0",
    description="Dictée vocale intelligente - Parle, transcrit, nettoie, colle.",
    author="VoxTool",
    python_requires=">=3.11",
    packages=find_packages(),
    install_requires=[
        "faster-whisper>=1.0.0",
        "sounddevice>=0.4.6",
        "numpy>=1.24.0",
        "pynput>=1.7.6",
        "pyperclip>=1.8.2",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "webrtcvad>=2.0.10",
        "pystray>=0.19.0",
        "Pillow>=10.0.0",
        "requests>=2.31.0",
    ],
    entry_points={
        "console_scripts": [
            "voxtool=src.app:main",
        ],
    },
)
