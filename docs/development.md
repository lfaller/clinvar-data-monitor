# Development Guide

## Environment Setup

### Prerequisites

- Python 3.8 or higher
- Poetry (see [installation](https://python-poetry.org/docs/#installation))
- AWS CLI configured with credentials
- Git

### Initial Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd clinvar-data-monitor
   ```

2. **Install Poetry** (if needed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**
   ```bash
   poetry install --with dev
   ```

4. **Activate virtual environment**
   ```bash
   poetry shell
   ```

5. **Configure AWS credentials**
   ```bash
   aws configure
   # Enter: Access Key ID, Secret Access Key, Region, Output format
   ```

6. **Set up configuration files**
   ```bash
   cp config/config.yaml.template config/config.yaml
   cp .env.template .env

   # Edit with your settings
   nano config/config.yaml
   nano .env
   ```

## Development Workflow

### Code Style and Quality

We follow the project guidelines in [AGENTS.md](../AGENTS.md):

**Formatting with Black:**
```bash
poetry run black src tests
```

**Import sorting with isort:**
```bash
poetry run isort src tests
```

**Linting with flake8:**
```bash
poetry run flake8 src tests
```

**Type checking with mypy:**
```bash
poetry run mypy src
```

**Run all checks at once:**
```bash
poetry run black src tests && \
poetry run isort src tests && \
poetry run flake8 src tests && \
poetry run mypy src
```

### Test-Driven Development (TDD)

We follow TDD practices strictly:

1. **Write tests first** for new features
2. **Run tests** to see them fail
3. **Implement feature** to make tests pass
4. **Refactor** as needed while keeping tests passing
5. **Commit** with tests included

**Running tests:**
```bash
# Run all tests
poetry run pytest

# Run with verbose output
poetry run pytest -v

# Run specific test file
poetry run pytest tests/test_quality_checker.py -v

# Run with coverage report
poetry run pytest --cov=src --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Git Workflow

1. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make changes** following TDD
3. **Commit frequently** with clear messages
4. **Push to remote** when ready
5. **Create Pull Request** with description

**Commit message format:**
```
[TYPE] Brief description

Longer explanation if needed. Reference issues (#123).

Tests added/modified: tests/test_*.py
```

**Commit types:** `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

## Adding Dependencies

**Add production dependency:**
```bash
poetry add package-name
```

**Add development dependency:**
```bash
poetry add --group dev package-name
```

**Update lock file:**
```bash
poetry update
```

**View installed packages:**
```bash
poetry show
poetry show --tree
```

## Project Structure

```
src/
├── __init__.py
├── downloader.py         # ClinVar data download
├── quality_checker.py    # Quality metrics calculation
├── quilt_packager.py     # Quilt package operations
├── drift_detector.py     # Version comparison
└── visualizer.py         # Charts and reports

tests/
├── __init__.py
├── test_downloader.py
├── test_quality_checker.py
├── test_quilt_packager.py
├── test_drift_detector.py
└── test_visualizer.py

scripts/
├── run_pipeline.py       # Main orchestration
└── analyze_history.py    # Historical analysis

config/
└── config.yaml.template  # Configuration template

docs/
└── *.md                  # Documentation files
```

## Common Tasks

### Running the full pipeline

```bash
# Phase 1 (basic functionality)
poetry run python scripts/run_pipeline.py --phase 1

# With specific config
poetry run python scripts/run_pipeline.py --config config/my-config.yaml
```

### Debugging

Enable debug logging:
```bash
# In config.yaml, set:
logging:
  level: "DEBUG"
```

Or pass via CLI:
```bash
poetry run python scripts/run_pipeline.py --log-level DEBUG
```

### Accessing the Python REPL

```bash
poetry run ipython

# Then in IPython:
from src.quality_checker import QualityChecker
qc = QualityChecker()
```

## Documentation

- Update [CHANGELOG.md](../CHANGELOG.md) for all changes
- Add docstrings to all functions and classes
- Update relevant docs in the `docs/` folder
- Keep [README.md](../README.md) concise; move details to `docs/`

## Continuous Integration

The project uses GitHub Actions (see `.github/workflows/ci.yml.template`):

- Runs tests on all pushes to `main` and `develop`
- Tests against Python 3.8, 3.9, 3.10, 3.11
- Checks code formatting and linting
- Uploads coverage reports

Enable this by:
1. Copy `.github/workflows/ci.yml.template` → `.github/workflows/ci.yml`
2. Push to GitHub

## Troubleshooting

**Poetry lock issues:**
```bash
poetry lock --no-update
poetry install
```

**Virtual environment issues:**
```bash
poetry env remove python3.x
poetry install
```

**Dependency conflicts:**
```bash
poetry update --dry-run  # See what would change
poetry update            # Apply updates
```

**Tests failing locally but passing in CI:**
```bash
poetry run pytest -v  # More verbose output
poetry show --tree    # Check dependency versions
```

## Performance Tips

- Use `--cov-report=term-skip-covered` to skip 100% covered files in coverage report
- Use `pytest -k "pattern"` to run specific tests
- Use `pytest --lf` to run last failing tests
- Use `pytest --ff` to run failed tests first, then others

## Resources

- [Poetry Documentation](https://python-poetry.org/docs/)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Code Formatter](https://black.readthedocs.io/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/example/index.html)
