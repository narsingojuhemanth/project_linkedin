from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    DISCOVERED = "discovered"
    IN_PROGRESS = "in_progress"
    APPLIED = "applied"
    FAILED = "failed"
    REVIEWING = "reviewing"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    OFFER = "offer"


@dataclass
class JobCard:
    linkedin_job_id: str
    title: str
    company: str
    location: str
    easy_apply: bool
    url: str


@dataclass
class ApplicationRecord:
    linkedin_job_id: str
    title: str
    company: str
    location: str
    status: ApplicationStatus
    note: str
    applied_at: datetime | None = None
    updated_at: datetime | None = None
