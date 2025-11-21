"""Quilt packaging module for versioning and S3 registry integration.

This module handles creating Quilt packages, attaching metadata and quality reports,
and pushing versioned data to S3 registries.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import quilt3

logger = logging.getLogger(__name__)


class QuiltPackager:
    """Create and manage Quilt packages for ClinVar data."""

    def __init__(self, config: dict):
        """Initialize the Quilt packager with configuration.

        Args:
            config: Configuration dictionary with quilt section containing:
                - bucket: S3 bucket for registry
                - package_name: Full package name (namespace/name)
                - registry: S3 registry URL
                - push_to_registry: Whether to push packages
        """
        self.config = config
        quilt_config = config["quilt"]

        self.bucket = quilt_config["bucket"]
        self.registry = quilt_config["registry"]
        self.push_enabled = quilt_config.get("push_to_registry", False)

        # Parse package name
        package_full_name = quilt_config["package_name"]
        parts = package_full_name.split("/")
        if len(parts) >= 2:
            self.namespace = parts[0]
            self.package = parts[1]
        else:
            self.namespace = "biodata"
            self.package = package_full_name

        self.package_name = f"{self.namespace}/{self.package}"

        logger.info(f"Quilt packager initialized with package: {self.package_name}")

    def create_package(self, data_file: Optional[Path] = None) -> quilt3.Package:
        """Create a new Quilt package.

        Args:
            data_file: Optional path to initial data file to add

        Returns:
            Quilt Package object
        """
        logger.info(f"Creating Quilt package: {self.package_name}")

        pkg = quilt3.Package()

        if data_file:
            self.add_data_file(pkg, data_file)

        logger.info("Package created successfully")
        return pkg

    def add_data_file(self, pkg: quilt3.Package, data_file: Path) -> quilt3.Package:
        """Add data file to Quilt package.

        Args:
            pkg: Quilt Package object
            data_file: Path to data file

        Returns:
            Updated Quilt Package object

        Raises:
            FileNotFoundError: If data file doesn't exist
        """
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {data_file}")

        logger.info(f"Adding data file to package: {data_file}")

        # Add file to package
        pkg.set(data_file.name, data_file)

        logger.info(f"Data file added: {data_file.name}")
        return pkg

    def add_quality_report(
        self, pkg: quilt3.Package, quality_report: Dict[str, Any]
    ) -> quilt3.Package:
        """Add quality report as package metadata.

        Args:
            pkg: Quilt Package object
            quality_report: Quality metrics report dictionary

        Returns:
            Updated Quilt Package object
        """
        logger.info("Adding quality report to package metadata")

        # Generate metadata from report
        metadata = self._generate_metadata_from_report(quality_report)

        # Set as package metadata
        pkg.set_meta(metadata)

        logger.info("Quality report metadata added")
        return pkg

    def set_metadata(
        self, pkg: quilt3.Package, metadata: Dict[str, Any]
    ) -> quilt3.Package:
        """Set custom metadata on package.

        Args:
            pkg: Quilt Package object
            metadata: Metadata dictionary

        Returns:
            Updated Quilt Package object
        """
        logger.info("Setting package metadata")

        pkg.set_meta(metadata)

        logger.info("Metadata set successfully")
        return pkg

    def push_to_registry(self, pkg: quilt3.Package) -> bool:
        """Push package to S3 registry.

        Args:
            pkg: Quilt Package object

        Returns:
            True if push was successful or skipped

        Raises:
            Exception: If push fails
        """
        if not self.push_enabled:
            logger.info("Push to registry is disabled in configuration")
            return True

        logger.info(f"Pushing package to registry: {self.registry}")

        try:
            # Push to S3 registry
            pkg.push(
                name=self.package_name,
                registry=self.registry,
                message=f"Automated ClinVar release {self.package_name}",
            )

            logger.info(f"Package successfully pushed to {self.registry}")
            return True

        except Exception as e:
            logger.error(f"Failed to push package to registry: {e}")
            raise

    def validate_data_file(self, data_file: Path) -> bool:
        """Validate data file exists and is readable.

        Args:
            data_file: Path to data file

        Returns:
            True if file is valid

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not data_file.exists():
            raise FileNotFoundError(f"Data file not found: {data_file}")

        if not data_file.is_file():
            raise ValueError(f"Path is not a file: {data_file}")

        logger.info(f"Data file validation passed: {data_file}")
        return True

    def validate_quality_report(self, report: Dict[str, Any]) -> bool:
        """Validate quality report has required fields.

        Args:
            report: Quality metrics report

        Returns:
            True if report is valid

        Raises:
            ValueError: If required fields are missing
        """
        required_fields = [
            "timestamp",
            "row_count",
            "column_count",
            "quality_score",
        ]

        missing_fields = [f for f in required_fields if f not in report]

        if missing_fields:
            raise ValueError(f"Quality report missing required fields: {missing_fields}")

        logger.info("Quality report validation passed")
        return True

    def get_registry_packages(self) -> List[Dict[str, Any]]:
        """Retrieve list of packages in registry.

        Returns:
            List of package metadata dictionaries
        """
        logger.info(f"Listing packages in registry: {self.registry}")

        try:
            packages = quilt3.list_packages(registry=self.registry)
            logger.info(f"Found {len(packages)} packages in registry")
            return packages

        except Exception as e:
            logger.warning(f"Could not list registry packages: {e}")
            return []

    def _generate_metadata_from_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Quilt package metadata from quality report.

        Args:
            report: Quality metrics report

        Returns:
            Metadata dictionary for Quilt package
        """
        metadata = {
            "timestamp": report.get("timestamp"),
            "quality_score": report.get("quality_score"),
            "row_count": report.get("row_count"),
            "column_count": report.get("column_count"),
            "null_percentage_avg": report.get("null_percentage_avg"),
            "duplicate_count": report.get("duplicate_count"),
            "conflicting_count": report.get("conflicting_count"),
            "four_star_percentage": report.get("four_star_percentage"),
        }

        # Add clinical significance distribution as tags
        clin_dist = report.get("clinical_significance_distribution", {})
        for significance, count in clin_dist.items():
            metadata[f"clin_sig_{significance.lower().replace(' ', '_')}"] = count

        # Add review status distribution
        review_dist = report.get("review_status_distribution", {})
        for status, count in review_dist.items():
            metadata[f"review_{status.lower().replace('-', '_')}"] = count

        logger.debug(f"Generated metadata with {len(metadata)} fields")
        return metadata

    def _extract_version_info(self, filename: str) -> str:
        """Extract version information from filename.

        Args:
            filename: Data filename

        Returns:
            Version string if found, None otherwise
        """
        # Try to extract date from filename (e.g., variant_summary_2025-11-21.txt.gz)
        import re

        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        if date_match:
            return date_match.group(1)

        return None

    def full_package_workflow(
        self, data_file: Path, quality_report: Dict[str, Any]
    ) -> bool:
        """Execute complete packaging workflow.

        This is the main entry point that coordinates:
        1. Validate inputs
        2. Create package
        3. Add data file
        4. Add quality metadata
        5. Push to registry

        Args:
            data_file: Path to variant data file
            quality_report: Quality metrics report

        Returns:
            True if workflow completed successfully

        Raises:
            Various exceptions if any step fails
        """
        logger.info("Starting full package workflow")

        # Validate inputs
        self.validate_data_file(data_file)
        self.validate_quality_report(quality_report)

        # Create package
        pkg = self.create_package()

        # Add data file
        pkg = self.add_data_file(pkg, data_file)

        # Add quality report metadata
        pkg = self.add_quality_report(pkg, quality_report)

        # Push to registry
        self.push_to_registry(pkg)

        logger.info("Full package workflow completed successfully")
        return True
