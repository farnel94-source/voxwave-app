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
        "keyboard>=0.13.5",
        "pyyaml>=6.0",
        "click>=8.1.0",
        "webrtcvad-wheels>=2.0.10",
        "PySide6>=6.6.0",
        "Pillow>=10.0.0",
        "requests>=2.31.0",
        "groq>=0.4.0",
        "openai>=1.0.0",
        "python-dotenv>=1.0.0",
        "cryptography>=41.0.0",
        'evdev>=1.7.0; sys_platform == "linux"',
    ],
    entry_points={
        "console_scripts": [
            "voxtool=src.app:main",
        ],
    },
)
