"""Project 08: build a safe command-line file organizer."""

import argparse
import sys
from pathlib import Path


from organizer import (
    create_category_folders,
    move_files,
    plan_moves,
    preflight_moves,
)


def parse_args(arguments=None):
    """Parse safe File Organizer command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Preview file organization or apply it explicitly."
        )
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Directory containing files to organize.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create category folders and move files.",
    )
    return parser.parse_args(arguments)


def run(
    arguments,
    output=sys.stdout,
    error_output=sys.stderr,
) -> int:
    """Preview planned moves or apply them with explicit approval."""
    directory = Path(arguments.directory)

    if not directory.exists():
        print(
            f"Error: directory does not exist: {directory}",
            file=error_output,
        )
        return 1

    if not directory.is_dir():
        print(
            f"Error: path is not a directory: {directory}",
            file=error_output,
        )
        return 1

    planned_moves = plan_moves(directory)

    for source, destination in planned_moves:
        relative_destination = destination.relative_to(directory)
        action = "MOVE" if arguments.apply else "PREVIEW"
        print(
            f"{action}: {source.name} -> {relative_destination}",
            file=output,
        )

    if not arguments.apply:
        print(
            "No files were changed. Use --apply to approve.",
            file=output,
        )
        return 0

    try:
        preflight_moves(planned_moves)
        create_category_folders(planned_moves, approved=True)
        move_files(planned_moves, approved=True)
    except (OSError, ValueError) as error:
        print(
            f"Error: {error}",
            file=error_output,
        )
        return 1

    print(
        f"Moved {len(planned_moves)} file(s).",
        file=output,
    )
    return 0


def main() -> None:
    """Run the File Organizer command-line interface."""
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
