#!/usr/bin/env python
"""Quick test script to demonstrate the modules in action.

This script loads sample ClinVar data and runs the quality checker
without requiring actual downloads or S3 access.
"""

import json
from pathlib import Path

from src.quality_checker import QualityChecker
from src.quilt_packager import QuiltPackager


def main():
    """Run module demonstration."""
    print("\n" + "=" * 80)
    print("ClinVar Data Quality Monitor - Module Demonstration")
    print("=" * 80 + "\n")

    # Configuration
    config = {
        "quality": {
            "thresholds": {
                "min_quality_score": 75,
                "max_null_percentage": 15,
                "max_conflict_rate": 5,
                "max_drift_percentage": 20,
            },
            "output_dir": "output/quality_reports",
        },
        "quilt": {
            "bucket": "test-clinvar",
            "package_name": "biodata/clinvar",
            "registry": "s3://test-clinvar",
            "push_to_registry": False,
        },
    }

    # 1. Load sample data
    print("1. LOADING SAMPLE DATA")
    print("-" * 80)
    data_file = Path("data/sample_variant_summary.txt")

    if not data_file.exists():
        print(f"❌ Sample data file not found: {data_file}")
        print("   Run from project root: poetry run python scripts/test_modules.py")
        return False

    print(f"✓ Sample data file found: {data_file}")
    print()

    # 2. Run quality checker
    print("2. QUALITY ASSESSMENT")
    print("-" * 80)
    try:
        qc = QualityChecker(config)
        print(f"✓ QualityChecker initialized")

        # Load and assess quality
        df = qc.load_variant_data(data_file)
        print(f"✓ Loaded {len(df)} variants with {len(df.columns)} columns")

        # Generate report
        report = qc.generate_report(df)
        print(f"✓ Quality report generated")
        print()

        # Display report summary
        print("Quality Report Summary:")
        print(f"  - Quality Score: {report['quality_score']:.1f}/100")
        print(f"  - Row Count: {report['row_count']}")
        print(f"  - Column Count: {report['column_count']}")
        print(f"  - Null Percentage: {report['null_percentage_avg']:.1f}%")
        print(f"  - Duplicate Count: {report['duplicate_count']}")
        print(f"  - Conflicting Interpretations: {report['conflicting_count']}")
        print(f"  - 4-Star Percentage: {report['four_star_percentage']:.1f}%")
        print()

        # Display clinical significance distribution
        print("Clinical Significance Distribution:")
        for sig, count in report.get('clinical_significance_distribution', {}).items():
            print(f"  - {sig}: {count}")
        print()

        # Display review status distribution
        print("Review Status Distribution:")
        for status, count in report.get('review_status_distribution', {}).items():
            print(f"  - {status}: {count}")
        print()

        # Save report
        saved_report = qc.save_report(report)
        print(f"✓ Report saved to: {saved_report}")
        print()

    except Exception as e:
        print(f"❌ Quality assessment failed: {e}")
        return False

    # 3. Test packager metadata generation
    print("3. QUILT PACKAGING")
    print("-" * 80)
    try:
        packager = QuiltPackager(config)
        print(f"✓ QuiltPackager initialized")
        print(f"✓ Package name: {packager.package_name}")
        print(f"✓ Namespace: {packager.namespace}")
        print(f"✓ Package: {packager.package}")
        print(f"✓ Registry: {packager.registry}")
        print()

        # Generate metadata from report
        metadata = packager._generate_metadata_from_report(report)
        print("Generated Metadata:")
        for key, value in metadata.items():
            if not key.startswith("clin_sig") and not key.startswith("review_"):
                print(f"  - {key}: {value}")
        print()

        # Validate report
        is_valid = packager.validate_quality_report(report)
        print(f"✓ Quality report validation: {is_valid}")
        print()

    except Exception as e:
        print(f"❌ Packaging setup failed: {e}")
        return False

    # Summary
    print("=" * 80)
    print("✅ All modules working correctly!")
    print("=" * 80)
    print()
    print("Next steps:")
    print("  1. To test with actual pipeline:")
    print("     poetry run python scripts/run_pipeline.py --help")
    print()
    print("  2. To run all tests:")
    print("     poetry run pytest tests/ -v")
    print()
    print("  3. To view generated quality report:")
    print(f"     cat {saved_report}")
    print()

    return True


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
