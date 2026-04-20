from setuptools import setup, find_packages

setup(
    name="hermes-tts",
    version="0.1.0",
    description="Text-to-Speech voice synthesis & delivery for Hermes Agent",
    python_requires=">=3.9",
    packages=find_packages(),
    install_requires=[
        "edge-tts>=6.1.0",
        "httpx>=0.24.0",
    ],
    entry_points={
        "console_scripts": [
            "hermes-tts=hermes_tts.cli:main",
        ],
    },
)
