from setuptools import setup, find_packages

setup(
    name="hedwig",
    version="0.1.0",
    description="Multi-Agent Task Execution System",
    author="Your Name",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.8",
    install_requires=[
        "pydantic>=2.0.0",
        "typing-extensions>=4.0.0",
        "langchain>=0.1.0",
        "langchain-openai>=0.1.0",
        "openai>=1.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.21.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "hedwig=hedwig.cli:main",
        ],
    },
)