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

    def test_in_memory_update_replaces_payload_and_preserves_identity(self) -> None:
        repository = InMemoryResearchRepository()
        running = repository.save({"status": "running", "synthesis": None})

        updated = repository.update(running["job_id"], {"status": "completed", "synthesis": {"title": "Done"}})

        self.assertIsNotNone(updated)
        self.assertEqual(running["job_id"], updated["job_id"])
        self.assertEqual(running["created_at"], updated["created_at"])
        self.assertEqual("completed", updated["status"])
        self.assertEqual("completed", repository.get(running["job_id"])["status"])

    def test_update_returns_none_for_missing_job(self) -> None:
        repository = InMemoryResearchRepository()

        self.assertIsNone(repository.update("missing-job", {"status": "completed"}))

    def test_list_returns_all_jobs(self) -> None:
        repository = InMemoryResearchRepository()
        a = repository.save({"status": "completed"})
        b = repository.save({"status": "running"})

        listed = repository.list()

        self.assertEqual(2, len(listed))
        self.assertEqual({a["job_id"], b["job_id"]}, {row["job_id"] for row in listed})

    def test_empty_repository_lists_nothing(self) -> None:
        self.assertEqual([], InMemoryResearchRepository().list())

    def test_json_repository_update_persists_across_instances(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "research_jobs.json"
            repository = JsonFileResearchRepository(path)
            running = repository.save({"status": "running", "synthesis": None})

            repository.update(running["job_id"], {"status": "completed", "synthesis": None})
            fetched = JsonFileResearchRepository(path).get(running["job_id"])

        self.assertEqual("completed", fetched["status"])
        self.assertEqual(running["job_id"], fetched["job_id"])


if __name__ == "__main__":
    unittest.main()