# Git Summary Tool

A command-line tool that generates comprehensive summaries of git repository activity.

![Git Summary Tool Screenshot](screenshot.png)

## Features

- Filter commits by email address(es) or email pattern
- Analyze commits within specific time periods (days, weeks, months, years)
- Calculate commit frequency statistics (per day/week/month)
- Categorize commits (Features, Fixes, Improvements, etc.)
- Show heavy changes and recent activity
- Analyze impact on directories with configurable depth levels
- Display COCOMO calculation and estimated development cost of the considered commits
- Colorized output for better readability

## Installation

1. Clone this repository
2. Make the script executable:
```bash
chmod +x git_summary.py
```

## Usage

Basic usage:
```bash
./git_summary.py [options]
```

### Options

- `--emails`, `-e`: Filter commits by specific email addresses
- `--email-contains`, `-ec`: Filter commits by emails containing a string
- Time period options (mutually exclusive):
  - `--days`, `-d`: Show commits from last N days
  - `--weeks`, `-w`: Show commits from last N weeks
  - `--months`, `-m`: Show commits from last N months
  - `--years`, `-y`: Show commits from last N years
- `--dir-level`, `-dl`: Directory level for impact analysis (default: 1)
Branch option:
- `--diverged-from`, `-df`: Only consider commits that diverged from specified branch
- `--salary`, `-s`: Average yearly salary in EUR for COCOMO cost estimation (default: 50000)
- `--pure-cocomo`, `-p`: Use pure COCOMO calculation (considers only net added lines)
- `--iterative-cocomo`, `-ic`: Display iterative COCOMO metrics (each commit added net lines contribute to total line count)

### Examples

Show all commits from the last 30 days:
```bash
./git_summary.py --days 30
```

Show only your commits from the last 30 days:
```bash
./git_summary.py --days 30 --emails $(git config user.email)
```

Show commits from specific email addresses:
```bash
./git_summary.py --emails user1@example.com user2@example.com
```

Show commits from the last 2 weeks for emails containing "company.com":
```bash
./git_summary.py --weeks 2 --email-contains company.com
```

Analyze modules at directory level 2:
```bash
./git_summary.py --dir-level 2
```

## Output

The tool provides:
- Total commit count and commit frequency
- Total lines changed (additions/deletions) with COCOMO estimates
- Commits categorized by type (Features, Fixes, etc.) with impact stats
- Top 5 commits with most changes
- Recent activity (last 5 dates with commits)
- Files impact analysis showing file counts and line changes

## Requirements

- Python 3.6+
- Git repository

## COCOMO Disclaimer

The COCOMO metrics provided by this tool should be interpreted with caution:

- The Basic COCOMO model used here is a simplified version from 1981 and may not accurately reflect modern development practices
- The model assumes a waterfall-style development process rather than agile/iterative approaches
- Estimates are based purely on lines of code, which is an imperfect measure of project complexity
- The tool provides two COCOMO calculation modes:
  - Pure mode: Only considers net added lines (additions minus deletions)
  - Iterative mode: Considers the impact of each commit's changes
- Results should be used as rough indicators rather than precise estimates
- Actual project costs and timelines depend on many factors not captured by COCOMO

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
