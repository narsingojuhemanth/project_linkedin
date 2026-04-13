# LinkedIn Easy Apply Assistant (Config-Driven)

> ⚠️ **Important**: Automating LinkedIn actions may violate LinkedIn Terms of Service and can risk account restrictions.
> This tool is provided for educational/personal workflow use. Start with `dry_run: true`.

This project gives you a configurable bot to:

- Search jobs on LinkedIn with your custom filters
- Target **Easy Apply** jobs only
- Fill common form fields from a profile file
- Track each application + status history in SQLite

## What is already ready end-to-end

- Config and profile examples you can copy and edit
- One-command init flow to create local files
- Login + Easy Apply loop with retry over multi-step flows
- Persistent tracking DB for discovered/applied/failed jobs
- CLI for run/report/manual status updates

## Prerequisites

- Python 3.10+
- LinkedIn account credentials
- Resume file path on your machine

## Quick Start

1. Install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   playwright install chromium
   pip install -e .
   ```

2. Initialize files:
   ```bash
   linkedin-bot init
   ```

3. Edit `config.yaml` and `profile.yaml`.

4. (Optional but recommended) store secrets in `.env` and use placeholders:
   ```env
   LINKEDIN_EMAIL=you@example.com
   LINKEDIN_PASSWORD=your-password
   ```
   In `config.yaml`:
   ```yaml
   linkedin:
     email: "${LINKEDIN_EMAIL}"
     password: "${LINKEDIN_PASSWORD}"
   ```

5. Run dry-run first:
   ```bash
   linkedin-bot run --config config.yaml --profile profile.yaml
   ```

6. View progress report:
   ```bash
   linkedin-bot report --db data/applications.db
   ```

## Personalization for your profile/resume

I cannot directly read your LinkedIn profile page or attached resume in this environment. You should paste your real details into `profile.yaml` and point to your local resume file.

## Commands

- `linkedin-bot init`
- `linkedin-bot run --config config.yaml --profile profile.yaml`
- `linkedin-bot report --db data/applications.db`
- `linkedin-bot update-status <job_id> <status> --note "..."`

## Safe rollout

1. Keep `runtime.dry_run: true` until you confirm job targeting is correct.
2. Keep `max_applications_per_run` low (5-10).
3. Disable dry-run when ready.
4. Review failed records and update `screening_answers`.
