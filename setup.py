"""
Facebook Auto-Poster - Automated posting to Facebook groups
"""
from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="fbposter",
    version="1.0.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="Automated Facebook group posting with scheduling and CLI management",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/facebook-autoposter",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
    ],
    python_requires=">=3.8",
    install_requires=[
        "selenium>=4.27.1",
        "webdriver-manager>=4.0.0",
        "requests>=2.32.4",
        "tenacity>=8.2.0",
        "pydantic>=2.0.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0",
        "click>=8.1.0",
        "rich>=13.0.0",
        "python-dateutil>=2.8.0",
    ],
    entry_points={
        "console_scripts": [
            "fbposter=fbposter.cli.main:cli",
        ],
    },
)
