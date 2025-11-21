# Architecture

## System Overview

The ClinVar Data Quality Monitor is built as a modular pipeline with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│                     ClinVar FTP Server                       │
│              (Monthly variant_summary.txt.gz)                │
└─────────────────────┬───────────────────────────────────────┘
                      │ Download
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Data Ingestion Layer                        │
│  (src/downloader.py)                                        │
│  • Download latest ClinVar release                           │
│  • Validate file integrity (MD5 checksums)                   │
│  • Decompress and parse data                                 │
│  • Optional filtering/preprocessing                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               Quality Assessment Engine                      │
│  (src/quality_checker.py)                                   │
│  • Calculate basic quality metrics                           │
│  • Analyze ClinVar-specific metrics                         │
│  • Compare with previous versions (drift detection)         │
│  • Generate quality reports (JSON)                          │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                  Quilt Packaging Layer                       │
│  (src/quilt_packager.py)                                    │
│  • Create Quilt packages                                     │
│  • Attach quality reports as metadata                       │
│  • Set searchable metadata and tags                         │
│  • Push versioned packages to S3 registry                   │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    AWS S3 Registry                           │
│  • Versioned data packages                                   │
│  • Quality reports and metadata                             │
│  • Historical snapshots                                      │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                   Quilt Web Catalog                          │
│  • Browse versions and metadata                              │
│  • Search by quality metrics                                 │
│  • Visualize quality trends                                  │
│  • Download historical versions                              │
└─────────────────────────────────────────────────────────────┘
```

## Core Modules

### 1. Data Ingestion (`src/downloader.py`)

Handles downloading and validating ClinVar data from NCBI FTP servers.

**Key Functions:**
- `download_clinvar()` - Download latest ClinVar release
- `validate_checksum()` - Verify file integrity with MD5
- `decompress_data()` - Handle gzip decompression
- `parse_variant_summary()` - Parse TSV data into pandas DataFrame

**Responsibilities:**
- Reliable downloads with retry logic
- Data integrity validation
- Local caching to avoid redundant downloads

### 2. Quality Assessment (`src/quality_checker.py`)

Analyzes data quality and generates comprehensive reports.

**Key Functions:**
- `calculate_basic_metrics()` - Row/column counts, null percentages
- `calculate_clinvar_metrics()` - Domain-specific metrics
- `calculate_quality_score()` - Overall quality scoring
- `generate_report()` - Create JSON quality report

**Responsibilities:**
- Compute quality indicators
- Detect data issues and anomalies
- Track metrics for trend analysis

### 3. Quilt Packaging (`src/quilt_packager.py`)

Creates versioned packages and pushes to S3 registry.

**Key Functions:**
- `create_package()` - Initialize Quilt package
- `add_data_file()` - Add CSV/data to package
- `add_quality_report()` - Attach quality metadata
- `set_metadata()` - Set searchable tags and metadata
- `push_to_registry()` - Upload to S3

**Responsibilities:**
- Package creation and versioning
- Metadata management
- S3 registry integration

### 4. Drift Detection (`src/drift_detector.py`)

Compares current and previous versions to detect changes.

**Key Functions:**
- `detect_drift()` - Compare metrics between versions
- `identify_significant_changes()` - Flag anomalies
- `generate_drift_report()` - Create drift analysis

**Responsibilities:**
- Version-to-version comparison
- Anomaly detection
- Alert triggering

### 5. Visualization (`src/visualizer.py`)

Creates charts and reports for trend analysis.

**Key Functions:**
- `plot_quality_trends()` - Quality score over time
- `plot_metric_trends()` - Individual metric trends
- `generate_html_report()` - Export interactive reports

**Responsibilities:**
- Data visualization
- Report generation
- Historical analysis

## Orchestration

### Pipeline Script (`scripts/run_pipeline.py`)

Main entry point that coordinates all modules:

```
1. Load configuration
2. Initialize logger
3. Download ClinVar data
4. Validate checksums
5. Calculate quality metrics
6. Compare with previous version (drift detection)
7. Create Quilt package
8. Push to S3 registry
9. Generate reports
10. Send alerts if thresholds breached
```

### Analysis Script (`scripts/analyze_history.py`)

Retrieves and analyzes historical data:

```
1. List all versions in registry
2. Extract quality metrics from each version
3. Build time-series data
4. Detect trends and anomalies
5. Generate visualizations
6. Export reports
```

## Data Flow

### Typical Execution

```
User triggers pipeline
    ↓
Download ClinVar data (FTP)
    ↓
Validate integrity (MD5)
    ↓
Parse into DataFrame
    ↓
Calculate quality metrics
    ↓
Load previous version (if exists)
    ↓
Detect drift
    ↓
Create Quilt package
    ↓
Add data file
    ↓
Attach metadata & quality report
    ↓
Push to S3 registry
    ↓
Check thresholds
    ↓
Send alerts if needed
    ↓
Complete
```

## Configuration Management

Settings are managed through:

1. **YAML Config** (`config/config.yaml`)
   - ClinVar FTP URLs
   - S3 bucket and paths
   - Quality thresholds
   - Alert settings

2. **Environment Variables** (`.env`)
   - AWS credentials
   - SMTP/Slack credentials
   - Secrets

3. **Code Defaults**
   - Fallback values for all settings

## Error Handling

The system implements graceful error handling:

- **Retry Logic** - Downloads with exponential backoff
- **Validation** - Checksums, schema validation
- **Logging** - Comprehensive logs for debugging
- **Alerts** - Email/Slack notifications on failures
- **Idempotency** - Safe to re-run without side effects

## Dependencies

**Core Libraries:**
- `quilt3` - Package versioning and registry
- `pandas` - Data manipulation
- `requests` - HTTP downloads
- `boto3` - AWS S3 integration
- `pyyaml` - Configuration parsing
- `plotly` - Visualization

**Development:**
- `pytest` - Testing framework
- `black` - Code formatting
- `flake8` - Linting
- `mypy` - Type checking

## Security Considerations

- AWS credentials managed via environment variables
- No credentials in configuration files
- Checksum validation for all downloads
- Input validation for all user-provided data
- Secure defaults for all settings

## Scalability

Current implementation focuses on:
- Single monthly releases
- Filtering to manageable dataset sizes
- Local processing before S3 upload

Future enhancements may include:
- Parallel processing
- Incremental updates
- Distributed computing
- Cloud processing (Lambda, Fargate)
