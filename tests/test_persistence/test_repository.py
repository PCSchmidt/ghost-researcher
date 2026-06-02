"""Regression tests for research job repositories."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from backend.persistence import InMemoryResearchRepository, JsonFileResearchRepository


def _payload() -> dict[str, object]:
    return {
        "status": "completed",
        "session": {"research_goal": "Review https://example.com/report"},
        "decisions": [],
        "tool_results": [],
        "synthesis": None,
    }


class ResearchRepositoryTests(unittest.TestCase):
    def test_in_memory_repository_saves_and_fetches_job(self) -> None:
        repository = InMemoryResearchRepository()

        stored = repository.save(_payload())
        fetched = repository.get(stored["job_id"])

        self.assertEqual(stored, fetched)
        self.assertEqual("completed", fetched["status"])
        self.assertIn("created_at", fetched)
        self.assertIn("updated_at", fetched)

    def test_json_repository_survives_new_instance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "research_jobs.json"
            first_repository = JsonFileResearchRepository(path)

            stored = first_repository.save(_payload())
            second_repository = JsonFileResearchRepository(path)
            fetched = second_repository.get(stored["job_id"])

        self.assertEqual(stored, fetched)
        self.assertEqual("Review https://example.com/report", fetched["session"]["research_goal"])

    def test_repository_returns_none_for_missing_job(self) -> None:
        repository = InMemoryResearchRepository()

        self.assertIsNone(repository.get("missing-job"))


if __name__ == "__main__":
    unittest.main()