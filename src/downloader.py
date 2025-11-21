"""ClinVar data downloader module.

This module handles downloading ClinVar variant summary data from the NCBI FTP server,
validating file integrity with MD5 checksums, and decompressing the data.
"""

import gzip
import hashlib
import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


class ClinVarDownloader:
    """Download and validate ClinVar data from NCBI FTP servers."""

    def __init__(self, config: dict):
        """Initialize the downloader with configuration.

        Args:
            config: Configuration dictionary with clinvar section containing:
                - source_url: URL to ClinVar data file
                - checksum_url: URL to MD5 checksum file
                - download_dir: Local directory for downloads
        """
        self.config = config
        self.download_dir = Path(config["clinvar"]["download_dir"])
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.source_url = config["clinvar"]["source_url"]
        self.checksum_url = config["clinvar"]["checksum_url"]

        logger.info(f"Downloader initialized with download_dir: {self.download_dir}")

    def download_file(
        self, url: str, max_retries: int = 3, timeout: int = 30
    ) -> Path:
        """Download a file from URL with retry logic.

        Args:
            url: URL to download from
            max_retries: Number of retry attempts
            timeout: Request timeout in seconds

        Returns:
            Path to downloaded file

        Raises:
            Exception: If download fails after all retries
        """
        filename = self._get_filename_from_url(url)
        filepath = self.download_dir / filename

        # Skip if file already exists
        if filepath.exists():
            logger.info(f"File already exists, skipping download: {filepath}")
            return filepath

        logger.info(f"Downloading {url}")

        for attempt in range(max_retries):
            try:
                response = requests.get(url, timeout=timeout)
                response.raise_for_status()

                filepath.write_bytes(response.content)
                logger.info(f"Successfully downloaded to {filepath}")
                return filepath

            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Download attempt {attempt + 1} failed: {e}. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"Download failed after {max_retries} attempts")
                    raise

    def calculate_md5(self, filepath: Path) -> str:
        """Calculate MD5 checksum of a file.

        Args:
            filepath: Path to file

        Returns:
            MD5 checksum as hex string

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        md5_hash = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)

        return md5_hash.hexdigest()

    def download_checksum(self, checksum_url: str) -> str:
        """Download and parse MD5 checksum from file.

        Expects format: "checksum  filename"

        Args:
            checksum_url: URL to checksum file

        Returns:
            MD5 checksum value

        Raises:
            Exception: If download or parsing fails
        """
        logger.info(f"Downloading checksum from {checksum_url}")

        response = requests.get(checksum_url, timeout=30)
        response.raise_for_status()

        # Parse checksum (format: "checksum  filename")
        checksum_line = response.text.strip().split()[0]
        logger.info("Successfully retrieved checksum")

        return checksum_line

    def validate_checksum(self, filepath: Path, expected_checksum: str) -> bool:
        """Validate file against expected checksum.

        Args:
            filepath: Path to file to validate
            expected_checksum: Expected MD5 checksum

        Returns:
            True if checksum matches

        Raises:
            ValueError: If checksum doesn't match
        """
        actual_checksum = self.calculate_md5(filepath)

        if actual_checksum.lower() != expected_checksum.lower():
            logger.error(
                f"Checksum mismatch for {filepath}: "
                f"expected {expected_checksum}, got {actual_checksum}"
            )
            raise ValueError(
                f"Checksum mismatch for {filepath}: "
                f"expected {expected_checksum}, got {actual_checksum}"
            )

        logger.info(f"Checksum validation passed for {filepath}")
        return True

    def decompress_gzip(
        self, gz_filepath: Path, output_path: Optional[Path] = None
    ) -> Path:
        """Decompress a gzip file.

        Args:
            gz_filepath: Path to .gz file
            output_path: Optional custom output path. If not provided,
                        removes .gz extension

        Returns:
            Path to decompressed file
        """
        if output_path is None:
            output_path = gz_filepath.with_suffix("")

        logger.info(f"Decompressing {gz_filepath} to {output_path}")

        with gzip.open(gz_filepath, "rb") as f_in:
            output_path.write_bytes(f_in.read())

        logger.info(f"Successfully decompressed to {output_path}")
        return output_path

    def download_and_verify(self) -> Path:
        """Execute the full download and verification workflow.

        This is the main entry point that coordinates:
        1. Download data file
        2. Download checksum file
        3. Validate checksum
        4. Decompress data

        Returns:
            Path to decompressed data file

        Raises:
            Various exceptions if any step fails
        """
        logger.info("Starting download and verification workflow")

        # Download data file
        gz_filepath = self.download_file(self.source_url)

        # Download and validate checksum
        expected_checksum = self.download_checksum(self.checksum_url)
        self.validate_checksum(gz_filepath, expected_checksum)

        # Decompress
        output_filepath = self.decompress_gzip(gz_filepath)

        logger.info(f"Download and verification complete: {output_filepath}")
        return output_filepath

    @staticmethod
    def _get_filename_from_url(url: str) -> str:
        """Extract filename from URL.

        Args:
            url: URL string

        Returns:
            Filename from URL path
        """
        return urlparse(url).path.split("/")[-1]
