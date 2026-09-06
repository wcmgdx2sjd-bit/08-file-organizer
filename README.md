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

## Safety Rules

- Never organize the current project directory by default.
- Never overwrite an existing file.
- Ignore directories and process files only.
- Preview actions before applying them.
- Test with disposable sample files first.

## Requirements

- Python 3.10 or newer
- No third-party packages required

## Current Verified Status

All seven milestones are complete, with 10 automated tests covering preview behavior, explicit approval, folder creation, file movement, and collision safety.

## Preview Changes

Preview mode does not change files:

```bash
python3 main.py /path/to/test-directory
```

Windows PowerShell:

```powershell
python main.py "C:\path\to\test-directory"
```

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
