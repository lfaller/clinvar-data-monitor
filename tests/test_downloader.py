"""Tests for the ClinVar data downloader module."""

import hashlib
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests

from src.downloader import ClinVarDownloader


class TestClinVarDownloader:
    """Test suite for ClinVarDownloader class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def downloader(self, temp_dir):
        """Create a ClinVarDownloader instance for testing."""
        config = {
            "clinvar": {
                "source_url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz",
                "checksum_url": "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz.md5",
                "download_dir": str(temp_dir),
            }
        }
        return ClinVarDownloader(config)

    def test_init_creates_download_directory(self, temp_dir):
        """Test that __init__ creates the download directory."""
        config = {
            "clinvar": {
                "source_url": "https://example.com/file.gz",
                "checksum_url": "https://example.com/file.gz.md5",
                "download_dir": str(temp_dir / "new_dir"),
            }
        }
        downloader = ClinVarDownloader(config)
        assert downloader.download_dir.exists()

    def test_init_stores_config(self, downloader, temp_dir):
        """Test that __init__ properly stores configuration."""
        assert downloader.download_dir == Path(temp_dir)
        assert "source_url" in downloader.config["clinvar"]
        assert "checksum_url" in downloader.config["clinvar"]

    @patch("src.downloader.requests.get")
    def test_download_file_success(self, mock_get, downloader):
        """Test successful file download."""
        mock_response = MagicMock()
        mock_response.content = b"test file content"
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = downloader.download_file("https://example.com/file.gz")

        assert result.exists()
        assert result.read_bytes() == b"test file content"
        mock_get.assert_called_once()

    @patch("src.downloader.requests.get")
    def test_download_file_with_existing_file(self, mock_get, downloader):
        """Test that download skips if file already exists."""
        test_file = downloader.download_dir / "variant_summary.txt.gz"
        test_file.write_bytes(b"existing content")

        result = downloader.download_file(
            "https://example.com/variant_summary.txt.gz"
        )

        assert result.exists()
        assert result.read_bytes() == b"existing content"
        # Should not have made a request
        mock_get.assert_not_called()

    @patch("src.downloader.requests.get")
    def test_download_file_retry_on_failure(self, mock_get, downloader):
        """Test that download retries on failure."""
        mock_response = MagicMock()
        mock_response.content = b"success"
        mock_response.raise_for_status.return_value = None

        mock_get.side_effect = [
            requests.RequestException("Connection failed"),
            requests.RequestException("Connection failed"),
            mock_response,
        ]

        result = downloader.download_file("https://example.com/file.gz", max_retries=3)

        assert result.exists()
        assert result.read_bytes() == b"success"
        assert mock_get.call_count == 3

    def test_calculate_md5_checksum(self, downloader, temp_dir):
        """Test MD5 checksum calculation."""
        test_file = temp_dir / "test.txt"
        test_content = b"test content"
        test_file.write_bytes(test_content)

        checksum = downloader.calculate_md5(test_file)

        expected = hashlib.md5(test_content).hexdigest()
        assert checksum == expected

    @patch("src.downloader.requests.get")
    def test_download_checksum_file(self, mock_get, downloader):
        """Test downloading checksum file."""
        checksum_content = "abc123def456  variant_summary.txt.gz\n"
        mock_response = MagicMock()
        mock_response.text = checksum_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        checksum = downloader.download_checksum("https://example.com/file.gz.md5")

        assert checksum == "abc123def456"

    @patch("src.downloader.requests.get")
    def test_download_checksum_file_multiple_formats(self, mock_get, downloader):
        """Test checksum parsing with different formats."""
        # Format: checksum  filename
        checksum_content = "abc123def456  variant_summary.txt.gz"
        mock_response = MagicMock()
        mock_response.text = checksum_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        checksum = downloader.download_checksum("https://example.com/file.gz.md5")

        assert checksum == "abc123def456"

    def test_validate_checksum_success(self, downloader, temp_dir):
        """Test successful checksum validation."""
        test_file = temp_dir / "test.txt"
        test_content = b"test content"
        test_file.write_bytes(test_content)

        expected_checksum = hashlib.md5(test_content).hexdigest()

        assert downloader.validate_checksum(test_file, expected_checksum) is True

    def test_validate_checksum_failure(self, downloader, temp_dir):
        """Test checksum validation failure."""
        test_file = temp_dir / "test.txt"
        test_file.write_bytes(b"test content")

        with pytest.raises(ValueError, match="Checksum mismatch"):
            downloader.validate_checksum(test_file, "wrongchecksumvalue")

    def test_decompress_gzip_file(self, downloader, temp_dir):
        """Test gzip decompression."""
        import gzip

        original_content = b"test data content"
        gz_file = temp_dir / "test.gz"

        with gzip.open(gz_file, "wb") as f:
            f.write(original_content)

        result = downloader.decompress_gzip(gz_file)

        assert result.exists()
        assert result.read_bytes() == original_content

    def test_decompress_gzip_file_with_output_path(self, downloader, temp_dir):
        """Test gzip decompression with custom output path."""
        import gzip

        original_content = b"test data content"
        gz_file = temp_dir / "test.gz"

        with gzip.open(gz_file, "wb") as f:
            f.write(original_content)

        output_file = temp_dir / "custom_output.txt"
        result = downloader.decompress_gzip(gz_file, output_path=output_file)

        assert result == output_file
        assert result.read_bytes() == original_content

    @patch.object(ClinVarDownloader, "download_file")
    @patch.object(ClinVarDownloader, "download_checksum")
    @patch.object(ClinVarDownloader, "validate_checksum")
    @patch.object(ClinVarDownloader, "decompress_gzip")
    def test_download_and_verify_full_workflow(
        self, mock_decompress, mock_validate, mock_checksum, mock_download, downloader
    ):
        """Test the full download and verify workflow."""
        mock_download.return_value = Path("/tmp/variant_summary.txt.gz")
        mock_checksum.return_value = "abc123"
        mock_decompress.return_value = Path("/tmp/variant_summary.txt")

        result = downloader.download_and_verify()

        assert result.exists() or result.name == "variant_summary.txt"
        mock_download.assert_called_once()
        mock_checksum.assert_called_once()
        mock_validate.assert_called_once()
        mock_decompress.assert_called_once()

    @patch("src.downloader.requests.get")
    def test_download_file_with_progress(self, mock_get, downloader):
        """Test that download_file can handle large files."""
        # Simulate a large file
        large_content = b"x" * (10 * 1024 * 1024)  # 10 MB
        mock_response = MagicMock()
        mock_response.content = large_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = downloader.download_file("https://example.com/large.gz")

        assert result.exists()
        assert len(result.read_bytes()) == len(large_content)

    def test_get_latest_filename(self, downloader):
        """Test extracting the correct filename from URL."""
        url = "https://ftp.ncbi.nlm.nih.gov/pub/clinvar/tab_delimited/variant_summary.txt.gz"
        filename = downloader._get_filename_from_url(url)
        assert filename == "variant_summary.txt.gz"

    def test_file_not_found_error(self, downloader):
        """Test handling of missing file."""
        non_existent = downloader.download_dir / "non_existent.txt"
        with pytest.raises(FileNotFoundError):
            downloader.calculate_md5(non_existent)
