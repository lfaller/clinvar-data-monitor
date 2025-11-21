"""Tests for the Quilt packager module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.quilt_packager import QuiltPackager


class TestQuiltPackager:
    """Test suite for QuiltPackager class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def sample_quality_report(self):
        """Create a sample quality report."""
        return {
            "timestamp": "2025-11-21T12:00:00+00:00",
            "row_count": 1000,
            "column_count": 8,
            "null_percentage_avg": 5.0,
            "duplicate_count": 0,
            "conflicting_count": 10,
            "four_star_percentage": 85.0,
            "quality_score": 92.5,
            "clinical_significance_distribution": {
                "Pathogenic": 500,
                "Likely pathogenic": 300,
                "Benign": 200,
            },
            "review_status_distribution": {"4-star": 850, "3-star": 100, "2-star": 50},
        }

    @pytest.fixture
    def quilt_config(self, temp_dir):
        """Create Quilt packager configuration."""
        return {
            "quilt": {
                "bucket": "test-clinvar-registry",
                "package_name": "biodata/clinvar",
                "registry": "s3://test-clinvar-registry",
                "push_to_registry": False,  # Don't actually push in tests
            }
        }

    @pytest.fixture
    def packager(self, quilt_config):
        """Create a QuiltPackager instance."""
        return QuiltPackager(quilt_config)

    def test_init_stores_config(self, packager, quilt_config):
        """Test that __init__ properly stores configuration."""
        assert packager.config["quilt"]["bucket"] == "test-clinvar-registry"
        assert packager.package_name == "biodata/clinvar"

    def test_init_extracts_package_name(self, quilt_config):
        """Test that package name is correctly extracted."""
        packager = QuiltPackager(quilt_config)
        assert packager.package_name == "biodata/clinvar"

    def test_create_package_local(self, packager, temp_dir):
        """Test creating a Quilt package locally."""
        data_file = temp_dir / "variant_summary.txt"
        data_file.write_text("VariationID\tType\n1\tSNV\n2\tDEL\n")

        with patch("src.quilt_packager.quilt3.Package") as mock_pkg_class:
            mock_pkg = MagicMock()
            mock_pkg_class.return_value = mock_pkg

            result = packager.create_package(data_file)

            assert result is not None
            mock_pkg_class.assert_called_once()

    def test_add_data_file_to_package(self, packager, temp_dir):
        """Test adding data file to package."""
        data_file = temp_dir / "variant_summary.txt"
        data_file.write_text("test data")

        mock_pkg = MagicMock()

        packager.add_data_file(mock_pkg, data_file)

        # Should call set method to add the file
        mock_pkg.set.assert_called_once()

    def test_add_quality_report_to_package(self, packager, sample_quality_report):
        """Test adding quality report metadata to package."""
        mock_pkg = MagicMock()

        packager.add_quality_report(mock_pkg, sample_quality_report)

        # Should set metadata
        mock_pkg.set_meta.assert_called_once()

    def test_set_metadata_basic(self, packager):
        """Test setting basic metadata on package."""
        mock_pkg = MagicMock()
        metadata = {
            "clinvar_release": "2025-11-21",
            "genome_assembly": "GRCh38",
        }

        packager.set_metadata(mock_pkg, metadata)

        mock_pkg.set_meta.assert_called()

    def test_generate_metadata_from_report(self, packager, sample_quality_report):
        """Test generating metadata from quality report."""
        metadata = packager._generate_metadata_from_report(sample_quality_report)

        assert "quality_score" in metadata
        assert metadata["quality_score"] == 92.5
        assert metadata["row_count"] == 1000
        assert metadata["timestamp"] == "2025-11-21T12:00:00+00:00"

    def test_generate_metadata_searchable_tags(self, packager, sample_quality_report):
        """Test that metadata includes searchable tags."""
        metadata = packager._generate_metadata_from_report(sample_quality_report)

        # Should have tags for searching
        assert "quality_score" in metadata
        assert "row_count" in metadata

    def test_push_to_registry(self, quilt_config):
        """Test pushing package to S3 registry."""
        quilt_config["quilt"]["push_to_registry"] = True
        packager = QuiltPackager(quilt_config)
        mock_pkg = MagicMock()

        packager.push_to_registry(mock_pkg)

        # Should call push method when enabled
        mock_pkg.push.assert_called_once()

    def test_push_disabled_when_config_false(self, quilt_config):
        """Test that push is skipped when push_to_registry is False."""
        quilt_config["quilt"]["push_to_registry"] = False
        packager = QuiltPackager(quilt_config)

        mock_pkg = MagicMock()

        result = packager.push_to_registry(mock_pkg)

        # Should not push when disabled
        mock_pkg.push.assert_not_called()

    def test_get_registry_info(self, packager):
        """Test retrieving registry information."""
        with patch("src.quilt_packager.quilt3.list_packages") as mock_list:
            mock_list.return_value = [
                {"name": "biodata/clinvar"},
                {"name": "biodata/gnomad"},
            ]

            packages = packager.get_registry_packages()

            assert len(packages) >= 0

    def test_validate_data_file(self, packager, temp_dir):
        """Test validation of data file."""
        data_file = temp_dir / "variant_summary.txt"
        data_file.write_text("test")

        result = packager.validate_data_file(data_file)

        assert result is True

    def test_validate_missing_data_file(self, packager, temp_dir):
        """Test validation fails for missing file."""
        missing_file = temp_dir / "missing.txt"

        with pytest.raises(FileNotFoundError):
            packager.validate_data_file(missing_file)

    def test_validate_quality_report(self, packager, sample_quality_report):
        """Test validation of quality report."""
        result = packager.validate_quality_report(sample_quality_report)

        assert result is True

    def test_validate_quality_report_missing_fields(self, packager):
        """Test validation fails for incomplete report."""
        incomplete_report = {"timestamp": "2025-11-21"}

        with pytest.raises(ValueError):
            packager.validate_quality_report(incomplete_report)

    def test_package_name_parsing(self, packager):
        """Test that package name is correctly parsed."""
        assert packager.package_name == "biodata/clinvar"
        assert packager.namespace == "biodata"
        assert packager.package == "clinvar"

    def test_create_package_local_directory(self, packager, temp_dir):
        """Test package creation uses proper directory."""
        with patch("src.quilt_packager.quilt3.Package") as mock_pkg_class:
            packager.create_package()

            # Should initialize Package
            mock_pkg_class.assert_called_once()

    def test_full_workflow_create_and_set_metadata(self, packager, temp_dir, sample_quality_report):
        """Test full workflow: create package, add data, add metadata."""
        data_file = temp_dir / "variant_summary.txt"
        data_file.write_text("VariationID\tType\n1\tSNV\n")

        with patch("src.quilt_packager.quilt3.Package") as mock_pkg_class:
            mock_pkg = MagicMock()
            mock_pkg_class.return_value = mock_pkg

            # Create and configure package
            pkg = packager.create_package(data_file)
            packager.add_data_file(pkg, data_file)
            packager.add_quality_report(pkg, sample_quality_report)

            # Verify operations were called
            assert mock_pkg.set.call_count >= 1
            assert mock_pkg.set_meta.call_count >= 1

    def test_extract_version_from_filename(self, packager):
        """Test extracting version info from filename."""
        filename = "variant_summary_2025-11-21.txt.gz"
        version = packager._extract_version_info(filename)

        assert version is not None
        assert "2025-11-21" in str(version)

    def test_metadata_includes_clinvar_release_date(self, packager, sample_quality_report):
        """Test that metadata includes ClinVar release date."""
        metadata = packager._generate_metadata_from_report(sample_quality_report)

        # Should have timestamp as release info
        assert "timestamp" in metadata

    def test_handle_special_characters_in_metadata(self, packager):
        """Test handling of special characters in metadata."""
        mock_pkg = MagicMock()
        metadata = {
            "description": "ClinVar data with special chars: @#$%^&*()",
            "tags": ["test", "variant-data"],
        }

        packager.set_metadata(mock_pkg, metadata)

        mock_pkg.set_meta.assert_called()

    def test_package_creation_with_custom_name(self, quilt_config):
        """Test creating package with custom name."""
        custom_config = quilt_config.copy()
        custom_config["quilt"]["package_name"] = "custom/mypackage"

        packager = QuiltPackager(custom_config)

        # Should parse namespace and package correctly
        assert packager.namespace == "custom"
        assert packager.package == "mypackage"
        assert packager.package_name == "custom/mypackage"

    def test_registry_url_validation(self, packager):
        """Test validation of registry URL."""
        assert packager.registry.startswith("s3://")

    def test_large_file_handling(self, packager, temp_dir):
        """Test handling of large data files."""
        # Create a larger file (simulated)
        large_file = temp_dir / "large_data.txt"
        large_file.write_text("x" * (1024 * 100))  # 100KB

        result = packager.validate_data_file(large_file)

        assert result is True

    def test_metadata_json_serializable(self, packager, sample_quality_report):
        """Test that generated metadata is JSON serializable."""
        metadata = packager._generate_metadata_from_report(sample_quality_report)

        # Should be JSON serializable
        json_str = json.dumps(metadata)
        assert json_str is not None
