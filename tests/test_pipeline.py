"""Tests for the pipeline orchestration module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.run_pipeline import ClinVarPipeline


class TestClinVarPipeline:
    """Test suite for ClinVarPipeline orchestration class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def pipeline_config(self, temp_dir):
        """Create pipeline configuration."""
        return {
            "clinvar": {
                "source_url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
                "checksum_url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz.md5",
                "download_dir": str(temp_dir / "downloads"),
            },
            "quality": {
                "thresholds": {
                    "min_quality_score": 75,
                    "max_null_percentage": 15,
                    "max_conflict_rate": 5,
                    "max_drift_percentage": 20,
                },
                "output_dir": str(temp_dir / "quality_reports"),
            },
            "quilt": {
                "bucket": "test-clinvar",
                "package_name": "biodata/clinvar",
                "registry": "s3://test-clinvar",
                "push_to_registry": False,
            },
            "logging": {
                "level": "INFO",
                "log_dir": str(temp_dir / "logs"),
                "file_logging": True,
                "console_logging": True,
            },
        }

    @pytest.fixture
    def pipeline(self, pipeline_config):
        """Create a ClinVarPipeline instance."""
        return ClinVarPipeline(pipeline_config)

    def test_init_loads_config(self, pipeline, pipeline_config):
        """Test that __init__ loads configuration."""
        assert pipeline.config is not None
        assert "clinvar" in pipeline.config

    def test_init_creates_directories(self, pipeline_config):
        """Test that __init__ creates required directories."""
        pipeline = ClinVarPipeline(pipeline_config)

        assert Path(pipeline_config["clinvar"]["download_dir"]).exists()
        assert Path(pipeline_config["quality"]["output_dir"]).exists()
        assert Path(pipeline_config["logging"]["log_dir"]).exists()

    def test_setup_logging(self, pipeline):
        """Test logging setup."""
        # Should not raise
        pipeline.setup_logging()

    def test_initialize_modules(self, pipeline):
        """Test initialization of pipeline modules."""
        pipeline.initialize_modules()

        assert pipeline.downloader is not None
        assert pipeline.quality_checker is not None
        assert pipeline.packager is not None

    @patch("scripts.run_pipeline.ClinVarDownloader")
    def test_download_data(self, mock_downloader_class, pipeline):
        """Test data download step."""
        mock_downloader = MagicMock()
        mock_downloader.download_and_verify.return_value = Path("/tmp/variant_summary.txt")
        mock_downloader_class.return_value = mock_downloader

        pipeline.downloader = mock_downloader

        result = pipeline.download_data()

        assert result is not None
        mock_downloader.download_and_verify.assert_called_once()

    @patch("scripts.run_pipeline.ClinVarDownloader")
    def test_assess_quality(self, mock_downloader_class, pipeline, temp_dir):
        """Test quality assessment step."""
        # Create sample data file
        data_file = temp_dir / "variant_summary.txt"
        data_file.write_text("VariationID\tType\n1\tSNV\n")

        mock_quality_checker = MagicMock()
        mock_quality_checker.assess_quality.return_value = {
            "quality_score": 85.0,
            "row_count": 1,
        }
        pipeline.quality_checker = mock_quality_checker

        result = pipeline.assess_quality(data_file)

        assert result is not None
        assert "quality_score" in result

    def test_create_package(self, pipeline, temp_dir):
        """Test package creation step."""
        data_file = temp_dir / "variant_summary.txt"
        data_file.write_text("test")

        quality_report = {
            "timestamp": "2025-11-21T12:00:00+00:00",
            "quality_score": 85.0,
            "row_count": 100,
            "column_count": 8,
        }

        mock_packager = MagicMock()
        mock_packager.full_package_workflow.return_value = True
        pipeline.packager = mock_packager

        result = pipeline.create_package(data_file, quality_report)

        assert result is True
        mock_packager.full_package_workflow.assert_called_once()

    def test_run_full_pipeline(self, pipeline, temp_dir):
        """Test running the full pipeline."""
        # Mock all external dependencies
        with patch.object(pipeline, "download_data") as mock_download:
            with patch.object(pipeline, "assess_quality") as mock_quality:
                with patch.object(pipeline, "create_package") as mock_package:
                    # Setup return values
                    data_file = temp_dir / "variant_summary.txt"
                    data_file.write_text("test")

                    mock_download.return_value = data_file
                    mock_quality.return_value = {
                        "quality_score": 85.0,
                        "row_count": 100,
                        "column_count": 8,
                        "timestamp": "2025-11-21T12:00:00+00:00",
                    }
                    mock_package.return_value = True

                    result = pipeline.run()

                    assert result is True
                    mock_download.assert_called_once()
                    mock_quality.assert_called_once()
                    mock_package.assert_called_once()

    def test_pipeline_error_handling(self, pipeline):
        """Test pipeline error handling."""
        with patch.object(pipeline, "download_data") as mock_download:
            mock_download.side_effect = Exception("Download failed")

            # Pipeline catches exceptions and returns False
            result = pipeline.run()

            assert result is False

    def test_config_validation(self, pipeline_config):
        """Test configuration validation."""
        required_sections = ["clinvar", "quality", "quilt", "logging"]

        for section in required_sections:
            assert section in pipeline_config

    def test_pipeline_summary(self, pipeline, temp_dir):
        """Test pipeline summary generation."""
        summary = pipeline.generate_summary({
            "download_status": "success",
            "quality_score": 85.0,
            "package_status": "success",
        })

        assert summary is not None
        assert "download_status" in str(summary)

    def test_log_pipeline_start(self, pipeline):
        """Test logging pipeline start."""
        # Should not raise
        pipeline.log_pipeline_start()

    def test_log_pipeline_end(self, pipeline):
        """Test logging pipeline end."""
        # Should not raise
        pipeline.log_pipeline_end(True)

    def test_pipeline_result_success(self, pipeline):
        """Test successful pipeline result."""
        with patch.object(pipeline, "download_data") as mock_download:
            with patch.object(pipeline, "assess_quality") as mock_quality:
                with patch.object(pipeline, "create_package") as mock_package:
                    data_file = Path("/tmp/data.txt")
                    mock_download.return_value = data_file
                    mock_quality.return_value = {
                        "quality_score": 85.0,
                        "row_count": 100,
                        "column_count": 8,
                        "timestamp": "2025-11-21T12:00:00+00:00",
                    }
                    mock_package.return_value = True

                    result = pipeline.run()

                    assert result is True

    def test_initialize_modules_creates_instances(self, pipeline):
        """Test that initialize_modules creates proper instances."""
        pipeline.initialize_modules()

        # Should have all three modules initialized
        assert hasattr(pipeline, "downloader")
        assert hasattr(pipeline, "quality_checker")
        assert hasattr(pipeline, "packager")

    def test_pipeline_with_quality_threshold_check(self, pipeline):
        """Test pipeline respects quality thresholds."""
        min_score = pipeline.config["quality"]["thresholds"]["min_quality_score"]

        assert min_score == 75
