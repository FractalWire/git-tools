#!/usr/bin/env python3
import subprocess
import datetime
import argparse
from collections import defaultdict

def parse_args():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Generate a summary of git commits')
    email_group = parser.add_mutually_exclusive_group()
    email_group.add_argument('--emails', '-e', nargs='+', help='Email addresses to filter commits by')
    email_group.add_argument('--email-contains', '-ec', help='Filter commits by emails containing this string')
    
    # Time period options
    time_group = parser.add_mutually_exclusive_group()
    time_group.add_argument('--days', '-d', type=int, help='Show commits from last N days')
    time_group.add_argument('--weeks', '-w', type=int, help='Show commits from last N weeks')
    time_group.add_argument('--months', '-m', type=int, help='Show commits from last N months')
    time_group.add_argument('--years', '-y', type=int, help='Show commits from last N years')
    
    # Module level option
    parser.add_argument('--module-level', '-ml', type=int, default=1,
                       help='Directory level to consider as modules (default: 1)')
    
    return parser.parse_args()

def get_emails_by_pattern(pattern):
    """Get all email addresses from git log that contain the given pattern"""
    cmd = ['git', 'log', '--format=%ae']
    result = subprocess.run(cmd, capture_output=True, text=True)
    all_emails = set(result.stdout.strip().split('\n'))
    return [e for e in all_emails if pattern in e]

def get_user_commits(emails=None, days=None, weeks=None, months=None, years=None, with_files=False):
    """Get all commits by specified emails or current user within time period"""
    if not emails:
        # Get current user's email if none specified
        email_cmd = ['git', 'config', 'user.email']
        email_result = subprocess.run(email_cmd, capture_output=True, text=True)
        emails = [email_result.stdout.strip()]

    # Build the author pattern for multiple emails
    author_args = [('--author', email) for email in emails]
    authors = [item for args in author_args for item in args]
    
    # Build time period argument
    time_arg = []
    if days:
        time_arg = ['--since', f'{days} days ago']
    elif weeks:
        time_arg = ['--since', f'{weeks} weeks ago']
    elif months:
        time_arg = ['--since', f'{months} months ago']
    elif years:
        time_arg = ['--since', f'{years} years ago']
    
    # Get commit info
    format_str = '--pretty=format:%H<sep>%s<sep>%ad' + ('<sep>%b' if with_files else '')
    cmd = ['git', 'log', format_str, '--date=short', '--numstat'] + authors + time_arg
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()
    
    if not output:
        return []
    
    # Parse the output which now includes numstat information
    commits = []
    current_commit = None
    
    for line in output.split('\n'):
        if '<sep>' in line:  # This is a commit header
            if current_commit:
                commits.append(current_commit)
            parts = line.split('<sep>')
            hash_id, subject, date = parts[:3]
            current_commit = {
                'hash': hash_id,
                'subject': subject,
                'date': date,
                'files': []
            }
        elif line.strip():  # This is a stat line
            try:
                added, deleted, filename = line.split('\t')
                if added != '-' and deleted != '-':
                    current_commit['files'].append({
                        'name': filename,
                        'added': int(added),
                        'deleted': int(deleted)
                    })
            except ValueError:
                continue
    
    if current_commit:
        commits.append(current_commit)
    
    return commits

def parse_commit(commit):
    """Parse a commit into structured format"""
    if not commit or commit.get('subject', '').startswith('Merge branch'):
        return None
    
    parsed = {
        'hash': commit['hash'],
        'subject': commit['subject'],
        'date': datetime.datetime.strptime(commit['date'], '%Y-%m-%d').date(),
        'files': commit.get('files', [])
    }
    
    # Add convenience properties for total changes
    parsed['added'] = sum(f['added'] for f in parsed['files'])
    parsed['deleted'] = sum(f['deleted'] for f in parsed['files'])
    
    return parsed

def categorize_commit(subject):
    """Basic categorization of commits based on common prefixes"""
    subject = subject.lower()
    if any(word in subject for word in ['fix', 'bug', 'issue']):
        return 'Fixes'
    if any(word in subject for word in ['feat', 'add', 'new']):
        return 'Features'
    if any(word in subject for word in ['refactor', 'clean', 'improve']):
        return 'Improvements'
    if any(word in subject for word in ['test']):
        return 'Tests'
    if any(word in subject for word in ['doc']):
        return 'Documentation'
    return 'Other'

def get_module_name(file_path, level=1):
    """Extract module name from file path under apps/"""
    if file_path.startswith('apps/'):
        parts = file_path.split('/')
        if len(parts) > level + 1:
            module_parts = parts[1:level+1]
        elif len(parts) > 1:
            # If we've reached max level, use the full remaining path
            module_parts = parts[1:]
        else:
            return None
            
        # Remove .py extension if present
        if module_parts[-1].endswith('.py'):
            module_parts[-1] = module_parts[-1][:-3]
            
        return '.'.join(module_parts)
    return None

def group_files_by_module(commit, module_level):
    """Group files in a commit by their module"""
    files_by_module = defaultdict(list)
    
    for file in commit.get('files', []):
        module = get_module_name(file['name'], module_level)
        if module:
            files_by_module[module].append(file)
    
    return files_by_module

def distribute_changes(commit, files_by_module, module_stats):
    """Distribute commit changes by module"""
    for module, files in files_by_module.items():
        module_stats[module]['files'].update(f['name'] for f in files)
        module_stats[module]['added'] += sum(f['added'] for f in files)
        module_stats[module]['deleted'] += sum(f['deleted'] for f in files)

def format_module_stats(module_stats):
    """Convert module stats dict to sorted list by impact"""
    module_list = [
        {
            'name': module,
            'files': len(stats['files']),
            'added': stats['added'],
            'deleted': stats['deleted'],
            'total_impact': stats['added'] + stats['deleted']
        }
        for module, stats in module_stats.items()
    ]
    
    return sorted(module_list, key=lambda x: x['total_impact'], reverse=True)

def analyze_modules(commits, module_level=1):
    """Analyze impact on modules under apps/"""
    module_stats = defaultdict(lambda: {'files': set(), 'added': 0, 'deleted': 0})
    
    for commit in commits:
        files_by_module = group_files_by_module(commit, module_level)
        distribute_changes(commit, files_by_module, module_stats)
    
    return format_module_stats(module_stats)

def generate_summary(emails=None, email_contains=None, days=None, weeks=None, months=None, years=None, module_level=1):
    if email_contains:
        emails = get_emails_by_pattern(email_contains)
    commits = get_user_commits(emails, days, weeks, months, years, with_files=True)
    if not commits or (len(commits) == 1 and not commits[0]):
        print("No commits found")
        return

    parsed_commits = [parse_commit(c) for c in commits if parse_commit(c)]
    
    # Group by date
    commits_by_date = defaultdict(list)
    for commit in parsed_commits:
        commits_by_date[commit['date']].append(commit)

    # Group by category
    categories = defaultdict(int)
    for commit in parsed_commits:
        category = categorize_commit(commit['subject'])
        categories[category] += 1

    # Print summary
    print("\n=== Git Commit Summary ===\n")
    
    if emails:
        print("Commits by:", ", ".join(emails))
    else:
        print("Commits by: current user")
    print("\nTotal commits:", len(parsed_commits))
    
    # Calculate total lines changed
    total_added = sum(commit['added'] for commit in parsed_commits)
    total_deleted = sum(commit['deleted'] for commit in parsed_commits)
    print(f"Lines changed: +{total_added} -{total_deleted}")
    
    print("\nCommits by category:")
    for category, count in sorted(categories.items()):
        category_commits = [c for c in parsed_commits if categorize_commit(c['subject']) == category]
        category_added = sum(c['added'] for c in category_commits)
        category_deleted = sum(c['deleted'] for c in category_commits)
        print(f"    {category}: {count} commits (+{category_added} -{category_deleted})")

    # Show commits with most changes
    print("\nHeavy changes (top 5):")
    heavy_commits = sorted(
        parsed_commits,
        key=lambda x: x['added'] + x['deleted'],
        reverse=True
    )[:5]
    for commit in heavy_commits:
        total_changes = commit['added'] + commit['deleted']
        print(f"    {commit['hash'][:7]} {commit['subject']} ({total_changes} lines: +{commit['added']} -{commit['deleted']})")

    print("\nRecent activity:")
    for date in sorted(commits_by_date.keys(), reverse=True)[:5]:
        print(f"    {date}:")
        for commit in commits_by_date[date]:
            print(f"        {commit['hash'][:7]} {commit['subject']} (+{commit['added']} -{commit['deleted']})")

    # Show module impact (top 5)
    modules = analyze_modules(parsed_commits, module_level)
    if modules:
        print(f"\nModule impact (top 10, level {module_level}):")
        for module in modules[:10]:
            print(f"    {module['name']}: {module['files']} files changed +{module['added']} -{module['deleted']} (total impact: {module['total_impact']})")

if __name__ == '__main__':
    args = parse_args()
    generate_summary(
        args.emails, args.email_contains,
        args.days, args.weeks, args.months, args.years,
        args.module_level
    )
