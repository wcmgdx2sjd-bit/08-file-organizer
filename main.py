"""Project 08: build a safe command-line file organizer."""

from pathlib import Path


def file_extension(path: Path) -> str:
    """Return the file extension normalized to lowercase."""
    return Path(path).suffix.lower()


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
    print("Next milestone: map extensions into file categories.")


if __name__ == "__main__":
    main()
