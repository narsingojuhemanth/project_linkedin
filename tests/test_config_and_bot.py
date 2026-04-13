from pathlib import Path

import pytest

from linkedin_easy_apply.config import load_app_config, load_user_profile
from linkedin_easy_apply.linkedin_bot import LinkedinEasyApplyBot
from linkedin_easy_apply.models import JobCard


class _Dummy:
    pass


def test_load_app_config_resolves_env(tmp_path, monkeypatch):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        """
linkedin:
  email: "${LINKEDIN_EMAIL}"
  password: "${LINKEDIN_PASSWORD}"
runtime: {}
search: {}
filters: {}
files: {}
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("LINKEDIN_EMAIL", "a@b.com")
    monkeypatch.setenv("LINKEDIN_PASSWORD", "secret")

    loaded = load_app_config(str(cfg))
    assert loaded.linkedin.email == "a@b.com"
    assert loaded.linkedin.password == "secret"


def test_load_user_profile_requires_resume_file(tmp_path):
    profile = tmp_path / "profile.yaml"
    profile.write_text(
        """
personal:
  full_name: "X"
  phone: "1"
  city: "C"
  country: "US"
  visa_status: "Yes"
  years_of_experience: 2
professional:
  title: "Engineer"
  skills: ["Python"]
  target_roles: ["Engineer"]
resume:
  file_path: "/not/found.pdf"
screening_answers: {}
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_user_profile(str(profile))


def test_extract_job_id_fallback():
    bot = LinkedinEasyApplyBot(_Dummy(), _Dummy(), _Dummy())
    job = JobCard("1", "Engineer", "Acme", "Remote", True, "https://www.linkedin.com/jobs/view/1234567890/")
    assert bot._extract_job_id(job.url, "fallback") == "1234567890"
    assert bot._extract_job_id("", "Acme Engineer") == "acme-engineer"
