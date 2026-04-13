from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, ValidationError, model_validator


class LinkedinConfig(BaseModel):
    email: str
    password: str


class RuntimeConfig(BaseModel):
    headless: bool = False
    dry_run: bool = True
    max_applications_per_run: int = 10
    delay_seconds_between_actions: float = 1.2
    wait_for_manual_login_seconds: int = 120


class SearchConfig(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    experience_levels: list[str] = Field(default_factory=list)
    date_posted: Literal["past_24_hours", "past_week", "past_month", "anytime"] = "past_week"
    remote_only: bool = True
    easy_apply_only: bool = True


class FiltersConfig(BaseModel):
    blacklisted_companies: list[str] = Field(default_factory=list)
    blacklisted_keywords: list[str] = Field(default_factory=list)
    minimum_match_score: float = 0.55


class FilesConfig(BaseModel):
    database_path: str = "data/applications.db"


class AppConfig(BaseModel):
    linkedin: LinkedinConfig
    runtime: RuntimeConfig
    search: SearchConfig
    filters: FiltersConfig
    files: FilesConfig


class PersonalProfile(BaseModel):
    full_name: str
    phone: str
    city: str
    country: str
    visa_status: str
    years_of_experience: int


class ProfessionalProfile(BaseModel):
    title: str
    skills: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    file_path: str


class UserProfile(BaseModel):
    personal: PersonalProfile
    professional: ProfessionalProfile
    resume: ResumeProfile
    screening_answers: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_resume_path(self) -> "UserProfile":
        resume = Path(self.resume.file_path)
        if not resume.exists():
            raise ValueError(f"Resume path does not exist: {resume}")
        return self


def _load_yaml(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Expected a mapping in {path}, got: {type(data).__name__}")
    return data


def _resolve_secret(value: str) -> str:
    if value.startswith("${") and value.endswith("}"):
        env_name = value[2:-1]
        env_val = os.getenv(env_name)
        if not env_val:
            raise ValueError(f"Missing environment variable: {env_name}")
        return env_val
    return value


def load_app_config(path: str) -> AppConfig:
    load_dotenv()
    raw = _load_yaml(Path(path))
    linkedin = raw.get("linkedin", {})
    if isinstance(linkedin, dict):
        if "email" in linkedin and isinstance(linkedin["email"], str):
            linkedin["email"] = _resolve_secret(linkedin["email"])
        if "password" in linkedin and isinstance(linkedin["password"], str):
            linkedin["password"] = _resolve_secret(linkedin["password"])

    try:
        return AppConfig.model_validate(raw)
    except ValidationError as exc:
        raise ValueError(f"Invalid app config: {exc}") from exc


def load_user_profile(path: str) -> UserProfile:
    try:
        return UserProfile.model_validate(_load_yaml(Path(path)))
    except ValidationError as exc:
        raise ValueError(f"Invalid user profile: {exc}") from exc
