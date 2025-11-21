# NeoLight Development Setup Guide

**Last Updated:** 2025-11-18  
**Python Version:** 3.12+  
**Status:** ✅ World-Class Development Tools Configured

---

## Overview

This guide covers the development tools and workflows for the NeoLight trading system. All tools are **free** and designed to improve code quality and productivity.

---

## Tools Installed

### 1. **Ruff** - Fast Python Linter & Formatter

**What it does:**
- Lints Python code (finds errors, style issues)
- Formats code automatically
- 10-100x faster than Black + flake8

**Usage:**

```bash
# Check for issues
ruff check .

# Auto-fix issues
ruff check --fix .

# Format code
ruff format .

# Check specific file
ruff check trader/smart_trader.py
```

**Configuration:** `pyproject.toml` (line length: 100, Python 3.12+)

---

### 2. **Pre-commit Hooks** - Automatic Code Quality Checks

**What it does:**
- Runs checks automatically before each commit
- Prevents bad code from being committed
- Runs Ruff, markdownlint, and file checks

**Setup (one-time):**

```bash
# Install pre-commit
pip install pre-commit

# Install git hooks
pre-commit install

# Test hooks manually
pre-commit run --all-files
```

**What runs on commit:**
- ✅ Ruff linting (auto-fixes issues)
- ✅ Ruff formatting
- ✅ Markdown linting
- ✅ Trailing whitespace removal
- ✅ End-of-file fixes
- ✅ YAML/JSON validation

**Configuration:** `.pre-commit-config.yaml`

---

### 3. **Pytest** - Lightweight Testing Framework

**What it does:**
- Runs automated tests
- Generates coverage reports
- Fast, simple test execution

**Usage:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_smart_trader_basic.py

# Run with verbose output
pytest -v

# Skip slow tests
pytest -m "not slow"
```

**Test Structure:**
```
tests/
├── conftest.py          # Shared fixtures
└── test_smart_trader_basic.py  # Basic smoke tests
```

**Configuration:** `pytest.ini`

---

### 4. **Quick Status Dashboard** - Real-Time System Monitoring

**What it does:**
- Shows trading agent status at a glance
- Displays portfolio value and positions
- Shows recent trades and errors
- Monitors system health

**Usage:**

```bash
# One-time status check
./scripts/quick_status.sh

# Watch mode (auto-refresh every 5 seconds)
./scripts/quick_status.sh --watch

# Custom refresh interval (10 seconds)
./scripts/quick_status.sh --watch --refresh 10
```

**What it shows:**
- ✅ Trading agent status (running/stopped, PID, uptime)
- 💰 Portfolio value and active positions count
- 📈 Recent trades (last 5)
- 🔌 Circuit breaker status
- ⚠️ Recent errors/warnings (last 5)
- 💻 System health (CPU, memory)

---

## Quick Reference Commands

### Code Quality

```bash
# Format all Python files
ruff format .

# Check and fix all Python files
ruff check --fix .

# Run pre-commit on all files
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run tests with coverage
pytest --cov --cov-report=html

# Run specific test
pytest tests/test_smart_trader_basic.py::TestSmartTraderImports
```

### Status Monitoring

```bash
# Quick status check
./scripts/quick_status.sh

# Watch mode
./scripts/quick_status.sh --watch
```

---

## Workflow Recommendations

### Before Committing Code

1. **Run Ruff:**
   ```bash
   ruff check --fix .
   ruff format .
   ```

2. **Run Tests:**
   ```bash
   pytest
   ```

3. **Pre-commit will run automatically** when you commit (if installed)

### Daily Development

1. **Start with status check:**
   ```bash
   ./scripts/quick_status.sh
   ```

2. **Make changes**

3. **Before committing:**
   ```bash
   ruff check --fix .
   pytest
   ```

### Continuous Monitoring

```bash
# Watch system status in separate terminal
./scripts/quick_status.sh --watch
```

---

## Configuration Files

### `pyproject.toml`
- Ruff configuration (linting rules, line length)
- Pytest configuration
- Coverage settings

### `.pre-commit-config.yaml`
- Pre-commit hooks configuration
- Automatic code quality checks

### `pytest.ini`
- Test discovery patterns
- Coverage settings
- Marker definitions

---

## Troubleshooting

### Ruff Issues

**Problem:** Ruff not found
```bash
# Install ruff
pip install ruff
```

**Problem:** Too many errors
```bash
# Fix automatically
ruff check --fix .
```

### Pre-commit Issues

**Problem:** Hooks not running
```bash
# Reinstall hooks
pre-commit install
```

**Problem:** Hook fails
```bash
# Run manually to see error
pre-commit run --all-files
```

### Pytest Issues

**Problem:** Tests not found
```bash
# Check test discovery
pytest --collect-only
```

**Problem:** Import errors
```bash
# Ensure project root is in PYTHONPATH
export PYTHONPATH="${HOME}/neolight:$PYTHONPATH"
```

### Status Dashboard Issues

**Problem:** No data shown
```bash
# Check if agent is running
ps aux | grep smart_trader

# Check log file exists
ls -lh logs/smart_trader.log

# Check state file exists
ls -lh state/smart_trader_state.json
```

---

## Best Practices

1. **Always run Ruff before committing**
   - Catches errors early
   - Keeps code consistent

2. **Write tests for new features**
   - Start with smoke tests
   - Add integration tests for complex logic

3. **Use status dashboard regularly**
   - Monitor system health
   - Catch issues early

4. **Keep pre-commit hooks enabled**
   - Prevents bad commits
   - Maintains code quality

---

## Next Steps

1. ✅ **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. ✅ **Set up pre-commit:**
   ```bash
   pre-commit install
   ```

3. ✅ **Run initial checks:**
   ```bash
   ruff check --fix .
   pytest
   ```

4. ✅ **Test status dashboard:**
   ```bash
   ./scripts/quick_status.sh
   ```

---

## Additional Resources

- **Ruff Docs:** https://docs.astral.sh/ruff/
- **Pytest Docs:** https://docs.pytest.org/
- **Pre-commit Docs:** https://pre-commit.com/

---

**All tools are free and open-source. No monthly payments required!**

