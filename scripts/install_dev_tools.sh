#!/bin/bash
# NeoLight Development Tools Installation Script
# Installs all tools for better performance and development

set -e

echo "🚀 Installing NeoLight Development Tools..."
echo ""

# AI/ML SDKs
echo "📦 Installing AI SDKs..."
pip3 install --upgrade --quiet \
    openai \
    anthropic \
    mistralai \
    google-generativeai \
    groq

# Code Quality Tools
echo "📦 Installing code quality tools..."
pip3 install --upgrade --quiet \
    mypy \
    black \
    ruff \
    pylint \
    flake8 \
    bandit \
    safety \
    isort \
    autopep8

# Testing Tools
echo "📦 Installing testing tools..."
pip3 install --upgrade --quiet \
    pytest \
    pytest-cov \
    pytest-asyncio \
    pytest-mock \
    pytest-xdist \
    hypothesis

# Performance Profiling
echo "📦 Installing performance tools..."
pip3 install --upgrade --quiet \
    memory-profiler \
    line-profiler \
    py-spy \
    psutil \
    pyinstrument \
    cProfile \
    snakeviz

# Development Utilities
echo "📦 Installing development utilities..."
pip3 install --upgrade --quiet \
    ipython \
    jupyter \
    ipdb \
    rich \
    typer \
    click \
    python-dotenv \
    pyyaml \
    toml

# Type Checking & Validation
echo "📦 Installing type checking tools..."
pip3 install --upgrade --quiet \
    types-requests \
    types-python-dateutil \
    types-PyYAML

# Async & Concurrency
echo "📦 Installing async tools..."
pip3 install --upgrade --quiet \
    aiohttp \
    asyncio \
    httpx \
    trio

# Data & Analytics
echo "📦 Installing data tools..."
pip3 install --upgrade --quiet \
    pandas \
    numpy \
    scipy \
    matplotlib \
    seaborn

echo ""
echo "✅ All development tools installed!"
echo ""
echo "📊 Installed tools:"
echo "  • AI SDKs: OpenAI, Anthropic, Mistral, Google, Groq"
echo "  • Code Quality: mypy, black, ruff, pylint, flake8, bandit"
echo "  • Testing: pytest, pytest-cov, pytest-asyncio"
echo "  • Performance: memory-profiler, line-profiler, py-spy, pyinstrument"
echo "  • Development: ipython, jupyter, rich, typer"
echo "  • Data: pandas, numpy, scipy, matplotlib"
echo ""

