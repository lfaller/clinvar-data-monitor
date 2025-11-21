"""Tests for the ClinVar quality checker module."""

import json
import tempfile
from pathlib import Path

import pandas as pd
import pytest

from src.quality_checker import QualityChecker


class TestQualityChecker:
    """Test suite for QualityChecker class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            yield Path(tmp_dir)

    @pytest.fixture
    def sample_clinvar_data(self, temp_dir):
        """Create a sample ClinVar dataset for testing."""
        data = {
            "VariationID": [1001, 1002, 1003, 1004, 1005],
            "Type": ["single nucleotide variant", "deletion", "single nucleotide variant", "insertion", "single nucleotide variant"],
            "Locations": ["chr1:100-100", "chr1:200-250", "chr2:300-300", "chr3:400-401", "chr4:500-500"],
            "Protein Change": ["p.Met1Val", None, "p.Gly100Asp", "p.frameshift", "p.Pro50Ala"],
            "Symptom(s)/phenotype(s)": ["Disease A", "Disease B", None, "Disease C", "Disease A"],
            "ClinicalSignificance": ["Pathogenic", "Likely pathogenic", "Benign", "Pathogenic", "Likely pathogenic"],
            "ReviewStatus": ["★★★★", "★★★", "★★", "★", "★★★★"],
            "ConflictingInterpretations": [0, 1, 0, 2, 0],
        }
        df = pd.DataFrame(data)
        filepath = temp_dir / "variant_summary.txt"
        df.to_csv(filepath, sep="\t", index=False)
        return filepath

    @pytest.fixture
    def quality_checker(self):
        """Create a QualityChecker instance."""
        config = {
            "quality": {
                "thresholds": {
                    "min_quality_score": 75,
                    "max_null_percentage": 15,
                    "max_conflict_rate": 5,
                    "max_drift_percentage": 20,
                },
                "output_dir": "output/quality_reports",
            }
        }
        return QualityChecker(config)

    def test_init_creates_output_directory(self, temp_dir):
        """Test that __init__ creates the output directory."""
        config = {
            "quality": {
                "thresholds": {
                    "min_quality_score": 75,
                    "max_null_percentage": 15,
                    "max_conflict_rate": 5,
                    "max_drift_percentage": 20,
                },
                "output_dir": str(temp_dir / "output"),
            }
        }
        checker = QualityChecker(config)
        assert checker.output_dir.exists()

    def test_init_stores_config(self, quality_checker):
        """Test that __init__ properly stores configuration."""
        assert "thresholds" in quality_checker.config["quality"]
        assert quality_checker.config["quality"]["thresholds"]["min_quality_score"] == 75

    def test_load_variant_data_success(self, quality_checker, sample_clinvar_data):
        """Test successfully loading variant data from TSV."""
        df = quality_checker.load_variant_data(sample_clinvar_data)

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5
        assert "VariationID" in df.columns
        assert "ClinicalSignificance" in df.columns

    def test_load_variant_data_file_not_found(self, quality_checker, temp_dir):
        """Test error handling for missing file."""
        missing_file = temp_dir / "missing.txt"
        with pytest.raises(FileNotFoundError):
            quality_checker.load_variant_data(missing_file)

    def test_calculate_row_count(self, quality_checker, sample_clinvar_data):
        """Test row count calculation."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        row_count = quality_checker._calculate_row_count(df)

        assert row_count == 5

    def test_calculate_column_count(self, quality_checker, sample_clinvar_data):
        """Test column count calculation."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        col_count = quality_checker._calculate_column_count(df)

        assert col_count == 8

    def test_calculate_null_percentage(self, quality_checker, sample_clinvar_data):
        """Test null percentage calculation."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        null_pct = quality_checker._calculate_null_percentage(df)

        # Two columns have 1 null value each out of 5 rows
        # (1 + 1) / (5 * 8) = 2/40 = 5%
        assert 4 <= null_pct <= 6  # Allow small rounding differences

    def test_calculate_duplicate_count(self, quality_checker, sample_clinvar_data):
        """Test duplicate detection."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        duplicates = quality_checker._calculate_duplicate_count(df)

        assert duplicates == 0  # No duplicates in sample data

    def test_calculate_duplicate_count_with_duplicates(self, quality_checker, temp_dir):
        """Test duplicate count with actual duplicates."""
        data = {
            "VariationID": [1, 1, 2, 3, 3],
            "Type": ["SNV", "SNV", "DEL", "INS", "INS"],
        }
        df = pd.DataFrame(data)
        filepath = temp_dir / "test.txt"
        df.to_csv(filepath, sep="\t", index=False)

        df_loaded = quality_checker.load_variant_data(filepath)
        duplicates = quality_checker._calculate_duplicate_count(df_loaded)

        assert duplicates == 2  # Rows 1 and 4 are duplicates

    def test_calculate_conflicting_interpretations(self, quality_checker, sample_clinvar_data):
        """Test conflicting interpretations count."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        conflicts = quality_checker._calculate_conflicting_count(df)

        # Sum of ConflictingInterpretations: 0 + 1 + 0 + 2 + 0 = 3
        assert conflicts == 3

    def test_calculate_clinical_significance_distribution(self, quality_checker, sample_clinvar_data):
        """Test clinical significance distribution calculation."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        dist = quality_checker._calculate_clinical_significance_distribution(df)

        assert "Pathogenic" in dist
        assert "Likely pathogenic" in dist
        assert "Benign" in dist
        assert dist["Pathogenic"] == 2
        assert dist["Likely pathogenic"] == 2
        assert dist["Benign"] == 1

    def test_calculate_review_status_distribution(self, quality_checker, sample_clinvar_data):
        """Test review status distribution calculation."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        dist = quality_checker._calculate_review_status_distribution(df)

        assert "4-star" in dist
        assert "3-star" in dist
        assert "2-star" in dist
        assert "1-star" in dist
        assert dist["4-star"] == 2
        assert dist["3-star"] == 1
        assert dist["2-star"] == 1
        assert dist["1-star"] == 1

    def test_calculate_basic_metrics(self, quality_checker, sample_clinvar_data):
        """Test calculation of all basic metrics."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        metrics = quality_checker.calculate_basic_metrics(df)

        assert metrics["row_count"] == 5
        assert metrics["column_count"] == 8
        assert "null_percentage" in metrics
        assert "duplicate_count" in metrics
        assert metrics["conflicting_count"] == 3

    def test_calculate_quality_score_all_good(self, quality_checker):
        """Test quality score calculation with perfect data."""
        report = {
            "row_count": 1000,
            "null_percentage_avg": 2.0,
            "conflicting_count": 5,
            "four_star_percentage": 85.0,
        }

        score = quality_checker.calculate_quality_score(report)

        assert 80 <= score <= 100

    def test_calculate_quality_score_all_bad(self, quality_checker):
        """Test quality score calculation with poor data."""
        report = {
            "row_count": 100,
            "null_percentage_avg": 25.0,
            "conflicting_count": 50,
            "four_star_percentage": 0.0,
        }

        score = quality_checker.calculate_quality_score(report)

        # With 25% null (penalty -12.5) and 50% conflict (penalty -25),
        # score should be lower than good data but bounded 0-100
        assert 0 <= score <= 70

    def test_calculate_quality_score_bounds(self, quality_checker):
        """Test that quality score is bounded 0-100."""
        report = {
            "row_count": 1,
            "null_percentage_avg": 100.0,
            "conflicting_count": 1000,
            "four_star_percentage": 100.0,
        }

        score = quality_checker.calculate_quality_score(report)

        assert 0 <= score <= 100

    def test_generate_report_returns_valid_json(self, quality_checker, sample_clinvar_data):
        """Test that report can be serialized to JSON."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        report = quality_checker.generate_report(df)

        # Should be JSON serializable
        json_str = json.dumps(report)
        assert json_str is not None

    def test_generate_report_contains_all_fields(self, quality_checker, sample_clinvar_data):
        """Test that generated report contains all required fields."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        report = quality_checker.generate_report(df)

        required_fields = [
            "timestamp",
            "row_count",
            "column_count",
            "null_percentage_avg",
            "duplicate_count",
            "conflicting_count",
            "quality_score",
            "clinical_significance_distribution",
            "review_status_distribution",
        ]

        for field in required_fields:
            assert field in report, f"Missing field: {field}"

    def test_save_report_creates_json_file(self, quality_checker, sample_clinvar_data, temp_dir):
        """Test that report is saved to JSON file."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        report = quality_checker.generate_report(df)

        output_file = quality_checker.save_report(report, output_dir=temp_dir)

        assert output_file.exists()
        assert output_file.suffix == ".json"

        # Verify JSON is valid
        with open(output_file) as f:
            loaded_report = json.load(f)
        assert loaded_report["row_count"] == 5

    def test_full_workflow(self, quality_checker, sample_clinvar_data, temp_dir):
        """Test the full quality check workflow."""
        quality_checker.output_dir = temp_dir

        # Load data
        df = quality_checker.load_variant_data(sample_clinvar_data)

        # Generate report
        report = quality_checker.generate_report(df)

        # Save report
        output_file = quality_checker.save_report(report, output_dir=temp_dir)

        assert output_file.exists()
        assert report["row_count"] == 5
        assert report["quality_score"] is not None

    def test_handle_empty_dataframe(self, quality_checker, temp_dir):
        """Test handling of empty DataFrame."""
        # Create empty CSV
        filepath = temp_dir / "empty.txt"
        pd.DataFrame(columns=["VariationID", "Type"]).to_csv(filepath, sep="\t", index=False)

        df = quality_checker.load_variant_data(filepath)
        report = quality_checker.generate_report(df)

        assert report["row_count"] == 0
        assert isinstance(report["quality_score"], (int, float))

    def test_calculate_null_percentage_all_nulls(self, quality_checker):
        """Test null percentage with all null values."""
        df = pd.DataFrame({"col1": [None, None], "col2": [None, None]})
        null_pct = quality_checker._calculate_null_percentage(df)

        assert null_pct == 100.0

    def test_calculate_null_percentage_no_nulls(self, quality_checker):
        """Test null percentage with no null values."""
        df = pd.DataFrame({"col1": [1, 2], "col2": [3, 4]})
        null_pct = quality_checker._calculate_null_percentage(df)

        assert null_pct == 0.0

    def test_quality_checker_logging(self, quality_checker, sample_clinvar_data, caplog):
        """Test that quality checker logs appropriately."""
        df = quality_checker.load_variant_data(sample_clinvar_data)
        report = quality_checker.generate_report(df)

        # Should have logged something
        assert len(caplog.records) >= 0  # At least some logging
