"""Reusable core operations for the safe File Organizer."""

import hashlib
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




def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file without changing it."""
    digest = hashlib.sha256()

    with Path(path).open("rb") as source_file:
        for chunk in iter(
            lambda: source_file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def build_move_receipt(
    directory: Path,
    planned_moves: list[tuple[Path, Path]],
) -> dict:
    """Return a portable JSON-ready receipt without changing files."""
    directory = Path(directory).resolve()
    receipt_moves = []
    created_directories = set()

    for source, destination in planned_moves:
        source = Path(source).resolve()
        destination = Path(destination).resolve()

        if not source.is_relative_to(directory):
            raise ValueError(
                f"source must stay inside directory: {source}"
            )

        if not destination.is_relative_to(directory):
            raise ValueError(
                f"destination must stay inside directory: "
                f"{destination}"
            )

        if not destination.parent.exists():
            created_directories.add(
                destination
                .parent
                .relative_to(directory)
                .as_posix()
            )

        receipt_moves.append(
            {
                "source": source.relative_to(directory).as_posix(),
                "destination": (
                    destination
                    .relative_to(directory)
                    .as_posix()
                ),
                "sha256": file_sha256(source),
            }
        )

    return {
        "receipt_version": 1,
        "directory": str(directory),
        "created_directories": sorted(
            created_directories,
            key=str.casefold,
        ),
        "moves": receipt_moves,
    }


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


def preflight_moves(
    planned_moves: list[tuple[Path, Path]],
) -> list[tuple[Path, Path]]:
    """Validate every planned move before changing the filesystem."""
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

    return validated_moves


def move_files(
    planned_moves: list[tuple[Path, Path]],
    *,
    approved: bool,
) -> list[Path]:
    """Move preflighted files only after explicit approval."""
    if approved is not True:
        return []

    validated_moves = preflight_moves(planned_moves)

    for _, destination in validated_moves:
        if not destination.parent.is_dir():
            raise FileNotFoundError(
                f"category folder does not exist: "
                f"{destination.parent}"
            )

    moved = []

    for source, destination in validated_moves:
        source.rename(destination)
        moved.append(destination)

    return moved




def undo_files(
    planned_moves: list[tuple[Path, Path]],
    directory: Path,
    *,
    approved: bool,
) -> list[Path]:
    """Restore receipt moves only after complete validated approval."""
    if approved is not True:
        return []

    directory = Path(directory).resolve()
    validated_moves = []
    destinations = set()

    for source, destination in planned_moves:
        source = Path(source).resolve()
        destination = Path(destination).resolve()

        if not source.is_relative_to(directory):
            raise ValueError(
                f"undo source must stay inside directory: {source}"
            )

        if not destination.is_relative_to(directory):
            raise ValueError(
                "undo destination must stay inside directory: "
                f"{destination}"
            )

        if not source.is_file():
            raise FileNotFoundError(
                f"undo source file does not exist: {source}"
            )

        if destination.exists():
            raise FileExistsError(
                f"undo destination already exists: {destination}"
            )

        if destination in destinations:
            raise FileExistsError(
                f"duplicate undo destination: {destination}"
            )

        if not destination.parent.is_dir():
            raise FileNotFoundError(
                "undo destination directory does not exist: "
                f"{destination.parent}"
            )

        validated_moves.append((source, destination))
        destinations.add(destination)

    restored = []

    for source, destination in validated_moves:
        source.rename(destination)
        restored.append(destination)

    return restored



def plan_undo_directories(receipt: dict) -> list[Path]:
    """Return safe receipt-created directories in removal order."""
    created_directories = receipt.get("created_directories", [])

    if not isinstance(created_directories, list):
        raise ValueError(
            "receipt created_directories must be a list."
        )

    directory = Path(receipt["directory"]).resolve()
    destination_parents = {
        (
            directory / move["destination"]
        ).resolve().parent
        for move in receipt["moves"]
        if (
            isinstance(move, dict)
            and isinstance(move.get("destination"), str)
        )
    }
    planned_directories = []
    seen_directories = set()

    for relative_path in created_directories:
        if (
            not isinstance(relative_path, str)
            or not relative_path.strip()
        ):
            raise ValueError(
                "receipt created directory must be non-empty text."
            )

        created_path = (
            directory / relative_path
        ).resolve()

        if not created_path.is_relative_to(directory):
            raise ValueError(
                "receipt created directory resolves outside "
                "directory."
            )

        if created_path not in destination_parents:
            raise ValueError(
                "receipt created directory is not a recorded "
                "destination folder."
            )

        if created_path in seen_directories:
            raise ValueError(
                "duplicate receipt created directory."
            )

        planned_directories.append(created_path)
        seen_directories.add(created_path)

    return sorted(
        planned_directories,
        key=lambda folder: len(folder.parts),
        reverse=True,
    )


def plan_undo_moves(
    receipt: dict,
) -> list[tuple[Path, Path]]:
    """Return validated rollback moves without changing files."""
    allowed_keys = (
        {
            "receipt_version",
            "directory",
            "moves",
        },
        {
            "receipt_version",
            "directory",
            "moves",
            "created_directories",
        },
    )

    if (
        not isinstance(receipt, dict)
        or set(receipt) not in allowed_keys
    ):
        raise ValueError("invalid move receipt structure.")

    if receipt["receipt_version"] != 1:
        raise ValueError("unsupported move receipt version.")

    if (
        not isinstance(receipt["directory"], str)
        or not receipt["directory"].strip()
    ):
        raise ValueError("receipt directory must be non-empty text.")

    if not isinstance(receipt["moves"], list):
        raise ValueError("receipt moves must be a list.")

    directory = Path(receipt["directory"]).resolve()
    undo_moves = []

    for move in reversed(receipt["moves"]):
        allowed_keys = (
            {"source", "destination"},
            {"source", "destination", "sha256"},
        )

        if (
            not isinstance(move, dict)
            or set(move) not in allowed_keys
        ):
            raise ValueError("invalid move receipt entry.")

        source_text = move["source"]
        destination_text = move["destination"]

        if (
            not isinstance(source_text, str)
            or not source_text.strip()
            or not isinstance(destination_text, str)
            or not destination_text.strip()
        ):
            raise ValueError(
                "receipt paths must be non-empty text."
            )

        original_path = (directory / source_text).resolve()
        organized_path = (
            directory / destination_text
        ).resolve()

        if not original_path.is_relative_to(directory):
            raise ValueError(
                "receipt source resolves outside directory."
            )

        if not organized_path.is_relative_to(directory):
            raise ValueError(
                "receipt destination resolves outside directory."
            )

        expected_sha256 = move.get("sha256")

        if expected_sha256 is not None:
            if (
                not isinstance(expected_sha256, str)
                or len(expected_sha256) != 64
                or any(
                    character not in "0123456789abcdef"
                    for character in expected_sha256
                )
            ):
                raise ValueError(
                    "receipt SHA-256 must be 64 lowercase "
                    "hexadecimal characters."
                )

            if (
                organized_path.is_file()
                and file_sha256(organized_path) != expected_sha256
            ):
                raise ValueError(
                    "organized file content changed: "
                    f"{organized_path}"
                )

        undo_moves.append(
            (organized_path, original_path)
        )

    return undo_moves


def plan_moves(
    directory: Path,
    *,
    recursive: bool = False,
) -> list[tuple[Path, Path]]:
    """Return proposed source and destination paths without moving files."""
    directory = Path(directory)

    return [
        (
            file_path,
            file_path.parent
            / file_category(file_path)
            / file_path.name,
        )
        for file_path in list_files(
            directory,
            recursive=recursive,
        )
    ]


def list_files(
    directory: Path,
    *,
    recursive: bool = False,
) -> list[Path]:
    """Return eligible files sorted by their relative paths."""
    directory = Path(directory)
    category_names = set(extension_categories) | {"Other"}
    candidates = (
        directory.rglob("*")
        if recursive
        else directory.iterdir()
    )

    return sorted(
        (
            entry
            for entry in candidates
            if (
                entry.is_file()
                and not any(
                    part in category_names
                    for part in entry.relative_to(directory).parts[:-1]
                )
            )
        ),
        key=lambda entry: (
            entry.relative_to(directory).as_posix().casefold()
        ),
    )
