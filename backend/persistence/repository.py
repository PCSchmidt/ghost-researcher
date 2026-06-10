"""Research job persistence skeletons."""

from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4


class ResearchRepository(Protocol):
    """Storage boundary for research job state."""

    def save(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def update(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any] | None: ...

    def get(self, job_id: str) -> dict[str, Any] | None: ...


@dataclass(frozen=True, slots=True)
class StoredResearchJob:
    """Serialized job payload plus stable persistence metadata."""

    job_id: str
    created_at: str
    updated_at: str
    payload: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "payload": deepcopy(self.payload),
        }

    def response_payload(self) -> dict[str, Any]:
        payload = deepcopy(self.payload)
        payload["job_id"] = self.job_id
        payload["created_at"] = self.created_at
        payload["updated_at"] = self.updated_at
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "StoredResearchJob":
        return cls(
            job_id=str(payload["job_id"]),
            created_at=str(payload["created_at"]),
            updated_at=str(payload["updated_at"]),
            payload=dict(payload["payload"]),
        )


class InMemoryResearchRepository:
    """Process-local repository for tests and dependency-free local runs."""

    def __init__(self) -> None:
        self._jobs: dict[str, StoredResearchJob] = {}

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        job = _new_job(payload)
        self._jobs[job.job_id] = job
        return job.response_payload()

    def update(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        existing = self._jobs.get(job_id)
        if existing is None:
            return None
        updated = _update_job(existing, payload)
        self._jobs[job_id] = updated
        return updated.response_payload()

    def get(self, job_id: str) -> dict[str, Any] | None:
        job = self._jobs.get(job_id)
        if job is None:
            return None
        return job.response_payload()


class JsonFileResearchRepository:
    """JSON-file repository that preserves job state across process restarts."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)

    def save(self, payload: dict[str, Any]) -> dict[str, Any]:
        jobs = self._read_jobs()
        job = _new_job(payload)
        jobs[job.job_id] = job
        self._write_jobs(jobs)
        return job.response_payload()

    def update(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any] | None:
        jobs = self._read_jobs()
        existing = jobs.get(job_id)
        if existing is None:
            return None
        updated = _update_job(existing, payload)
        jobs[job_id] = updated
        self._write_jobs(jobs)
        return updated.response_payload()

    def get(self, job_id: str) -> dict[str, Any] | None:
        job = self._read_jobs().get(job_id)
        if job is None:
            return None
        return job.response_payload()

    def _read_jobs(self) -> dict[str, StoredResearchJob]:
        if not self._path.exists():
            return {}
        with self._path.open("r", encoding="utf-8") as handle:
            raw_payload = json.load(handle)
        if not isinstance(raw_payload, dict):
            return {}
        jobs = raw_payload.get("jobs", {})
        if not isinstance(jobs, dict):
            return {}
        return {job_id: StoredResearchJob.from_dict(job) for job_id, job in jobs.items() if isinstance(job, dict)}

    def _write_jobs(self, jobs: dict[str, StoredResearchJob]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {"jobs": {job_id: job.to_dict() for job_id, job in jobs.items()}},
                handle,
                indent=2,
                sort_keys=True,
            )
        tmp_path.replace(self._path)


def _new_job(payload: dict[str, Any]) -> StoredResearchJob:
    timestamp = datetime.now(UTC).isoformat()
    return StoredResearchJob(
        job_id=str(uuid4()),
        created_at=timestamp,
        updated_at=timestamp,
        payload=deepcopy(payload),
    )


def _update_job(existing: StoredResearchJob, payload: dict[str, Any]) -> StoredResearchJob:
    """Replace a stored job's payload, preserving its id and creation time."""
    return StoredResearchJob(
        job_id=existing.job_id,
        created_at=existing.created_at,
        updated_at=datetime.now(UTC).isoformat(),
        payload=deepcopy(payload),
    )
