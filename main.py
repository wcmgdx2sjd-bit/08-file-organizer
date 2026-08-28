"""Project 08: build a safe command-line file organizer."""

from pathlib import Path


def file_extension(path: Path) -> str:
    """Return the file extension normalized to lowercase."""
    return Path(path).suffix.lower()


extension_categories = {
    "Documents": {".doc", ".docx", ".pdf", ".txt"},
    "Images": {".gif", ".jpeg", ".jpg", ".png"},
    "Audio": {".flac", ".m4a", ".mp3", ".wav"},
    "Video": {".avi", ".mkv", ".mov", ".mp4"},
    "Archives": {".7z", ".gz", ".rar", ".tar", ".zip"},
}


def file_category(path: Path) -> str:
    """Return the category associated with a file's extension."""
    extension = file_extension(path)

    for category, extensions in extension_categories.items():
        if extension in extensions:
            return category

    return "Other"


def list_files(directory: Path) -> list[Path]:
    """Return direct child files sorted by name."""
    directory = Path(directory)

    return sorted(
        (
            entry
            for entry in directory.iterdir()
            if entry.is_file()
        ),
        key=lambda entry: entry.name.casefold(),
    )


def main() -> None:
    """Display the next implementation milestone."""
    print("File Organizer milestone 1 is complete.")
    print("Next milestone: preview planned moves without changing files.")


if __name__ == "__main__":
    main()
