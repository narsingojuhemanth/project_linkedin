from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .config import load_app_config, load_user_profile
from .linkedin_bot import LinkedinEasyApplyBot
from .models import ApplicationStatus
from .tracker import ApplicationTracker

console = Console()


def cmd_init(args: argparse.Namespace) -> None:
    config_dst = Path(args.config)
    profile_dst = Path(args.profile)

    if not config_dst.exists():
        shutil.copyfile("config.example.yaml", config_dst)
        console.print(f"[green]Created {config_dst}[/green]")
    else:
        console.print(f"[yellow]Skipped {config_dst} (already exists)[/yellow]")

    if not profile_dst.exists():
        shutil.copyfile("profile.example.yaml", profile_dst)
        console.print(f"[green]Created {profile_dst}[/green]")
    else:
        console.print(f"[yellow]Skipped {profile_dst} (already exists)[/yellow]")

    console.print("[cyan]Next: update both files, then run `linkedin-bot run`.[/cyan]")


def cmd_run(args: argparse.Namespace) -> None:
    config = load_app_config(args.config)
    profile = load_user_profile(args.profile)

    tracker = ApplicationTracker(config.files.database_path)
    bot = LinkedinEasyApplyBot(config, profile, tracker)
    bot.run()
    console.print("[green]Run completed.[/green]")


def cmd_report(args: argparse.Namespace) -> None:
    tracker = ApplicationTracker(args.db)
    stats = tracker.stats()

    stats_table = Table(title="Application Status Counts")
    stats_table.add_column("Status")
    stats_table.add_column("Count", justify="right")
    for status, count in sorted(stats.items()):
        stats_table.add_row(status, str(count))
    console.print(stats_table)

    recent_table = Table(title="Recent Applications")
    recent_table.add_column("Job ID")
    recent_table.add_column("Title")
    recent_table.add_column("Company")
    recent_table.add_column("Status")
    recent_table.add_column("Updated")

    for item in tracker.recent(limit=20):
        updated_text = item.updated_at.isoformat() if item.updated_at else ""
        recent_table.add_row(item.linkedin_job_id, item.title, item.company, item.status.value, updated_text)
    console.print(recent_table)


def cmd_update_status(args: argparse.Namespace) -> None:
    tracker = ApplicationTracker(args.db)
    status = ApplicationStatus(args.status)
    tracker.update_status(args.job_id, status, args.note)
    console.print(f"[green]Updated {args.job_id} -> {status.value}[/green]")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="LinkedIn Easy Apply Assistant")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Create local config/profile files from examples")
    init_parser.add_argument("--config", default="config.yaml")
    init_parser.add_argument("--profile", default="profile.yaml")
    init_parser.set_defaults(func=cmd_init)

    run_parser = subparsers.add_parser("run", help="Run Easy Apply bot")
    run_parser.add_argument("--config", default="config.yaml")
    run_parser.add_argument("--profile", default="profile.yaml")
    run_parser.set_defaults(func=cmd_run)

    report_parser = subparsers.add_parser("report", help="Show application report")
    report_parser.add_argument("--db", default="data/applications.db")
    report_parser.set_defaults(func=cmd_report)

    status_parser = subparsers.add_parser("update-status", help="Manually update status")
    status_parser.add_argument("job_id")
    status_parser.add_argument(
        "status",
        choices=[s.value for s in ApplicationStatus],
        help="New status value",
    )
    status_parser.add_argument("--note", default="Manual update")
    status_parser.add_argument("--db", default="data/applications.db")
    status_parser.set_defaults(func=cmd_update_status)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
