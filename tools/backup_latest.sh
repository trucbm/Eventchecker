#!/usr/bin/env bash
set -euo pipefail

BACKUP_TAG="${BACKUP_TAG:-backup-latest}"

usage() {
    cat <<'USAGE'
Usage:
  bash tools/backup_latest.sh show
  bash tools/backup_latest.sh set [<commit-or-ref>]
  bash tools/backup_latest.sh revert --confirm

The repository keeps one managed backup ref: backup-latest.
`set` moves that ref and therefore replaces the previous backup.
`revert` is deliberately guarded because it resets the current worktree.
USAGE
}

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

resolve_commit() {
    git rev-parse --verify "$1^{commit}" 2>/dev/null
}

require_clean_worktree() {
    if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
        echo "Refusing to continue: the worktree is not clean." >&2
        echo "Commit or stash changes before this operation." >&2
        exit 1
    fi
}

show_backup() {
    local commit
    if ! commit="$(resolve_commit "$BACKUP_TAG")"; then
        echo "No managed backup exists: $BACKUP_TAG" >&2
        exit 1
    fi
    git show -s --format="%H%n%ad%n%s" --date=iso "$commit"
}

set_backup() {
    local target="${1:-HEAD}"
    local commit

    if [[ "$target" == "HEAD" ]]; then
        require_clean_worktree
    fi
    if ! commit="$(resolve_commit "$target")"; then
        echo "Invalid commit or ref: $target" >&2
        exit 1
    fi

    git tag -f "$BACKUP_TAG" "$commit" >/dev/null
    echo "Managed backup updated: $BACKUP_TAG -> $(git rev-parse --short "$commit")"
    git show -s --format="%H%n%ad%n%s" --date=iso "$commit"
}

revert_to_backup() {
    if [[ "${1:-}" != "--confirm" ]]; then
        echo "Revert changes the current worktree. Run: bash tools/backup_latest.sh revert --confirm" >&2
        exit 2
    fi
    require_clean_worktree

    local commit
    if ! commit="$(resolve_commit "$BACKUP_TAG")"; then
        echo "No managed backup exists: $BACKUP_TAG" >&2
        exit 1
    fi
    git reset --hard "$commit"
    echo "Reverted to managed backup: $BACKUP_TAG -> $(git rev-parse --short "$commit")"
}

case "${1:-}" in
    show)
        show_backup
        ;;
    set)
        set_backup "${2:-HEAD}"
        ;;
    revert)
        revert_to_backup "${2:-}"
        ;;
    *)
        usage
        exit 2
        ;;
esac
