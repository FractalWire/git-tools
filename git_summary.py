#!/usr/bin/env python3
import subprocess
import datetime
import argparse
from collections import defaultdict


# ANSI color codes
class Colors:
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    RESET = "\033[0m"


def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Generate a summary of git commits")
    email_group = parser.add_mutually_exclusive_group()
    email_group.add_argument(
        "--emails", "-e", nargs="+", help="Email addresses to filter commits by"
    )
    email_group.add_argument(
        "--email-contains",
        "-ec",
        help="Filter commits by emails containing this string",
    )

    # Time period options
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument(
        "--days", "-d", type=int, help="Show commits from last N days"
    )
    time_group.add_argument(
        "--weeks", "-w", type=int, help="Show commits from last N weeks"
    )
    time_group.add_argument(
        "--months", "-m", type=int, help="Show commits from last N months"
    )
    time_group.add_argument(
        "--years", "-y", type=int, help="Show commits from last N years"
    )

    # Directory level option
    parser.add_argument(
        "--dir-level",
        "-dl",
        type=int,
        default=1,
        help="Directory depth level for impact analysis (default: 1)",
    )

    return parser.parse_args()


def get_emails_by_pattern(pattern):
    """Get all email addresses from git log that contain the given pattern"""
    cmd = ["git", "log", "--format=%ae"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    all_emails = set(result.stdout.strip().split("\n"))
    return [e for e in all_emails if pattern in e]


def get_user_commits(
    emails=None, days=None, weeks=None, months=None, years=None, with_files=False
):
    """Get all commits by specified emails or current user within time period"""
    if not emails:
        # Get current user's email if none specified
        email_cmd = ["git", "config", "user.email"]
        email_result = subprocess.run(email_cmd, capture_output=True, text=True)
        emails = [email_result.stdout.strip()]

    # Track which emails actually have commits
    active_emails = set()

    all_commits = []
    # Query commits for each email separately to track which ones are active
    for email in emails:
        author_args = ["--author", email]

        # Build time period argument
        time_arg = []
        if days:
            time_arg = ["--since", f"{days} days ago"]
        elif weeks:
            time_arg = ["--since", f"{weeks} weeks ago"]
        elif months:
            time_arg = ["--since", f"{months} months ago"]
        elif years:
            time_arg = ["--since", f"{years} years ago"]

        # Get commit info
        format_str = "--pretty=format:%H<sep>%s<sep>%ad" + ("<sep>%b" if with_files else "")
        cmd = ["git", "log", format_str, "--date=short", "--numstat"] + author_args + time_arg
        result = subprocess.run(cmd, capture_output=True, text=True)
        output = result.stdout.strip()

        if output:
            active_emails.add(email)
            all_commits.extend(parse_commit_output(output))

    if not all_commits:
        return [], set()

    return all_commits, active_emails

def parse_commit_output(output):
    """Parse the git log output into commit objects"""
    commits = []
    current_commit = None

    for line in output.split("\n"):
        if "<sep>" in line:  # This is a commit header
            if current_commit:
                commits.append(current_commit)
            parts = line.split("<sep>")
            hash_id, subject, date = parts[:3]
            current_commit = {
                "hash": hash_id,
                "subject": subject,
                "date": date,
                "files": [],
            }
        elif line.strip():  # This is a stat line
            try:
                added, deleted, filename = line.split("\t")
                if added != "-" and deleted != "-":
                    current_commit["files"].append(
                        {"name": filename, "added": int(added), "deleted": int(deleted)}
                    )
            except ValueError:
                continue

    if current_commit:
        commits.append(current_commit)

    return commits


def parse_commit(commit):
    """Parse a commit into structured format"""
    if not commit or commit.get("subject", "").startswith("Merge branch"):
        return None

    parsed = {
        "hash": commit["hash"],
        "subject": commit["subject"],
        "date": datetime.datetime.strptime(commit["date"], "%Y-%m-%d").date(),
        "files": commit.get("files", []),
    }

    # Add convenience properties for total changes
    parsed["added"] = sum(f["added"] for f in parsed["files"])
    parsed["deleted"] = sum(f["deleted"] for f in parsed["files"])

    return parsed


def categorize_commit(subject):
    """Basic categorization of commits based on common prefixes"""
    subject = subject.lower()
    if any(word in subject for word in ["fix", "bug", "issue"]):
        return "Fixes"
    if any(word in subject for word in ["feat", "add", "new"]):
        return "Features"
    if any(word in subject for word in ["refactor", "clean", "improve"]):
        return "Improvements"
    if any(word in subject for word in ["test"]):
        return "Tests"
    if any(word in subject for word in ["doc"]):
        return "Documentation"
    return "Other"


def get_directory_path(file_path, level=1):
    """Extract directory path up to specified level"""
    parts = file_path.split("/")
    
    if len(parts) > level:
        return "/".join(parts[:level])
    return "/".join(parts)


def group_files_by_directory(commit, dir_level):
    """Group files in a commit by their directory"""
    files_by_dir = defaultdict(list)

    for file in commit.get("files", []):
        directory = get_directory_path(file["name"], dir_level)
        if directory:
            files_by_dir[directory].append(file)

    return files_by_dir


def distribute_changes(commit, files_by_dir, dir_stats):
    """Distribute commit changes by directory"""
    for directory, files in files_by_dir.items():
        dir_stats[directory]["files"].update(f["name"] for f in files)
        dir_stats[directory]["added"] += sum(f["added"] for f in files)
        dir_stats[directory]["deleted"] += sum(f["deleted"] for f in files)


def calculate_frequency_stats(commits, total_days):
    """Calculate commit frequency statistics and return most relevant period"""
    if not commits or total_days == 0:
        return None, None

    commits_per_day = len(commits) / total_days
    commits_per_week = commits_per_day * 7
    commits_per_month = commits_per_day * 30.44  # Average days in a month

    # Find most relevant period
    if commits_per_day >= 1:
        return "day", round(commits_per_day, 1)
    elif commits_per_week >= 1:
        return "week", round(commits_per_week, 1)
    else:
        return "month", round(commits_per_month, 1)


def format_directory_stats(dir_stats):
    """Convert directory stats dict to sorted list by impact"""
    dir_list = [
        {
            "name": directory,
            "files": len(stats["files"]),
            "added": stats["added"],
            "deleted": stats["deleted"],
            "total_impact": stats["added"] + stats["deleted"],
        }
        for directory, stats in dir_stats.items()
    ]

    return sorted(dir_list, key=lambda x: x["total_impact"], reverse=True)


def analyze_directories(commits, dir_level=1):
    """Analyze impact on directories"""
    dir_stats = defaultdict(lambda: {"files": set(), "added": 0, "deleted": 0})

    for commit in commits:
        files_by_dir = group_files_by_directory(commit, dir_level)
        distribute_changes(commit, files_by_dir, dir_stats)

    return format_directory_stats(dir_stats)


def generate_summary(
    emails=None,
    email_contains=None,
    days=None,
    weeks=None,
    months=None,
    years=None,
    dir_level=1,
):
    if email_contains:
        emails = get_emails_by_pattern(email_contains)
    commits, active_emails = get_user_commits(emails, days, weeks, months, years, with_files=True)
    if not commits or (len(commits) == 1 and not commits[0]):
        print("No commits found")
        return

    parsed_commits = [parse_commit(c) for c in commits if parse_commit(c)]

    # Group by date
    commits_by_date = defaultdict(list)
    for commit in parsed_commits:
        commits_by_date[commit["date"]].append(commit)

    # Group by category
    categories = defaultdict(int)
    for commit in parsed_commits:
        category = categorize_commit(commit["subject"])
        categories[category] += 1

    # Print summary
    print(f"\n{Colors.CYAN}=== Git Commit Summary ==={Colors.RESET}\n")

    if active_emails:
        print(f"{Colors.BLUE}Commits by:{Colors.RESET}", ", ".join(active_emails))
    else:
        print(f"{Colors.BLUE}Commits by:{Colors.RESET} no active users found")
    print(f"\n{Colors.BLUE}Total commits:{Colors.RESET}", len(parsed_commits))

    # Calculate commit frequency
    if days:
        total_days = days
    elif weeks:
        total_days = weeks * 7
    elif years:
        total_days = years * 365
    else:
        total_days = (
            max(c["date"] for c in parsed_commits)
            - min(c["date"] for c in parsed_commits)
        ).days + 1

    period, frequency = calculate_frequency_stats(parsed_commits, total_days)
    if period and frequency:
        print(f"{Colors.BLUE}Commit frequency:{Colors.RESET} {frequency} per {period}")

    # Calculate total lines changed
    total_added = sum(commit["added"] for commit in parsed_commits)
    total_deleted = sum(commit["deleted"] for commit in parsed_commits)
    print(
        f"{Colors.BLUE}Lines changed:{Colors.RESET} {Colors.GREEN}+{total_added}{Colors.RESET} {Colors.RED}-{total_deleted}{Colors.RESET}"
    )

    print(f"\n{Colors.BLUE}Commits by category:{Colors.RESET}")
    for category, count in sorted(categories.items()):
        category_commits = [
            c for c in parsed_commits if categorize_commit(c["subject"]) == category
        ]
        category_added = sum(c["added"] for c in category_commits)
        category_deleted = sum(c["deleted"] for c in category_commits)
        print(
            f"    {Colors.YELLOW}{category}:{Colors.RESET} {count} commits ({Colors.GREEN}+{category_added}{Colors.RESET} {Colors.RED}-{category_deleted}{Colors.RESET})"
        )

    # Show commits with most changes
    print(f"\n{Colors.BLUE}Heavy changes (top 5):{Colors.RESET}")
    heavy_commits = sorted(
        parsed_commits, key=lambda x: x["added"] + x["deleted"], reverse=True
    )[:5]
    for commit in heavy_commits:
        total_changes = commit["added"] + commit["deleted"]
        print(
            f"    {Colors.YELLOW}{commit['hash'][:7]}{Colors.RESET} {commit['subject']} ({total_changes} lines: {Colors.GREEN}+{commit['added']}{Colors.RESET} {Colors.RED}-{commit['deleted']}{Colors.RESET})"
        )

    print(f"\n{Colors.BLUE}Recent activity:{Colors.RESET}")
    for date in sorted(commits_by_date.keys(), reverse=True)[:5]:
        print(f"    {Colors.CYAN}{date}:{Colors.RESET}")
        for commit in commits_by_date[date]:
            print(
                f"        {Colors.YELLOW}{commit['hash'][:7]}{Colors.RESET} {commit['subject']} ({Colors.GREEN}+{commit['added']}{Colors.RESET} {Colors.RED}-{commit['deleted']}{Colors.RESET})"
            )

    # Show directory impact (top 10)
    directories = analyze_directories(parsed_commits, dir_level)
    if directories:
        print(
            f"\n{Colors.BLUE}Files impact (top 10, level {dir_level}):{Colors.RESET}"
        )
        for directory in directories[:10]:
            print(
                f"    {Colors.YELLOW}{directory['name']}:{Colors.RESET} {directory['files']} files changed {Colors.GREEN}+{directory['added']}{Colors.RESET} {Colors.RED}-{directory['deleted']}{Colors.RESET} (total impact: {directory['total_impact']})"
            )


if __name__ == "__main__":
    args = parse_args()
    generate_summary(
        args.emails,
        args.email_contains,
        args.days,
        args.weeks,
        args.months,
        args.years,
        args.dir_level,
    )
