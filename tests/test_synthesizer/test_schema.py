"""Regression tests for report schema validation."""

from __future__ import annotations

import unittest

from backend.agent.memory import EvidenceRecord
from backend.synthesizer.schema import ResearchReport, ReportClaim, ReportValidationError, validate_report_sources


class ReportSchemaTests(unittest.TestCase):
    def test_report_round_trip_to_dict(self) -> None:
        report = ResearchReport(
            title="FAA BVLOS Guidance",
            summary="FAA is evaluating BVLOS pathways.",
            key_findings=[ReportClaim(text="FAA is evaluating BVLOS pathways.", source_urls=["https://faa.gov/bvlos"])],
            sources_used=["https://faa.gov/bvlos"],
            confidence=0.91,
            limitations=["single source"],
        )

        payload = report.to_dict()
        restored = ResearchReport.from_dict(payload)

        self.assertEqual(report, restored)

    def test_validation_rejects_unsupported_report_source(self) -> None:
        report = ResearchReport(
            title="Unsupported source",
            summary="Claim cites a source outside evidence.",
            key_findings=[ReportClaim(text="Unsupported claim", source_urls=["https://example.com/unsupported"])],
            sources_used=["https://example.com/unsupported"],
            confidence=0.7,
        )

        with self.assertRaisesRegex(ReportValidationError, "unsupported_source"):
            validate_report_sources(
                report,
                [EvidenceRecord(url="https://faa.gov/bvlos", title="FAA", claims=["FAA claim"], credibility_score=0.9)],
            )

    def test_validation_rejects_claim_without_source(self) -> None:
        report = ResearchReport(
            title="Missing source",
            summary="Claim has no citation.",
            key_findings=[ReportClaim(text="Uncited claim", source_urls=[])],
            sources_used=["https://faa.gov/bvlos"],
            confidence=0.7,
        )

        with self.assertRaisesRegex(ReportValidationError, "claim_without_source"):
            validate_report_sources(
                report,
                [EvidenceRecord(url="https://faa.gov/bvlos", title="FAA", claims=["FAA claim"], credibility_score=0.9)],
            )


if __name__ == "__main__":
    unittest.main()
