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


def create_category_folders(
    planned_moves: list[tuple[Path, Path]],
    *,
    approved: bool,
) -> list[Path]:
    """Create planned category folders only after explicit approval."""
    if approved is not True:
        return []

    folders = set()

    for source, destination in planned_moves:
        source = Path(source)
        destination = Path(destination)
        category_folder = destination.parent

        if category_folder.parent != source.parent:
            raise ValueError(
                "planned destination must stay inside "
                "the source directory."
            )

        folders.add(category_folder)

    ordered_folders = sorted(
        folders,
        key=lambda folder: folder.name.casefold(),
    )

    for folder in ordered_folders:
        folder.mkdir(exist_ok=True)

    return ordered_folders


def move_files(
    planned_moves: list[tuple[Path, Path]],
    *,
    approved: bool,
) -> list[Path]:
    """Move planned files only after approval and a safe preflight."""
    if approved is not True:
        return []

    validated_moves = []
    destinations = set()

    for source, destination in planned_moves:
        source = Path(source)
        destination = Path(destination)

        if destination.parent.parent != source.parent:
            raise ValueError(
                "planned destination must stay inside "
                "the source directory."
            )

        if not source.is_file():
            raise FileNotFoundError(
                f"source file does not exist: {source}"
            )

        if not destination.parent.is_dir():
            raise FileNotFoundError(
                f"category folder does not exist: "
                f"{destination.parent}"
            )

        if destination.exists():
            raise FileExistsError(
                f"destination already exists: {destination}"
            )

        if destination in destinations:
            raise FileExistsError(
                f"duplicate destination planned: {destination}"
            )

        validated_moves.append((source, destination))
        destinations.add(destination)

    moved = []

    for source, destination in validated_moves:
        source.rename(destination)
        moved.append(destination)

    return moved


def plan_moves(directory: Path) -> list[tuple[Path, Path]]:
    """Return proposed source and destination paths without moving files."""
    directory = Path(directory)

    return [
        (
            file_path,
            directory / file_category(file_path) / file_path.name,
        )
        for file_path in list_files(directory)
    ]


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
    print("File Organizer milestone 6 is complete.")
    print("Next milestone: add complete automated filesystem coverage.")


if __name__ == "__main__":
    main()
