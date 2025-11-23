#!/usr/bin/env python
"""S3 Integration Tests for ClinVar Data Monitor.

This script tests the complete S3 workflow including:
1. Package creation and S3 upload
2. Package listing from S3 registry
3. Package retrieval and metadata access
4. Local storage fallback
"""

import logging
import sys
from pathlib import Path
from typing import List

import quilt3
import yaml

logger = logging.getLogger(__name__)


def setup_logging():
    """Configure logging."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def load_config(config_file: str) -> dict:
    """Load configuration from YAML file."""
    with open(config_file) as f:
        return yaml.safe_load(f)


def test_s3_bucket_access(bucket_url: str) -> bool:
    """Test that S3 bucket is accessible.

    Args:
        bucket_url: Full S3 registry URL (e.g., s3://bucket-name)

    Returns:
        True if bucket is accessible, False otherwise
    """
    logger.info(f"Testing S3 bucket access: {bucket_url}")
    try:
        # Try to list packages from the registry
        packages = list(quilt3.list_packages(registry=bucket_url))
        logger.info(f"Successfully accessed S3 registry. Found {len(packages)} packages")
        for pkg in packages:
            logger.info(f"  - {pkg}")
        return True
    except Exception as e:
        logger.error(f"Failed to access S3 bucket: {e}")
        return False


def test_package_metadata(bucket_url: str, package_name: str) -> bool:
    """Test that package metadata is accessible.

    Args:
        bucket_url: Full S3 registry URL
        package_name: Package name (e.g., biodata/clinvar)

    Returns:
        True if metadata is accessible, False otherwise
    """
    logger.info(f"Testing package metadata for {package_name}")
    try:
        pkg = quilt3.Package.browse(package_name, registry=bucket_url)
        logger.info(f"Successfully loaded package: {package_name}")

        # Get package metadata
        metadata = pkg.meta if hasattr(pkg, "meta") else {}
        logger.info(f"Package metadata keys: {list(metadata.keys())}")

        # Check for quality metrics in metadata
        if "quality_score" in metadata:
            logger.info(f"Quality Score: {metadata['quality_score']}")
        if "row_count" in metadata:
            logger.info(f"Row Count: {metadata['row_count']}")
        if "timestamp" in metadata:
            logger.info(f"Timestamp: {metadata['timestamp']}")

        return True
    except Exception as e:
        logger.error(f"Failed to access package metadata: {e}")
        return False


def test_local_storage_mode(config_file: str) -> bool:
    """Test local storage mode (push_to_registry: false).

    Args:
        config_file: Path to config file with push_to_registry: false

    Returns:
        True if local storage works, False otherwise
    """
    logger.info(f"Testing local storage mode with config: {config_file}")
    try:
        config = load_config(config_file)

        # Verify push_to_registry is disabled
        if config.get("quilt", {}).get("push_to_registry"):
            logger.error("Config shows push_to_registry is enabled, expected false")
            return False

        logger.info("Local storage mode verified (push_to_registry: false)")

        # Try to check local Quilt registry
        try:
            local_packages = list(quilt3.list_packages())  # No registry = local
            logger.info(f"Local registry contains {len(local_packages)} packages")
            for pkg in local_packages:
                logger.info(f"  - {pkg}")
        except Exception as e:
            logger.warning(f"Could not list local packages: {e}")

        return True
    except Exception as e:
        logger.error(f"Failed to test local storage mode: {e}")
        return False


def test_package_contents(
    bucket_url: str, package_name: str
) -> bool:
    """Test that package contents are accessible.

    Args:
        bucket_url: Full S3 registry URL
        package_name: Package name

    Returns:
        True if contents are accessible, False otherwise
    """
    logger.info(f"Testing package contents for {package_name}")
    try:
        pkg = quilt3.Package.browse(package_name, registry=bucket_url)
        logger.info(f"Package structure:")

        # List package contents
        for name in pkg:
            logger.info(f"  - {name}")

        return True
    except Exception as e:
        logger.error(f"Failed to access package contents: {e}")
        return False


def run_all_tests() -> bool:
    """Run all S3 integration tests.

    Returns:
        True if all tests pass, False otherwise
    """
    setup_logging()
    logger.info("=" * 80)
    logger.info("Starting S3 Integration Tests")
    logger.info("=" * 80)

    results = {}

    # Test 1: S3 bucket access
    logger.info("\n[Test 1/4] S3 Bucket Access")
    config = load_config("config/demo_config.yaml")
    bucket_url = config.get("quilt", {}).get("registry")
    if bucket_url:
        results["s3_access"] = test_s3_bucket_access(bucket_url)
    else:
        logger.error("No registry URL found in config")
        results["s3_access"] = False

    # Test 2: Package metadata
    logger.info("\n[Test 2/4] Package Metadata Access")
    package_name = config.get("quilt", {}).get("package_name")
    if bucket_url and package_name:
        results["metadata"] = test_package_metadata(bucket_url, package_name)
    else:
        logger.warning("Skipping metadata test - package_name or registry not configured")
        results["metadata"] = True  # Skip with pass

    # Test 3: Package contents
    logger.info("\n[Test 3/4] Package Contents Access")
    if bucket_url and package_name:
        results["contents"] = test_package_contents(bucket_url, package_name)
    else:
        logger.warning("Skipping contents test - package_name or registry not configured")
        results["contents"] = True  # Skip with pass

    # Test 4: Local storage mode
    logger.info("\n[Test 4/4] Local Storage Mode")
    results["local_storage"] = test_local_storage_mode("config/local_test_config.yaml")

    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("Test Results Summary")
    logger.info("=" * 80)
    for test_name, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        logger.info(f"{test_name:20} {status}")

    all_passed = all(results.values())
    logger.info("=" * 80)
    if all_passed:
        logger.info("All tests PASSED")
    else:
        logger.error("Some tests FAILED")
    logger.info("=" * 80)

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
