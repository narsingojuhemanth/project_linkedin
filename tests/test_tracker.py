from linkedin_easy_apply.models import ApplicationStatus, JobCard
from linkedin_easy_apply.tracker import ApplicationTracker


def test_tracker_insert_and_update(tmp_path):
    db_path = tmp_path / "apps.db"
    tracker = ApplicationTracker(str(db_path))

    job = JobCard(
        linkedin_job_id="123",
        title="Software Engineer",
        company="Acme",
        location="Remote",
        easy_apply=True,
        url="https://example.com",
    )

    tracker.upsert_discovered(job)
    assert tracker.exists("123")

    tracker.update_status("123", ApplicationStatus.APPLIED, "Submitted")
    stats = tracker.stats()
    assert stats[ApplicationStatus.APPLIED.value] == 1

    recent = tracker.recent(limit=1)
    assert len(recent) == 1
    assert recent[0].linkedin_job_id == "123"
