# Latest backup policy

The project keeps exactly one managed backup reference: `backup-latest`.

## Current backup

Version `2.5.0(49)` is the initial backup:

`0fed557bcfa09ecdc45d996f2c8cb50c855188e3`

## When finalizing a backup

1. Commit the release and finish the required tests.
2. Run `bash tools/backup_latest.sh set <release-commit>`.
3. Do not create a new versioned backup tag. The command moves `backup-latest`, replacing the previous managed backup.

Use `bash tools/backup_latest.sh show` to verify the active backup.

## Reverting

After checking that the worktree is clean, run:

`bash tools/backup_latest.sh revert --confirm`

Historical `checkpoint-*` tags are kept as history; they are not additional managed backups.
