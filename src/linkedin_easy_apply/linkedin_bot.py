from __future__ import annotations

import re
import time
from typing import Iterable
from urllib.parse import quote_plus

from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

from .config import AppConfig, UserProfile
from .models import ApplicationStatus, JobCard
from .tracker import ApplicationTracker


class LinkedinEasyApplyBot:
    def __init__(self, config: AppConfig, profile: UserProfile, tracker: ApplicationTracker):
        self.config = config
        self.profile = profile
        self.tracker = tracker

    def run(self) -> None:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self.config.runtime.headless)
            context = browser.new_context()
            page = context.new_page()

            self._login(page)
            jobs = list(self._collect_jobs(page))
            applied = 0

            for job in jobs:
                if applied >= self.config.runtime.max_applications_per_run:
                    break
                if self.tracker.exists(job.linkedin_job_id):
                    continue
                if not self._is_match(job):
                    continue

                self.tracker.upsert_discovered(job)
                if self.config.runtime.dry_run:
                    self.tracker.update_status(job.linkedin_job_id, ApplicationStatus.IN_PROGRESS, "Dry run - skipped apply")
                    continue

                ok = self._easy_apply(page, job)
                if ok:
                    applied += 1
                    self.tracker.update_status(job.linkedin_job_id, ApplicationStatus.APPLIED, "Submitted via Easy Apply")
                else:
                    self.tracker.update_status(job.linkedin_job_id, ApplicationStatus.FAILED, "Failed during Easy Apply flow")

                time.sleep(self.config.runtime.delay_seconds_between_actions)

            context.close()
            browser.close()

    def _login(self, page: Page) -> None:
        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
        page.fill("input#username", self.config.linkedin.email)
        page.fill("input#password", self.config.linkedin.password)
        page.click("button[type='submit']")

        # Allow time for captcha/2FA approval when required.
        page.wait_for_timeout(self.config.runtime.wait_for_manual_login_seconds * 1000)

    def _collect_jobs(self, page: Page) -> Iterable[JobCard]:
        keywords = quote_plus(" OR ".join(self.config.search.keywords) if self.config.search.keywords else "Software Engineer")
        location = quote_plus(self.config.search.locations[0] if self.config.search.locations else "United States")

        query_parts = [f"keywords={keywords}", f"location={location}"]
        if self.config.search.easy_apply_only:
            query_parts.append("f_AL=true")
        if self.config.search.remote_only:
            query_parts.append("f_WT=2")
        if self.config.search.date_posted == "past_24_hours":
            query_parts.append("f_TPR=r86400")
        elif self.config.search.date_posted == "past_week":
            query_parts.append("f_TPR=r604800")
        elif self.config.search.date_posted == "past_month":
            query_parts.append("f_TPR=r2592000")

        page.goto(f"https://www.linkedin.com/jobs/search/?{'&'.join(query_parts)}", wait_until="domcontentloaded")
        page.wait_for_timeout(2500)

        cards = page.query_selector_all("li.jobs-search-results__list-item")
        for card in cards:
            title = (card.query_selector("h3") or card).inner_text().strip()
            company = (card.query_selector("h4") or card).inner_text().strip()
            loc_node = card.query_selector(".job-search-card__location")
            location_text = loc_node.inner_text().strip() if loc_node else ""
            link_node = card.query_selector("a")
            url = link_node.get_attribute("href") if link_node else ""
            job_id = self._extract_job_id(url, fallback=f"{company}-{title}")

            yield JobCard(
                linkedin_job_id=job_id,
                title=title,
                company=company,
                location=location_text,
                easy_apply=True,
                url=url,
            )

    def _easy_apply(self, page: Page, job: JobCard) -> bool:
        page.goto(job.url, wait_until="domcontentloaded")
        page.wait_for_timeout(1200)

        easy_apply_button = page.query_selector("button.jobs-apply-button")
        if not easy_apply_button:
            return False

        easy_apply_button.click()
        page.wait_for_timeout(1000)

        for _ in range(8):
            self._fill_common_fields(page)

            submit = page.query_selector("button[aria-label='Submit application']")
            if submit and submit.is_enabled():
                submit.click()
                page.wait_for_timeout(1200)
                return True

            next_button = page.query_selector("button[aria-label='Continue to next step']")
            if next_button and next_button.is_enabled():
                next_button.click()
                page.wait_for_timeout(800)
                continue

            review_button = page.query_selector("button[aria-label='Review your application']")
            if review_button and review_button.is_enabled():
                review_button.click()
                page.wait_for_timeout(800)
                continue

            break

        dismiss = page.query_selector("button[aria-label='Dismiss']")
        if dismiss:
            dismiss.click()
            page.wait_for_timeout(300)

        return False

    def _fill_common_fields(self, page: Page) -> None:
        for question, answer in self.profile.screening_answers.items():
            try:
                label = page.query_selector(f"label:has-text('{question}')")
            except PlaywrightTimeoutError:
                continue

            if not label:
                continue
            for_attr = label.get_attribute("for")
            if not for_attr:
                continue
            field = page.query_selector(f"#{for_attr}")
            if field:
                field.fill(answer)

    def _extract_job_id(self, url: str, fallback: str) -> str:
        match = re.search(r"/(\d+)(?:[/?]|$)", url or "")
        if match:
            return match.group(1)
        return fallback.replace(" ", "-").lower()

    def _is_match(self, job: JobCard) -> bool:
        lowered_title = job.title.lower()
        lowered_company = job.company.lower()

        for blocked in self.config.filters.blacklisted_companies:
            if blocked.lower() in lowered_company:
                return False

        for keyword in self.config.filters.blacklisted_keywords:
            if keyword.lower() in lowered_title:
                return False

        score = self._match_score(job.title)
        return score >= self.config.filters.minimum_match_score

    def _match_score(self, title: str) -> float:
        title_tokens = set(re.findall(r"[a-zA-Z]+", title.lower()))
        if not title_tokens:
            return 0.0

        skill_tokens = set()
        for skill in self.profile.professional.skills + self.profile.professional.target_roles:
            skill_tokens.update(re.findall(r"[a-zA-Z]+", skill.lower()))

        overlap = len(title_tokens & skill_tokens)
        return overlap / len(title_tokens)
