#!/usr/bin/env python
"""ClinVar Data Quality Monitor Pipeline Orchestrator.

This script coordinates the complete data quality monitoring workflow:
1. Download latest ClinVar data
2. Assess data quality
3. Create versioned Quilt packages
4. Push to S3 registry
"""

import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from src.downloader import ClinVarDownloader
from src.quality_checker import QualityChecker
from src.quilt_packager import QuiltPackager


class ClinVarPipeline:
    """Orchestrate the complete ClinVar data quality monitoring pipeline."""

    def __init__(self, config: dict):
        """Initialize the pipeline with configuration.

        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.downloader = None
        self.quality_checker = None
        self.packager = None

        self.setup_logging()
        self.create_directories()

    def setup_logging(self) -> None:
        """Configure logging for the pipeline."""
        log_config = self.config.get("logging", {})
        log_level = log_config.get("level", "INFO")
        log_dir = log_config.get("log_dir", "logs")

        # Create log directory
        Path(log_dir).mkdir(parents=True, exist_ok=True)

        # Configure logging
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
        )

        # Add file handler if enabled
        if log_config.get("file_logging", True):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_file = Path(log_dir) / f"pipeline_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)

        self.logger = logging.getLogger(__name__)

    def create_directories(self) -> None:
        """Create required directories from configuration."""
        dirs = [
            self.config["clinvar"]["download_dir"],
            self.config["quality"]["output_dir"],
            self.config["logging"]["log_dir"],
        ]

        for directory in dirs:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def initialize_modules(self) -> None:
        """Initialize all pipeline modules."""
        self.logger.info("Initializing pipeline modules")

        self.downloader = ClinVarDownloader(self.config)
        self.quality_checker = QualityChecker(self.config)
        self.packager = QuiltPackager(self.config)

        self.logger.info("All modules initialized successfully")

    def log_pipeline_start(self) -> None:
        """Log pipeline start."""
        self.logger.info("=" * 80)
        self.logger.info("ClinVar Data Quality Monitor Pipeline Started")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info("=" * 80)

    def log_pipeline_end(self, success: bool) -> None:
        """Log pipeline end.

        Args:
            success: Whether pipeline completed successfully
        """
        status = "COMPLETED" if success else "FAILED"
        self.logger.info("=" * 80)
        self.logger.info(f"ClinVar Pipeline {status}")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info("=" * 80)

    def download_data(self) -> Path:
        """Execute data download step.

        Returns:
            Path to downloaded and decompressed data file

        Raises:
            Exception: If download fails
        """
        self.logger.info("Step 1: Downloading ClinVar data")

        try:
            data_file = self.downloader.download_and_verify()
            self.logger.info(f"Data download successful: {data_file}")
            return data_file

        except Exception as e:
            self.logger.error(f"Data download failed: {e}")
            raise

    def assess_quality(self, data_file: Path) -> dict:
        """Execute quality assessment step.

        Args:
            data_file: Path to variant data file

        Returns:
            Quality metrics report

        Raises:
            Exception: If quality assessment fails
        """
        self.logger.info("Step 2: Assessing data quality")

        try:
            report = self.quality_checker.assess_quality(data_file)
            self.logger.info(
                f"Quality assessment complete. Quality score: {report['quality_score']}"
            )
            return report

        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            raise

    def create_package(self, data_file: Path, quality_report: dict) -> bool:
        """Execute package creation and push step.

        Args:
            data_file: Path to variant data file
            quality_report: Quality metrics report

        Returns:
            True if packaging successful

        Raises:
            Exception: If packaging fails
        """
        self.logger.info("Step 3: Creating Quilt package and pushing to registry")

        try:
            self.packager.full_package_workflow(data_file, quality_report)
            self.logger.info("Package creation and push successful")
            return True

        except Exception as e:
            self.logger.error(f"Package creation failed: {e}")
            raise

    def generate_summary(self, results: dict) -> str:
        """Generate pipeline execution summary.

        Args:
            results: Dictionary with pipeline results

        Returns:
            Summary string
        """
        summary = [
            "\n" + "=" * 80,
            "PIPELINE EXECUTION SUMMARY",
            "=" * 80,
        ]

        for key, value in results.items():
            summary.append(f"{key}: {value}")

        summary.append("=" * 80)
        return "\n".join(summary)

    def run(self) -> bool:
        """Execute the complete pipeline.

        Returns:
            True if pipeline completed successfully

        Raises:
            Exception: If any step fails
        """
        self.log_pipeline_start()
        results = {}

        try:
            # Initialize modules
            self.initialize_modules()

            # Step 1: Download data
            data_file = self.download_data()
            results["download_status"] = "success"

            # Step 2: Assess quality
            quality_report = self.assess_quality(data_file)
            results["quality_status"] = "success"
            results["quality_score"] = quality_report.get("quality_score")

            # Step 3: Create package and push to registry
            self.create_package(data_file, quality_report)
            results["package_status"] = "success"

            # Log success
            self.logger.info(self.generate_summary(results))
            self.log_pipeline_end(True)

            return True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}")
            results["error"] = str(e)
            self.logger.error(self.generate_summary(results))
            self.log_pipeline_end(False)
            return False


def load_config(config_file: Path) -> dict:
    """Load configuration from YAML file.

    Args:
        config_file: Path to configuration file

    Returns:
        Configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        yaml.YAMLError: If YAML is invalid
    """
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_file}")

    with open(config_file) as f:
        config = yaml.safe_load(f)

    return config


def main():
    """Main entry point for pipeline execution."""
    parser = argparse.ArgumentParser(
        description="ClinVar Data Quality Monitor Pipeline"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/config.yaml"),
        help="Path to configuration file",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default="INFO",
        help="Logging level",
    )

    args = parser.parse_args()

    try:
        # Load configuration
        config = load_config(args.config)

        # Override log level if provided
        if args.log_level:
            config.setdefault("logging", {})["level"] = args.log_level

        # Run pipeline
        pipeline = ClinVarPipeline(config)
        success = pipeline.run()

        # Exit with appropriate code
        sys.exit(0 if success else 1)

    except Exception as e:
        logging.error(f"Failed to run pipeline: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
