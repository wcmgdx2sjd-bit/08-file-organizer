# File Organizer

Project 08 of Brandon's Python learning journey.

The goal is to build a command-line program that organizes files into folders based on file type. This repository begins with a safe scaffold so each feature can be implemented and understood incrementally.

## Learning Goals

- Work with paths using Python's `pathlib` module
- Inspect files and extensions
- Create directories safely
- Move files without overwriting existing data
- Add command-line arguments
- Use a dry-run mode before changing files
- Write automated tests for filesystem behavior
- Practice a consistent Git and GitHub workflow

## Planned Milestones

1. List files in a selected directory.
2. Identify each file's extension.
3. Map extensions into categories such as Documents, Images, Audio, Video, Archives, and Other.
4. Preview planned moves without changing files.
5. Create category folders when needed.
6. Move files safely while preventing name collisions.
7. Add automated tests.

## Safety Rules

- Never organize the current project directory by default.
- Never overwrite an existing file.
- Ignore directories and process files only.
- Preview actions before applying them.
- Test with disposable sample files first.

## Requirements

- Python 3.10 or newer
- No third-party packages are required for the initial version

## Run the Scaffold

```bash
python3 main.py
```

Windows PowerShell users can run:

```powershell
python main.py
```

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
