# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [ARCHIVED] - 2025-11-24

### Status: Project Archived

This project is now archived as a historical reference implementation. See [FINAL_STATUS.md](FINAL_STATUS.md) for complete details.

**Why:** The ClinVar dataset (4 GB per release) makes ongoing S3 monitoring cost-prohibitive for a demonstration project. The team has pivoted to [climate-data-monitor](https://github.com/linafaller/climate-data-monitor), which applies the same architectural patterns (Quilt versioning, quality assessment, drift detection) to a smaller dataset (100-200 MB per release).

**What's Preserved:** Phases 1-2 are fully implemented and tested (81 tests passing). All code, architecture, and patterns are available for reference or adaptation to other datasets.

## [0.2.1] - 2025-11-23

### Added

#### Testing & Development
- **Demo Pipeline** (`scripts/run_demo_pipeline.py`)
  - Run full pipeline workflow with sample data (914 bytes) instead of 3.7GB download
  - Configurable storage backends via `--config` argument
  - Supports both S3 and local storage modes
  - Perfect for rapid development and CI/CD testing

- **S3 Integration Tests** (`scripts/test_s3_integration.py`)
  - Comprehensive integration test suite for S3 backend
  - 4 test suites: bucket access, metadata retrieval, package contents, local storage fallback
  - Exit codes: 0 for success, 1 for failure
  - Enables validation of S3 configuration and registry connectivity

- **Test Configurations**
  - `config/demo_config.yaml`: Demo pipeline with S3 storage
  - `config/local_test_config.yaml`: Demo pipeline with local storage fallback

### Benefits
- Develop and test without downloading large datasets
- Validate S3 setup without waiting for 3.7GB uploads
- Test local storage fallback (offline mode)
- Rapid iteration on pipeline features
- All features tested with sample data in seconds

## [0.2.0] - Phase 1: Foundation - 2025-11-21

### Added

#### Core Modules
- **ClinVarDownloader** (`src/downloader.py`)
  - Download ClinVar data from NCBI FTP with retry logic (exponential backoff)
  - MD5 checksum validation
  - Gzip decompression with automatic filename extraction
  - Full `download_and_verify()` workflow
  - Comprehensive error handling and logging
  - Tests: 16 passing tests

- **QualityChecker** (`src/quality_checker.py`)
  - Load variant data from TSV files
  - Calculate basic metrics: row/column counts, null percentages, duplicates
  - Calculate ClinVar-specific metrics: clinical significance distribution, review status
  - Count conflicting interpretations
  - Generate quality reports with JSON serialization
  - Quality scoring algorithm (0-100 scale) with weighted factors
  - Save reports with timestamp-based filenames
  - Tests: 24 passing tests

- **QuiltPackager** (`src/quilt_packager.py`)
  - Create Quilt packages locally
  - Add data files to packages
  - Attach quality reports as metadata
  - Set searchable metadata tags
  - Validate data files and quality reports
  - Push packages to S3 registries (with configurable toggle)
  - Parse package names and manage namespaces
  - Extract version information from filenames
  - Tests: 25 passing tests

- **ClinVarPipeline** (`scripts/run_pipeline.py`)
  - Orchestrate complete workflow: download → assess → package
  - Load configuration from YAML files
  - Setup logging with file and console handlers
  - Initialize all modules
  - Error handling with graceful failures
  - Pipeline execution summary reporting
  - Command-line interface with config and log-level options
  - Tests: 16 passing tests

#### Documentation
- Comprehensive development guide (`docs/development.md`)
- Architecture documentation (`docs/architecture.md`)
- Configuration guide (`docs/configuration.md`)
- Documentation index (`docs/README.md`)

#### Testing Infrastructure
- 81 total tests (all passing)
- TDD approach with tests written first
- Comprehensive mocking for external dependencies
- Coverage reporting with pytest-cov
- Fixtures for reusable test data

### Changed
- Updated pyproject.toml with relaxed quilt3 version constraints (>=5.0)
- Updated Python requirement to ^3.8.1 for flake8 compatibility
- Enhanced README with Poetry-specific instructions

### Fixed
- DateTime deprecation warnings (use timezone-aware UTC)
- Package naming and namespace parsing
- Quality score calculation bounds (0-100)

## [0.1.0] - 2025-11-21

### Added
- Initial project scaffolding
- Poetry configuration with core dependencies
- Comprehensive .gitignore for Python projects
- Environment configuration templates
- README with setup instructions

[Unreleased]: https://github.com/linafaller/clinvar-data-monitor/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/linafaller/clinvar-data-monitor/releases/tag/v0.1.0
