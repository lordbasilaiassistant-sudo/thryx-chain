from setuptools import setup, find_packages

setup(
    name="thryx",
    version="1.0.0",
    description="Thryx Agent Framework - Build autonomous AI agents on Thryx blockchain",
    author="Thryx Team",
    packages=find_packages(),
    install_requires=[
        "web3>=6.0.0",
        "eth-account>=0.10.0",
        "requests>=2.28.0",
    ],
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
