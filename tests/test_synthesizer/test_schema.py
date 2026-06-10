"""Regression tests for report schema validation."""

from __future__ import annotations

import unittest

from backend.agent.memory import EvidenceRecord
from backend.synthesizer.schema import (
    Reference,
    ReportClaim,
    ReportParagraph,
    ReportSection,
    ReportValidationError,
    ResearchReport,
    validate_report_sources,
)


def _long_form_report() -> ResearchReport:
    return ResearchReport(
        title="Data Center Efficiency in 2025",
        summary="Hyperscalers adopt liquid cooling.",
        key_findings=[ReportClaim(text="Liquid cooling cuts PUE.", source_urls=["https://a.gov/x"])],
        sources_used=["https://a.gov/x", "https://b.org/y"],
        confidence=0.75,
        abstract="This report surveys data-center efficiency strategies in 2025.",
        sections=[
            ReportSection(
                heading="Cooling",
                paragraphs=[
                    ReportParagraph(text="Direct-to-chip cooling lowers PUE.", citations=["https://a.gov/x"]),
                    ReportParagraph(text="Adoption is accelerating.", citations=["https://b.org/y"]),
                ],
            )
        ],
        conclusion="Efficiency gains are driven primarily by cooling and siting.",
        references=[
            Reference(url="https://a.gov/x", title="A", credibility_score=0.9),
            Reference(url="https://b.org/y", title="B", credibility_score=0.6),
        ],
    )


def _evidence() -> list[EvidenceRecord]:
    return [
        EvidenceRecord(url="https://a.gov/x", title="A", claims=["c"], credibility_score=0.9),
        EvidenceRecord(url="https://b.org/y", title="B", claims=["c"], credibility_score=0.6),
    ]


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

    def test_long_form_report_round_trips_and_validates(self) -> None:
        report = _long_form_report()

        restored = ResearchReport.from_dict(report.to_dict())

        self.assertEqual(report, restored)
        self.assertTrue(restored.is_long_form)
        self.assertEqual(2, len(restored.sections[0].paragraphs))
        self.assertEqual(2, len(restored.references))
        # Must not raise — every citation/reference is in evidence.
        validate_report_sources(restored, _evidence())

    def test_validation_rejects_unsupported_in_text_citation(self) -> None:
        report = _long_form_report()
        bad = ResearchReport(
            **{
                **{f.name: getattr(report, f.name) for f in report.__dataclass_fields__.values()},
                "sections": [
                    ReportSection(
                        heading="Cooling",
                        paragraphs=[ReportParagraph(text="Bad cite.", citations=["https://evil.com/not-evidence"])],
                    )
                ],
            }
        )

        with self.assertRaisesRegex(ReportValidationError, "unsupported_citation"):
            validate_report_sources(bad, _evidence())

    def test_validation_rejects_unsupported_reference(self) -> None:
        report = _long_form_report()
        bad = ResearchReport(
            **{
                **{f.name: getattr(report, f.name) for f in report.__dataclass_fields__.values()},
                "references": [Reference(url="https://evil.com/not-evidence", title="X")],
            }
        )

        with self.assertRaisesRegex(ReportValidationError, "unsupported_reference"):
            validate_report_sources(bad, _evidence())

    def test_flat_skeleton_report_is_not_long_form(self) -> None:
        report = ResearchReport(
            title="t",
            summary="s",
            key_findings=[ReportClaim(text="c", source_urls=["https://a.gov/x"])],
            sources_used=["https://a.gov/x"],
            confidence=0.5,
        )

        self.assertFalse(report.is_long_form)
        self.assertEqual([], report.to_dict()["sections"])


if __name__ == "__main__":
    unittest.main()
