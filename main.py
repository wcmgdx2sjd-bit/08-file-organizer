"""Project 08: build a safe command-line file organizer."""

import argparse
import json
import sys
from pathlib import Path


from organizer import (
    build_move_receipt,
    create_category_folders,
    inspect_move_receipt,
    move_files,
    parse_category_rules,
    plan_moves,
    plan_undo_directories,
    plan_undo_moves,
    preflight_moves,
    preflight_undo_moves,
    undo_files,
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
        nargs="?",
        help="Directory containing files to organize.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Create category folders and move files.",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help=(
            "Include nested folders while skipping existing "
            "category folders."
        ),
    )
    parser.add_argument(
        "--rules",
        type=Path,
        help="Load additional category rules from a JSON file.",
    )
    parser.add_argument(
        "--receipt",
        type=Path,
        help=(
            "Write a JSON move receipt after a successful "
            "--apply operation."
        ),
    )
    parser.add_argument(
        "--undo",
        type=Path,
        help="Preview or apply rollback from a JSON move receipt.",
    )
    parser.add_argument(
        "--undo-directory",
        type=Path,
        help=(
            "Use a relocated directory as the root for --undo "
            "or --receipt-status."
        ),
    )
    parser.add_argument(
        "--receipt-status",
        type=Path,
        help="Print a read-only JSON move-receipt status report.",
    )
    return parser.parse_args(arguments)


def run(
    arguments,
    output=sys.stdout,
    error_output=sys.stderr,
) -> int:
    """Preview planned moves or apply them with explicit approval."""
    if arguments.receipt_status is not None:
        if (
            arguments.directory is not None
            or arguments.apply
            or arguments.recursive
            or arguments.receipt is not None
            or arguments.undo is not None
            or arguments.rules is not None
        ):
            print(
                "Error: --receipt-status cannot be combined "
                "with organizer or undo options.",
                file=error_output,
            )
            return 1

        receipt_path = Path(arguments.receipt_status)

        try:
            receipt = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )
            status_report = inspect_move_receipt(
                receipt,
                arguments.undo_directory,
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as error:
            print(
                f"Error: invalid move receipt: {error}",
                file=error_output,
            )
            return 1

        json.dump(
            status_report,
            output,
            indent=2,
            sort_keys=True,
        )
        print(file=output)
        return 0 if status_report["status"] == "completed" else 1

    if (
        arguments.undo_directory is not None
        and arguments.undo is None
    ):
        print(
            "Error: --undo-directory requires --undo.",
            file=error_output,
        )
        return 1

    if (
        arguments.undo is not None
        and (
            arguments.receipt is not None
            or arguments.recursive
            or arguments.rules is not None
        )
    ):
        print(
            "Error: --undo cannot be combined with "
            "--receipt, --recursive, or --rules.",
            file=error_output,
        )
        return 1

    if arguments.receipt is not None and not arguments.apply:
        print(
            "Error: --receipt requires --apply.",
            file=error_output,
        )
        return 1

    if (
        arguments.undo is not None
        and arguments.directory is not None
    ):
        print(
            "Error: directory cannot be used with --undo.",
            file=error_output,
        )
        return 1

    if arguments.undo is not None:
        receipt_path = Path(arguments.undo)

        try:
            receipt = json.loads(
                receipt_path.read_text(encoding="utf-8")
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
        ) as error:
            print(
                f"Error: invalid move receipt: {error}",
                file=error_output,
            )
            return 1

        try:
            undo_moves = plan_undo_moves(
                receipt,
                arguments.undo_directory,
            )

            directory = Path(
                receipt["directory"]
                if arguments.undo_directory is None
                else arguments.undo_directory
            ).resolve()

            if not directory.exists():
                raise FileNotFoundError(
                    f"undo directory does not exist: {directory}"
                )

            if not directory.is_dir():
                raise NotADirectoryError(
                    f"undo path is not a directory: {directory}"
                )

            undo_directories = plan_undo_directories(
                receipt,
                directory,
            )
            preflight_undo_moves(
                undo_moves,
                directory,
            )
        except (OSError, ValueError) as error:
            print(
                f"Error: {error}",
                file=error_output,
            )
            return 1

        for source, destination in undo_moves:
            relative_source = source.relative_to(directory)
            relative_destination = destination.relative_to(directory)
            action = "UNDO" if arguments.apply else "UNDO PREVIEW"
            print(
                f"{action}: "
                f"{relative_source} -> {relative_destination}",
                file=output,
            )

        if not arguments.apply:
            print(
                "No files were changed. Use --apply to approve.",
                file=output,
            )
            return 0

        try:
            undo_files(
                undo_moves,
                directory,
                approved=True,
            )
        except (OSError, ValueError) as error:
            print(
                f"Error: {error}",
                file=error_output,
            )
            return 1

        for created_directory in undo_directories:
            if (
                created_directory.is_dir()
                and not any(created_directory.iterdir())
            ):
                created_directory.rmdir()

        print(
            f"Restored {len(undo_moves)} file(s).",
            file=output,
        )
        return 0

    if arguments.directory is None:
        print(
            "Error: provide a directory or --undo receipt.",
            file=error_output,
        )
        return 1

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

    category_rules = None

    if arguments.rules is not None:
        try:
            rules_document = json.loads(
                Path(arguments.rules).read_text(encoding="utf-8")
            )
            category_rules = parse_category_rules(
                rules_document
            )
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            ValueError,
        ) as error:
            print(
                f"Error: invalid rules file: {error}",
                file=error_output,
            )
            return 1

    planned_moves = plan_moves(
        directory,
        recursive=arguments.recursive,
        category_rules=category_rules,
    )

    for source, destination in planned_moves:
        relative_source = source.relative_to(directory)
        relative_destination = destination.relative_to(directory)
        action = "MOVE" if arguments.apply else "PREVIEW"
        print(
            f"{action}: {relative_source} -> {relative_destination}",
            file=output,
        )

    if not arguments.apply:
        print(
            "No files were changed. Use --apply to approve.",
            file=output,
        )
        return 0

    receipt_path = (
        Path(arguments.receipt)
        if arguments.receipt is not None
        else None
    )
    receipt_created = False
    created_directories = sorted(
        {
            destination.parent
            for _, destination in planned_moves
            if not destination.parent.exists()
        },
        key=lambda folder: len(folder.parts),
        reverse=True,
    )

    try:
        preflight_moves(planned_moves)

        if receipt_path is not None:
            if receipt_path.exists():
                raise FileExistsError(
                    f"receipt already exists: {receipt_path}"
                )

            if not receipt_path.parent.is_dir():
                raise FileNotFoundError(
                    "receipt directory does not exist: "
                    f"{receipt_path.parent}"
                )

            receipt = build_move_receipt(
                directory,
                planned_moves,
            )

            with receipt_path.open(
                "x",
                encoding="utf-8",
            ) as receipt_file:
                receipt_created = True
                json.dump(
                    receipt,
                    receipt_file,
                    indent=2,
                    sort_keys=True,
                )
                receipt_file.write("\n")

        create_category_folders(planned_moves, approved=True)
        move_files(planned_moves, approved=True)
    except (OSError, ValueError) as error:
        rollback_complete = all(
            source.is_file() and not destination.exists()
            for source, destination in planned_moves
        )

        if rollback_complete:
            for created_directory in created_directories:
                if (
                    created_directory.is_dir()
                    and not any(created_directory.iterdir())
                ):
                    created_directory.rmdir()

            if receipt_path is not None and receipt_created:
                try:
                    receipt_path.unlink()
                except OSError:
                    pass

        print(
            f"Error: {error}",
            file=error_output,
        )
        return 1

    print(
        f"Moved {len(planned_moves)} file(s).",
        file=output,
    )

    if receipt_path is not None:
        print(
            f"Receipt: {receipt_path}",
            file=output,
        )

    return 0


def main() -> None:
    """Run the File Organizer command-line interface."""
    raise SystemExit(run(parse_args()))


if __name__ == "__main__":
    main()
