# NeoLight Development Tools

## Overview
Comprehensive toolkit for NeoLight development, research, and performance optimization.

## AI Research Assistants

### Multi-AI Research Assistant (`ai/research_assistant.py`)
Unified interface supporting multiple AI providers with automatic fallback:
- **OpenAI GPT-4** (best for complex analysis)
- **Anthropic Claude** (best for reasoning)
- **Mistral** (cost-effective)
- **Google Gemini** (free tier available)
- **Groq** (ultra-fast, free tier available)

**Usage:**
```python
from ai.research_assistant import get_research_assistant, research

# Quick research
result = research("Best RSI trading strategies for crypto")

# Full assistant
assistant = get_research_assistant()
analysis = assistant.analyze_code(code_snippet, language="python")
strategy = assistant.suggest_strategy("bull market", {"RSI": 45})
```

**Setup:**
Set environment variables for desired providers:
```bash
export OPENAI_API_KEY="your-key"
export ANTHROPIC_API_KEY="your-key"
export GROQ_API_KEY="your-key"  # Free tier available
export GOOGLE_API_KEY="your-key"  # Free tier available
```

## Code Quality Tools

### Type Checking
- **mypy**: Static type checking
```bash
mypy trader/smart_trader.py
```

### Code Formatting
- **black**: Opinionated formatter
```bash
black trader/
```

- **ruff**: Fast linter (replaces flake8 + isort)
```bash
ruff check trader/
ruff format trader/
```

### Linting
- **pylint**: Comprehensive linting
```bash
pylint trader/
```

- **flake8**: Style guide enforcement
```bash
flake8 trader/
```

### Security
- **bandit**: Security vulnerability scanner
```bash
bandit -r trader/
```

- **safety**: Dependency vulnerability checker
```bash
safety check
```

## Testing Tools

### pytest
```bash
# Run tests
pytest tests/

# With coverage
pytest --cov=trader tests/

# Parallel execution
pytest -n auto tests/
```

## Performance Profiling

### Memory Profiling
```python
from memory_profiler import profile

@profile
def my_function():
    # Your code
    pass
```

### Line Profiling
```python
from line_profiler import LineProfiler

lp = LineProfiler()
lp.add_function(my_function)
lp.run('my_function()')
lp.print_stats()
```

### py-spy (System-wide Profiler)
```bash
# Profile running Python process
py-spy top --pid <PID>

# Generate flamegraph
py-spy record -o profile.svg --pid <PID>
```

### pyinstrument (Statistical Profiler)
```python
from pyinstrument import Profiler

profiler = Profiler()
profiler.start()
# Your code
profiler.stop()
profiler.print()
```

## Development Utilities

### Rich (Beautiful Terminal Output)
```python
from rich.console import Console
from rich.table import Table

console = Console()
console.print("[bold green]NeoLight[/bold green] is running!")
```

### IPython (Enhanced REPL)
```bash
ipython
```

### Jupyter (Notebooks)
```bash
jupyter notebook
```

## Installation

Run the installation script:
```bash
bash scripts/install_dev_tools.sh
```

Check installed tools:
```bash
bash scripts/check_dev_tools.sh
```

## Quick Start

1. **Research a trading strategy:**
```python
from ai.research_assistant import research
result = research("Best RSI thresholds for crypto trading")
```

2. **Analyze code performance:**
```bash
python3 -m pyinstrument trader/smart_trader.py
```

3. **Check code quality:**
```bash
ruff check trader/
black trader/
mypy trader/
```

4. **Profile memory usage:**
```bash
python3 -m memory_profiler trader/smart_trader.py
```

## Recommendations

### For Daily Development
- Use **ruff** for fast linting
- Use **black** for consistent formatting
- Use **mypy** for type safety

### For Performance Optimization
- Use **py-spy** for system-wide profiling
- Use **memory-profiler** for memory leak detection
- Use **line_profiler** for line-by-line analysis

### For AI Assistance
- Use **Groq** (free tier) for fast responses
- Use **OpenAI GPT-4** for complex analysis
- Use **Anthropic Claude** for reasoning tasks

## Environment Variables

Create `.env` file:
```bash
# AI Providers (choose one or more)
OPENAI_API_KEY=your-key
ANTHROPIC_API_KEY=your-key
GROQ_API_KEY=your-key  # Free tier available
GOOGLE_API_KEY=your-key  # Free tier available
MISTRAL_API_KEY=your-key

# NeoLight Configuration
ALPACA_API_KEY=your-key
ALPACA_API_SECRET=your-secret
NEOLIGHT_USE_ALPACA_QUOTES=true
```

