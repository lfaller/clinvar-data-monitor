#!/usr/bin/env python
"""ClinVar Data Quality Monitor - Demo Pipeline with Sample Data.

This script runs the pipeline using sample data instead of downloading
the full 3.7GB dataset. Perfect for testing and demonstrations.

Usage:
    poetry run python scripts/run_demo_pipeline.py [--config CONFIG_FILE]
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from src.quality_checker import QualityChecker
from src.quilt_packager import QuiltPackager


class ClinVarDemoPipeline:
    """Run demo pipeline with sample data."""

    def __init__(self, config_file: str = "config/demo_config.yaml"):
        """Initialize the demo pipeline.

        Args:
            config_file: Path to configuration file
        """
        self.config = self.load_config(config_file)
        self.quality_checker = None
        self.packager = None
        self.sample_data_file = Path("data/sample_variant_summary.txt")

        self.setup_logging()
        self.validate_sample_data()

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
            log_file = Path(log_dir) / f"demo_pipeline_{timestamp}.log"

            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(logging.Formatter(log_format))
            logging.getLogger().addHandler(file_handler)

        self.logger = logging.getLogger(__name__)

    def validate_sample_data(self) -> None:
        """Validate that sample data file exists."""
        if not self.sample_data_file.exists():
            self.logger.error(f"Sample data file not found: {self.sample_data_file}")
            raise FileNotFoundError(f"Sample data file not found: {self.sample_data_file}")
        self.logger.info(f"Sample data file found: {self.sample_data_file}")

    def load_config(self, config_file: str) -> dict:
        """Load configuration from YAML file.

        Args:
            config_file: Path to configuration file

        Returns:
            Configuration dictionary
        """
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")

        with open(config_path) as f:
            config = yaml.safe_load(f)
        return config

    def initialize_modules(self) -> None:
        """Initialize quality checker and packager modules."""
        self.logger.info("Initializing pipeline modules")

        self.quality_checker = QualityChecker(self.config)
        self.packager = QuiltPackager(self.config)

        self.logger.info("All modules initialized successfully")

    def log_pipeline_start(self) -> None:
        """Log pipeline start."""
        self.logger.info("=" * 80)
        self.logger.info("ClinVar Demo Pipeline Started (Using Sample Data)")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info(f"Sample data file: {self.sample_data_file}")
        self.logger.info("=" * 80)

    def log_pipeline_end(self, success: bool) -> None:
        """Log pipeline end.

        Args:
            success: Whether pipeline completed successfully
        """
        status = "COMPLETED SUCCESSFULLY" if success else "FAILED"
        self.logger.info("=" * 80)
        self.logger.info(f"ClinVar Demo Pipeline {status}")
        self.logger.info(f"Timestamp: {datetime.now().isoformat()}")
        self.logger.info("=" * 80)

    def assess_quality(self) -> dict:
        """Assess data quality using sample data.

        Returns:
            Quality report dictionary
        """
        self.logger.info("Step 1: Assessing data quality")
        try:
            report = self.quality_checker.assess_quality(self.sample_data_file)
            self.logger.info("Quality assessment completed successfully")
            return report
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            raise

    def create_package(self, quality_report: dict) -> None:
        """Create Quilt package with sample data and quality report.

        Args:
            quality_report: Quality report dictionary
        """
        self.logger.info("Step 2: Creating Quilt package and pushing to registry")
        try:
            self.packager.full_package_workflow(
                self.sample_data_file,
                quality_report,
            )
            self.logger.info("Package creation and push completed successfully")
        except Exception as e:
            self.logger.error(f"Package creation failed: {e}")
            raise

    def run(self) -> bool:
        """Execute the demo pipeline.

        Returns:
            True if successful, False otherwise
        """
        try:
            self.log_pipeline_start()
            self.initialize_modules()

            # Run quality assessment
            quality_report = self.assess_quality()
            self.logger.info(f"Quality Score: {quality_report.get('quality_score', 'N/A')}")

            # Create and push package
            self.create_package(quality_report)

            self.log_pipeline_end(True)
            return True

        except Exception as e:
            self.logger.error(f"Pipeline failed: {e}", exc_info=True)
            self.log_pipeline_end(False)
            return False


def main():
    """Run the demo pipeline."""
    parser = argparse.ArgumentParser(
        description="Run ClinVar demo pipeline with sample data"
    )
    parser.add_argument(
        "--config",
        default="config/demo_config.yaml",
        help="Path to configuration file (default: config/demo_config.yaml)",
    )
    args = parser.parse_args()

    try:
        pipeline = ClinVarDemoPipeline(config_file=args.config)
        success = pipeline.run()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
