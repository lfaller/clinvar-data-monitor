"""ClinVar quality assessment engine.

This module calculates quality metrics for ClinVar data, generates quality reports,
and tracks data quality over time.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger(__name__)


class QualityChecker:
    """Calculate quality metrics for ClinVar variant data."""

    def __init__(self, config: dict):
        """Initialize the quality checker with configuration.

        Args:
            config: Configuration dictionary with quality section containing:
                - thresholds: Quality thresholds (min_quality_score, max_null_percentage, etc.)
                - output_dir: Directory for saving quality reports
        """
        self.config = config
        self.output_dir = Path(config["quality"]["output_dir"])
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Quality checker initialized with output_dir: {self.output_dir}")

    def load_variant_data(self, filepath: Path) -> pd.DataFrame:
        """Load ClinVar variant data from TSV file.

        Args:
            filepath: Path to variant summary TSV file

        Returns:
            pandas DataFrame with variant data

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")

        logger.info(f"Loading variant data from {filepath}")
        df = pd.read_csv(filepath, sep="\t", dtype={"VariationID": "int64", "ConflictingInterpretations": "int64"})

        logger.info(f"Loaded {len(df)} variants with {len(df.columns)} columns")
        return df

    def _calculate_row_count(self, df: pd.DataFrame) -> int:
        """Calculate number of rows."""
        return len(df)

    def _calculate_column_count(self, df: pd.DataFrame) -> int:
        """Calculate number of columns."""
        return len(df.columns)

    def _calculate_null_percentage(self, df: pd.DataFrame) -> float:
        """Calculate percentage of null values in dataset.

        Args:
            df: Variant DataFrame

        Returns:
            Percentage of null values (0-100)
        """
        if df.empty:
            return 0.0

        total_cells = len(df) * len(df.columns)
        null_cells = df.isnull().sum().sum()
        null_percentage = (null_cells / total_cells) * 100 if total_cells > 0 else 0.0

        return round(null_percentage, 2)

    def _calculate_duplicate_count(self, df: pd.DataFrame) -> int:
        """Count duplicate rows in dataset.

        Args:
            df: Variant DataFrame

        Returns:
            Number of duplicate rows
        """
        if df.empty:
            return 0

        duplicates = df.duplicated().sum()
        return int(duplicates)

    def _calculate_conflicting_count(self, df: pd.DataFrame) -> int:
        """Count total conflicting interpretations.

        Args:
            df: Variant DataFrame with ConflictingInterpretations column

        Returns:
            Total count of conflicting interpretations
        """
        if "ConflictingInterpretations" not in df.columns:
            return 0

        return int(df["ConflictingInterpretations"].sum())

    def _calculate_clinical_significance_distribution(
        self, df: pd.DataFrame
    ) -> Dict[str, int]:
        """Calculate distribution of clinical significance values.

        Args:
            df: Variant DataFrame

        Returns:
            Dictionary with significance levels and counts
        """
        if "ClinicalSignificance" not in df.columns:
            return {}

        dist = df["ClinicalSignificance"].value_counts().to_dict()
        return {k: int(v) for k, v in dist.items()}

    def _calculate_review_status_distribution(self, df: pd.DataFrame) -> Dict[str, int]:
        """Calculate distribution of review status (star ratings).

        Args:
            df: Variant DataFrame

        Returns:
            Dictionary with star ratings and counts
        """
        if "ReviewStatus" not in df.columns:
            return {}

        def extract_stars(status_str):
            """Convert ★ symbols to star rating."""
            if pd.isna(status_str):
                return "no-review"
            star_count = str(status_str).count("★")
            return f"{star_count}-star"

        star_ratings = df["ReviewStatus"].apply(extract_stars).value_counts().to_dict()
        return {k: int(v) for k, v in star_ratings.items()}

    def calculate_basic_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Calculate basic data quality metrics.

        Args:
            df: Variant DataFrame

        Returns:
            Dictionary with basic metrics
        """
        logger.info("Calculating basic quality metrics")

        metrics = {
            "row_count": self._calculate_row_count(df),
            "column_count": self._calculate_column_count(df),
            "null_percentage": self._calculate_null_percentage(df),
            "duplicate_count": self._calculate_duplicate_count(df),
            "conflicting_count": self._calculate_conflicting_count(df),
            "clinical_significance_distribution": self._calculate_clinical_significance_distribution(df),
            "review_status_distribution": self._calculate_review_status_distribution(df),
        }

        return metrics

    def calculate_quality_score(self, report: Dict[str, Any]) -> float:
        """Calculate overall quality score (0-100).

        Factors:
        - Data completeness (30 points): penalize high null percentage
        - Low conflict rate (25 points): penalize high conflict rate
        - High review status (25 points): reward high-confidence annotations
        - Reasonable size (20 points): penalize very small datasets

        Args:
            report: Quality metrics report

        Returns:
            Quality score (0-100)
        """
        score = 100.0

        # Completeness penalty (30 points max)
        null_pct = report.get("null_percentage_avg", 0)
        score -= min(null_pct * 0.5, 30)

        # Conflict penalty (25 points max)
        conflict_rate = 0
        if report.get("row_count", 0) > 0:
            conflict_rate = (report.get("conflicting_count", 0) / report["row_count"]) * 100
        score -= min(conflict_rate * 2, 25)

        # Review status bonus (25 points max)
        four_star_pct = report.get("four_star_percentage", 0)
        score += min(four_star_pct * 0.25, 25)

        # Size penalty (20 points max)
        row_count = report.get("row_count", 0)
        if row_count < 100:
            score -= min((100 - row_count) * 0.2, 20)

        # Bound score between 0 and 100
        return max(0, min(100, score))

    def generate_report(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate comprehensive quality report for dataset.

        Args:
            df: Variant DataFrame

        Returns:
            Dictionary with quality metrics and analysis
        """
        logger.info("Generating quality report")

        # Calculate basic metrics
        metrics = self.calculate_basic_metrics(df)

        # Calculate average null percentage across columns
        null_percentage_avg = metrics["null_percentage"]

        # Calculate four-star percentage
        review_dist = metrics.get("review_status_distribution", {})
        four_star_count = review_dist.get("4-star", 0)
        four_star_percentage = (
            (four_star_count / metrics["row_count"]) * 100
            if metrics["row_count"] > 0
            else 0
        )

        # Prepare report
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "row_count": metrics["row_count"],
            "column_count": metrics["column_count"],
            "null_percentage_avg": null_percentage_avg,
            "duplicate_count": metrics["duplicate_count"],
            "conflicting_count": metrics["conflicting_count"],
            "four_star_percentage": four_star_percentage,
            "clinical_significance_distribution": metrics[
                "clinical_significance_distribution"
            ],
            "review_status_distribution": metrics["review_status_distribution"],
        }

        # Calculate quality score
        report["quality_score"] = self.calculate_quality_score(report)

        logger.info(f"Generated report with quality score: {report['quality_score']}")
        return report

    def save_report(
        self, report: Dict[str, Any], output_dir: Optional[Path] = None
    ) -> Path:
        """Save quality report to JSON file.

        Args:
            report: Quality metrics report
            output_dir: Optional directory for output. Uses self.output_dir if not provided

        Returns:
            Path to saved report file
        """
        if output_dir is None:
            output_dir = self.output_dir

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename with timestamp
        timestamp = report.get("timestamp", datetime.now(timezone.utc).isoformat())
        timestamp_str = timestamp.replace(":", "-").replace(".", "-").split("T")[0]
        filename = f"quality_report_{timestamp_str}.json"
        filepath = output_dir / filename

        logger.info(f"Saving quality report to {filepath}")

        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

        logger.info(f"Report saved successfully: {filepath}")
        return filepath

    def assess_quality(self, data_filepath: Path) -> Dict[str, Any]:
        """Execute the full quality assessment workflow.

        This is the main entry point that coordinates:
        1. Load variant data
        2. Calculate metrics
        3. Generate report
        4. Save report

        Args:
            data_filepath: Path to variant summary data

        Returns:
            Quality report dictionary
        """
        logger.info("Starting quality assessment workflow")

        # Load data
        df = self.load_variant_data(data_filepath)

        # Generate report
        report = self.generate_report(df)

        # Save report
        self.save_report(report)

        logger.info("Quality assessment complete")
        return report
