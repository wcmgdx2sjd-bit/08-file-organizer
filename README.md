# File Organizer

Project 08 of Brandon's Python learning journey.

This command-line program organizes files into folders based on file type. It previews every planned move by default and requires an explicit `--apply` option before changing files.

## Learning Goals

- Work with paths using Python's `pathlib` module
- Inspect files and extensions
- Create directories safely
- Move files without overwriting existing data
- Add command-line arguments
- Use a dry-run mode before changing files
- Write automated tests for filesystem behavior
- Practice a consistent Git and GitHub workflow

## Completed Milestones

1. ✅ List files in a selected directory.
2. ✅ Identify each file's extension.
3. ✅ Map extensions into Documents, Images, Audio, Video, Archives, and Other.
4. ✅ Preview planned moves without changing files.
5. ✅ Create category folders only after explicit approval.
6. ✅ Move files safely while preventing name collisions.
7. ✅ Add a preview-first command-line interface and complete automated coverage.
8. ✅ Add optional recursive organization with nested-folder collision safety.
9. ✅ Add JSON move receipts and preview-first, collision-safe undo.
10. ✅ Add explicit, safe undo support for relocated directories.

## Safety Rules

- Never organize the current project directory by default.
- Never overwrite an existing file.
- Ignore directories and process files only.
- Preview actions before applying them.
- Skip existing category folders during recursive scans.
- Test with disposable sample files first.

## Requirements

- Python 3.10 or newer
- No third-party packages required

## Current Verified Status

All ten milestones are complete, with 43 automated tests. Reusable file operations live in `organizer.py`, while `main.py` remains a thin command-line interface. Coverage includes recursive discovery, category-folder skipping, explicit approval, portable JSON move receipts, SHA-256 content verification, preview-first undo, and atomic collision safety.

## Preview Changes

Preview mode does not change files:

```bash
python3 main.py /path/to/test-directory
```

Windows PowerShell:

```powershell
python main.py "C:\path\to\test-directory"
```

## Include Nested Folders

Use `--recursive` to preview files inside nested folders:

```bash
python3 main.py /path/to/test-directory --recursive
```

After reviewing the preview, apply it explicitly:

```bash
python3 main.py /path/to/test-directory --recursive --apply
```

Each file is organized beside its current location. Existing category folders are skipped, and one collision blocks every planned move.

## Apply Changes

After reviewing the preview, explicitly approve the operation:

```bash
python3 main.py /path/to/test-directory --apply
```

Windows PowerShell:

```powershell
python main.py "C:\path\to\test-directory" --apply
```

Always test with disposable sample files before organizing important data.

## Create a Move Receipt

Use `--receipt` with an approved operation to record every move:

```bash
python3 main.py /path/to/test-directory --recursive --apply --receipt move-receipt.json
```

The receipt stores portable relative source and destination paths, a SHA-256 fingerprint of each file, and the category folders created by the operation. An existing receipt is never overwritten, and `--receipt` requires explicit `--apply` approval. The complete receipt is written before movement begins; if receipt writing fails, no files are moved.

## Undo an Organized Move

Preview the rollback without changing files:

```bash
python3 main.py --undo move-receipt.json
```

After reviewing the preview, explicitly approve the rollback:

```bash
python3 main.py --undo move-receipt.json --apply
```

If the organized directory has moved or been renamed, provide its current location:

```bash
python3 main.py --undo move-receipt.json --undo-directory /current/path
```

Add `--apply` only after reviewing the relocated preview. The override must be an existing directory and never changes the receipt.

Undo cannot be combined with a directory, `--receipt`, or `--recursive`. Preview and apply run the same complete preflight, validating every source, destination, collision, and recorded SHA-256 fingerprint before showing or moving anything. A missing file, changed file, invalid receipt, or collision blocks the complete rollback. After restoring files, undo removes only the recorded organizer-created folders that are empty; pre-existing or non-empty folders remain untouched. The receipt remains as an audit record.

## Repository Location

Windows:

```text
C:\Users\bphil\Documents\Codex\08-file-organizer
```

Ubuntu/WSL:

```text
/mnt/c/Users/bphil/Documents/Codex/08-file-organizer
```

Both paths point to the same files.

## Author

Created by Brandon Phlipot as part of a hands-on Python and automation learning plan.
