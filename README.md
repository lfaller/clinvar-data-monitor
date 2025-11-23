# ClinVar Data Quality Monitor

An automated data quality monitoring system for ClinVar genetic variant data using Quilt for versioning, with the ability to track quality metrics over time, detect data drift, and enable quick rollback to previous versions.

## Quick Start

### Prerequisites

- Python 3.8 or higher
- [Poetry](https://python-poetry.org/) (for dependency management)
- AWS account with S3 access
- Git (for version control)

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd clinvar-data-monitor
   ```

2. **Install Poetry** (if not already installed)
   ```bash
   curl -sSL https://install.python-poetry.org | python3 -
   ```

3. **Install dependencies**
   ```bash
   poetry install
   ```

   For development (includes testing, linting, formatting tools):
   ```bash
   poetry install --with dev
   ```

4. **Activate the virtual environment**
   ```bash
   poetry shell
   ```
   Or prefix commands with `poetry run`:
   ```bash
   poetry run python scripts/run_pipeline.py
   ```

5. **Configure AWS credentials**
   ```bash
   aws configure
   ```
   This will prompt you for:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region (us-east-1 recommended)
   - Default output format (json recommended)

6. **Set up configuration**
   ```bash
   # Copy the template configuration
   cp config/config.yaml.template config/config.yaml

   # Copy the environment template
   cp .env.template .env

   # Edit both files with your specific settings
   nano config/config.yaml
   nano .env
   ```

7. **Create S3 bucket** (if not already created)
   ```bash
   aws s3 mb s3://your-clinvar-registry

   # Enable versioning (recommended)
   aws s3api put-bucket-versioning \
       --bucket your-clinvar-registry \
       --versioning-configuration Status=Enabled
   ```

## Project Structure

```
clinvar-data-monitor/
├── src/                          # Main source code
│   ├── __init__.py
│   ├── downloader.py             # Data ingestion from ClinVar FTP
│   ├── quality_checker.py         # Quality assessment engine
│   ├── quilt_packager.py          # Quilt packaging operations
│   ├── drift_detector.py          # Version comparison & drift detection
│   └── visualizer.py              # Visualization & reporting
├── config/
│   └── config.yaml.template       # Configuration template
├── scripts/
│   ├── run_pipeline.py            # Main orchestration script
│   └── analyze_history.py         # Historical analysis & visualization
├── tests/
│   └── test_quality_checker.py    # Unit tests
├── notebooks/
│   └── exploration.ipynb          # Jupyter notebooks for analysis
├── data/                          # Data directory (git-ignored)
│   └── downloads/                 # ClinVar downloads
├── output/                        # Output directory (git-ignored)
│   └── quality_reports/           # Quality reports
├── logs/                          # Logs directory (git-ignored)
├── pyproject.toml                 # Poetry configuration & dependencies
├── .github/
│   └── workflows/
│       └── ci.yml.template        # CI/CD workflow template
├── README.md                      # This file
├── .gitignore                     # Git ignore patterns
├── .env.template                  # Environment variables template
└── roadmap.md                     # Project roadmap & planning
```

## Configuration

### config.yaml

Edit `config/config.yaml` to customize:
- ClinVar FTP source URLs
- Data filtering options (chromosomes, clinical significance)
- Quilt S3 bucket settings
- Quality assessment thresholds
- Alert settings (email, Slack)
- Logging configuration

### .env

Set environment variables in `.env`:
- AWS credentials
- SMTP settings (for email alerts)
- Slack webhook URL (for notifications)

## Development

### Testing with Sample Data

For quick testing without downloading actual ClinVar data or requiring AWS credentials, use the built-in sample data demonstration:

#### Quick Module Test

Test all modules with sample data in a few seconds:

```bash
poetry run python scripts/test_modules.py
```

This script demonstrates:
- **QualityChecker**: Loading variant data and calculating quality metrics
- **QuiltPackager**: Package initialization and metadata generation
- Sample output: Quality score, clinical significance distribution, review status breakdown

Example output:
```
================================================================================
ClinVar Data Quality Monitor - Module Demonstration
================================================================================

1. LOADING SAMPLE DATA
✓ Sample data file found: data/sample_variant_summary.txt

2. QUALITY ASSESSMENT
✓ QualityChecker initialized
✓ Loaded 10 variants with 8 columns
✓ Quality report generated

Quality Report Summary:
  - Quality Score: 62.6/100
  - Row Count: 10
  - Column Count: 8
  - Null Percentage: 3.8%
  - Duplicate Count: 0
  - Conflicting Interpretations: 6
  - 4-Star Percentage: 30.0%

3. QUILT PACKAGING
✓ QuiltPackager initialized
✓ Quality report validation: True

✅ All modules working correctly!
```

The sample quality report is saved to: `output/quality_reports/quality_report_YYYY-MM-DD.json`

#### View the Generated Report

```bash
# See the latest quality report in JSON format
cat output/quality_reports/quality_report_*.json | python -m json.tool
```

#### Sample Data & Package Storage

**Sample Data Location**: `data/sample_variant_summary.txt`

The sample dataset contains:
- 10 realistic ClinVar variants
- Full set of columns: VariationID, Type, Locations, Protein Change, Symptom(s), ClinicalSignificance, ReviewStatus, ConflictingInterpretations
- Mix of pathogenic/benign classifications
- Varying review status (1-4 stars)

**Quilt Package Storage**:
- **Local (testing)**: When `push_to_registry: false`, packages are built locally in Quilt's registry
  - Access via: `quilt3.Package.browse("namespace/package_name")`
  - Storage: Managed by Quilt internally

- **S3 Registry (production)**: When `push_to_registry: true` and AWS credentials are configured
  - Pushed to S3 bucket specified in config
  - Requires AWS credentials (Access Key ID + Secret Key)
  - No credentials needed for local testing mode

### Running Tests

All tests use mocking to avoid external dependencies:

```bash
# Run all tests with coverage
poetry run pytest

# Run specific test file
poetry run pytest tests/test_quality_checker.py -v

# Run with coverage report
poetry run pytest --cov=src --cov-report=html
```

**Current Test Coverage:**
- 81 total tests (all passing)
- ClinVarDownloader: 16 tests
- QualityChecker: 24 tests
- QuiltPackager: 25 tests
- ClinVarPipeline: 16 tests

All tests use mocking for:
- NCBI FTP downloads
- S3 operations
- Quilt package operations

No AWS credentials or actual network access required.

### Running the Pipeline

```bash
# Phase 1: Download and assess quality
poetry run python scripts/run_pipeline.py --phase 1

# Phase 2: Analyze drift and enhanced metrics
poetry run python scripts/run_pipeline.py --phase 2

# Phase 3: Full automation with visualization
poetry run python scripts/run_pipeline.py --phase 3
```

For testing the pipeline with sample data (without actual downloads):

```bash
# Use the test configuration
poetry run python scripts/run_pipeline.py --config config/test_config.yaml
```

Note: This requires sample data to be present in `data/`

### Code Quality

```bash
# Format code with black
poetry run black src tests

# Check formatting
poetry run black --check src tests

# Sort imports
poetry run isort src tests

# Lint with flake8
poetry run flake8 src tests

# Type checking
poetry run mypy src
```

### Using Poetry

Common Poetry commands:

```bash
# Add a new dependency
poetry add package-name

# Add a development dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# View installed packages
poetry show

# Run a Python script
poetry run python script.py

# Activate virtual environment
poetry shell

# View project info
poetry info
```

## Features

### Phase 1: Foundation
- Download ClinVar data with integrity validation
- Calculate basic quality metrics
- Package data with Quilt
- Push to S3 registry

### Phase 2: ClinVar-Specific
- Enhanced biological metrics
- Drift detection between versions
- Improved quality scoring
- Multiple filtered package variants

### Phase 3: Automation & Monitoring
- Automated orchestration
- Scheduled execution (cron/Lambda)
- Quality trend visualization
- Alert system with thresholds

## Resources

- [Quilt Documentation](https://docs.quilt.bio/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [ClinVar FTP](https://ftp.ncbi.nlm.nih.gov/pub/clinvar/)
- [ClinVar Data Dictionary](https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/)

## License

[Add your license here]

## Support

For issues, questions, or contributions, please open an issue on GitHub.

---

For detailed project planning and implementation roadmap, see [roadmap.md](roadmap.md).
