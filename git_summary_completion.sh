#!/usr/bin/env bash

_git_summary() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # All available options
    opts="--emails -e --email-contains -ec --days -d --weeks -w --months -m --years -y --dir-level -dl --diverged-from -df --salary -s --pure-cocomo -p --incremental-cocomo -ic"

    # Handle option arguments
    case "${prev}" in
        --emails|-e)
            # Complete with git email addresses
            COMPREPLY=( $(compgen -W "$(git log --format='%ae' | sort -u)" -- ${cur}) )
            return 0
            ;;
        --email-contains|-ec|--salary|-s|--days|-d|--weeks|-w|--months|-m|--years|-y|--dir-level|-dl)
            # These options expect numeric values, no completion needed
            return 0
            ;;
        --diverged-from|-df)
            # Complete with git branches
            COMPREPLY=( $(compgen -W "$(git branch --format='%(refname:short)')" -- ${cur}) )
            return 0
            ;;
        *)
            # Complete with all available options
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
    esac
}

# Register completion for both the Python script and git subcommand
complete -F _git_summary ./git_summary.py
complete -F _git_summary git-summary

# Enable git-summary as a git subcommand completion
if declare -F __git_complete >/dev/null; then
    __git_complete summary _git_summary
fi
