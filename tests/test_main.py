import hashlib
import importlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from main import parse_args, run
from organizer import (
    build_move_receipt,
    create_category_folders,
    file_category,
    file_extension,
    list_files,
    move_files,
    plan_moves,
    plan_undo_moves,
    undo_files,
)


class FileOrganizerTests(unittest.TestCase):
    def test_lists_only_files_in_name_order(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            (directory / "zebra.txt").write_text(
                "text",
                encoding="utf-8",
            )
            (directory / "alpha.py").write_text(
                "python",
                encoding="utf-8",
            )
            (directory / "nested").mkdir()

            files = list_files(directory)

        self.assertEqual(
            [path.name for path in files],
            ["alpha.py", "zebra.txt"],
        )


    def test_identifies_normalized_file_extension(self):
        self.assertEqual(
            file_extension(Path("REPORT.PDF")),
            ".pdf",
        )
        self.assertEqual(
            file_extension(Path("README")),
            "",
        )


    def test_maps_files_into_categories(self):
        expected_categories = {
            "report.PDF": "Documents",
            "photo.JPG": "Images",
            "song.mp3": "Audio",
            "movie.MP4": "Video",
            "backup.zip": "Archives",
            "README": "Other",
            "script.py": "Other",
        }

        for filename, expected_category in expected_categories.items():
            with self.subTest(filename=filename):
                self.assertEqual(
                    file_category(Path(filename)),
                    expected_category,
                )


    def test_previews_moves_without_changing_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.PDF"
            photo = directory / "photo.jpg"
            script = directory / "script.py"

            for file_path in (report, photo, script):
                file_path.write_text("sample", encoding="utf-8")

            planned_moves = plan_moves(directory)

            self.assertEqual(
                planned_moves,
                [
                    (photo, directory / "Images" / "photo.jpg"),
                    (report, directory / "Documents" / "report.PDF"),
                    (script, directory / "Other" / "script.py"),
                ],
            )
            self.assertTrue(report.is_file())
            self.assertTrue(photo.is_file())
            self.assertTrue(script.is_file())
            self.assertFalse((directory / "Documents").exists())
            self.assertFalse((directory / "Images").exists())
            self.assertFalse((directory / "Other").exists())


    def test_creates_category_folders_only_after_approval(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            script = directory / "script.py"

            for file_path in (report, photo, script):
                file_path.write_text("sample", encoding="utf-8")

            existing_images = directory / "Images"
            existing_images.mkdir()
            keep_file = existing_images / "keep.txt"
            keep_file.write_text("keep", encoding="utf-8")

            planned_moves = plan_moves(directory)

            not_created = create_category_folders(
                planned_moves,
                approved=False,
            )

            self.assertEqual(not_created, [])
            self.assertFalse((directory / "Documents").exists())
            self.assertFalse((directory / "Other").exists())

            folders = create_category_folders(
                planned_moves,
                approved=True,
            )

            self.assertEqual(
                folders,
                [
                    directory / "Documents",
                    directory / "Images",
                    directory / "Other",
                ],
            )
            self.assertTrue((directory / "Documents").is_dir())
            self.assertTrue((directory / "Images").is_dir())
            self.assertTrue((directory / "Other").is_dir())
            self.assertEqual(
                keep_file.read_text(encoding="utf-8"),
                "keep",
            )
            self.assertTrue(report.is_file())
            self.assertTrue(photo.is_file())
            self.assertTrue(script.is_file())



    def test_rejects_category_folder_outside_source_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "report.pdf"
            source.write_text("sample", encoding="utf-8")
            outside = (
                directory.parent
                / f"{directory.name}-outside"
            )
            unsafe_destination = outside / "report.pdf"

            with self.assertRaisesRegex(
                ValueError,
                "must stay inside",
            ):
                create_category_folders(
                    [(source, unsafe_destination)],
                    approved=True,
                )

            self.assertFalse(outside.exists())



    def test_moves_files_only_after_explicit_approval(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            report.write_text("report contents", encoding="utf-8")
            photo.write_text("photo contents", encoding="utf-8")

            planned_moves = plan_moves(directory)
            create_category_folders(
                planned_moves,
                approved=True,
            )

            not_moved = move_files(
                planned_moves,
                approved=False,
            )

            self.assertEqual(not_moved, [])
            self.assertTrue(report.is_file())
            self.assertTrue(photo.is_file())

            moved = move_files(
                planned_moves,
                approved=True,
            )

            report_destination = (
                directory / "Documents" / "report.pdf"
            )
            photo_destination = (
                directory / "Images" / "photo.jpg"
            )

            self.assertEqual(
                moved,
                [photo_destination, report_destination],
            )
            self.assertFalse(report.exists())
            self.assertFalse(photo.exists())
            self.assertEqual(
                report_destination.read_text(encoding="utf-8"),
                "report contents",
            )
            self.assertEqual(
                photo_destination.read_text(encoding="utf-8"),
                "photo contents",
            )



    def test_collision_blocks_every_planned_move(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            photo = directory / "photo.jpg"
            report = directory / "report.pdf"
            photo.write_text("new photo", encoding="utf-8")
            report.write_text("new report", encoding="utf-8")

            planned_moves = plan_moves(directory)
            create_category_folders(
                planned_moves,
                approved=True,
            )

            existing_report = (
                directory / "Documents" / "report.pdf"
            )
            existing_report.write_text(
                "existing report",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                FileExistsError,
                "destination already exists",
            ):
                move_files(
                    planned_moves,
                    approved=True,
                )

            self.assertTrue(photo.is_file())
            self.assertTrue(report.is_file())
            self.assertFalse(
                (directory / "Images" / "photo.jpg").exists()
            )
            self.assertEqual(
                existing_report.read_text(encoding="utf-8"),
                "existing report",
            )



    def test_cli_previews_moves_without_changing_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")
            output = io.StringIO()

            arguments = parse_args([str(directory)])
            exit_code = run(arguments, output=output)

            self.assertEqual(exit_code, 0)
            self.assertIn(
                "PREVIEW: photo.jpg -> Images/photo.jpg",
                output.getvalue(),
            )
            self.assertIn(
                "PREVIEW: report.pdf -> Documents/report.pdf",
                output.getvalue(),
            )
            self.assertIn(
                "No files were changed. Use --apply to approve.",
                output.getvalue(),
            )
            self.assertTrue(photo.is_file())
            self.assertTrue(report.is_file())
            self.assertFalse((directory / "Images").exists())
            self.assertFalse((directory / "Documents").exists())


    def test_cli_apply_moves_files_after_explicit_approval(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn(
                "MOVE: photo.jpg -> Images/photo.jpg",
                result.stdout,
            )
            self.assertIn(
                "MOVE: report.pdf -> Documents/report.pdf",
                result.stdout,
            )
            self.assertIn("Moved 2 file(s).", result.stdout)
            self.assertFalse(photo.exists())
            self.assertFalse(report.exists())
            self.assertEqual(
                (
                    directory / "Images" / "photo.jpg"
                ).read_text(encoding="utf-8"),
                "photo",
            )
            self.assertEqual(
                (
                    directory / "Documents" / "report.pdf"
                ).read_text(encoding="utf-8"),
                "report",
            )


    def test_cli_reports_missing_directory_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            missing_directory = (
                Path(temporary_directory) / "does-not-exist"
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(missing_directory),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn(
                "Error: directory does not exist:",
                result.stderr,
            )
            self.assertIn(
                str(missing_directory),
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)


    def test_cli_rejects_file_path_without_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            file_path = Path(temporary_directory) / "report.pdf"
            file_path.write_text("report", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn(
                "Error: path is not a directory:",
                result.stderr,
            )
            self.assertIn(str(file_path), result.stderr)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                file_path.read_text(encoding="utf-8"),
                "report",
            )


    def test_cli_reports_collision_without_moving_or_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            source = directory / "report.pdf"
            photo = directory / "photo.jpg"
            source.write_text("new report", encoding="utf-8")
            photo.write_text("new photo", encoding="utf-8")

            documents = directory / "Documents"
            documents.mkdir()
            destination = documents / "report.pdf"
            destination.write_text(
                "existing report",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "MOVE: report.pdf -> Documents/report.pdf",
                result.stdout,
            )
            self.assertIn(
                "Error: destination already exists:",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                source.read_text(encoding="utf-8"),
                "new report",
            )
            self.assertEqual(
                photo.read_text(encoding="utf-8"),
                "new photo",
            )
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "existing report",
            )
            self.assertFalse((directory / "Images").exists())


    def test_core_operations_are_exposed_by_organizer_module(self):
        organizer = importlib.import_module("organizer")

        expected_operations = (
            "file_extension",
            "file_category",
            "list_files",
            "plan_moves",
            "create_category_folders",
            "preflight_moves",
            "move_files",
        )

        for operation in expected_operations:
            with self.subTest(operation=operation):
                self.assertTrue(
                    callable(getattr(organizer, operation, None))
                )


    def test_main_remains_a_thin_cli_module(self):
        source = (
            Path(__file__).parents[1] / "main.py"
        ).read_text(encoding="utf-8")

        self.assertIn("from organizer import (", source)

        for operation in (
            "file_extension",
            "file_category",
            "list_files",
            "plan_moves",
            "create_category_folders",
            "preflight_moves",
            "move_files",
        ):
            with self.subTest(operation=operation):
                self.assertNotIn(f"def {operation}(", source)


    def test_recursive_preview_plans_nested_files_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            nested = directory / "client"
            nested.mkdir()

            report = nested / "report.pdf"
            photo = nested / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            planned_moves = plan_moves(
                directory,
                recursive=True,
            )

            self.assertEqual(
                planned_moves,
                [
                    (
                        photo,
                        nested / "Images" / "photo.jpg",
                    ),
                    (
                        report,
                        nested / "Documents" / "report.pdf",
                    ),
                ],
            )
            self.assertTrue(photo.is_file())
            self.assertTrue(report.is_file())
            self.assertFalse((nested / "Images").exists())
            self.assertFalse((nested / "Documents").exists())


    def test_recursive_preview_skips_existing_category_folders(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            client = directory / "client"
            documents = client / "Documents"
            images = directory / "Images"
            documents.mkdir(parents=True)
            images.mkdir()

            unorganized = client / "notes.txt"
            organized_document = documents / "report.pdf"
            organized_image = images / "photo.jpg"

            unorganized.write_text("notes", encoding="utf-8")
            organized_document.write_text(
                "report",
                encoding="utf-8",
            )
            organized_image.write_text(
                "photo",
                encoding="utf-8",
            )

            planned_moves = plan_moves(
                directory,
                recursive=True,
            )

            self.assertEqual(
                planned_moves,
                [
                    (
                        unorganized,
                        client / "Documents" / "notes.txt",
                    ),
                ],
            )
            self.assertTrue(organized_document.is_file())
            self.assertTrue(organized_image.is_file())


    def test_cli_recursive_option_previews_nested_files(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            client = directory / "client"
            client.mkdir()
            report = client / "report.pdf"
            report.write_text("report", encoding="utf-8")
            output = io.StringIO()

            arguments = parse_args([
                str(directory),
                "--recursive",
            ])
            exit_code = run(arguments, output=output)

            self.assertEqual(exit_code, 0)
            self.assertIn(
                (
                    "PREVIEW: client/report.pdf -> "
                    "client/Documents/report.pdf"
                ),
                output.getvalue(),
            )
            self.assertIn(
                "No files were changed. Use --apply to approve.",
                output.getvalue(),
            )
            self.assertTrue(report.is_file())
            self.assertFalse(
                (client / "Documents").exists()
            )


    def test_cli_recursive_apply_moves_nested_files_safely(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            client = directory / "client"
            project = directory / "project"
            client.mkdir()
            project.mkdir()

            report = client / "report.pdf"
            photo = project / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--recursive",
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn(
                (
                    "MOVE: client/report.pdf -> "
                    "client/Documents/report.pdf"
                ),
                result.stdout,
            )
            self.assertIn(
                (
                    "MOVE: project/photo.jpg -> "
                    "project/Images/photo.jpg"
                ),
                result.stdout,
            )
            self.assertIn("Moved 2 file(s).", result.stdout)
            self.assertEqual(
                (
                    client / "Documents" / "report.pdf"
                ).read_text(encoding="utf-8"),
                "report",
            )
            self.assertEqual(
                (
                    project / "Images" / "photo.jpg"
                ).read_text(encoding="utf-8"),
                "photo",
            )
            self.assertFalse(report.exists())
            self.assertFalse(photo.exists())


    def test_recursive_collision_blocks_all_nested_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            client = directory / "client"
            project = directory / "project"
            documents = client / "Documents"
            client.mkdir()
            project.mkdir()
            documents.mkdir()

            report = client / "report.pdf"
            photo = project / "photo.jpg"
            destination = documents / "report.pdf"

            report.write_text("new report", encoding="utf-8")
            photo.write_text("new photo", encoding="utf-8")
            destination.write_text(
                "existing report",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--recursive",
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "Error: destination already exists:",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                report.read_text(encoding="utf-8"),
                "new report",
            )
            self.assertEqual(
                photo.read_text(encoding="utf-8"),
                "new photo",
            )
            self.assertEqual(
                destination.read_text(encoding="utf-8"),
                "existing report",
            )
            self.assertFalse((project / "Images").exists())


    def test_builds_portable_move_receipt_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            client = directory / "client"
            client.mkdir()

            report = client / "report.pdf"
            report.write_text("report", encoding="utf-8")
            planned_moves = [
                (
                    report,
                    client / "Documents" / "report.pdf",
                ),
            ]

            receipt = build_move_receipt(
                directory,
                planned_moves,
            )

            self.assertEqual(
                receipt,
                {
                    "receipt_version": 1,
                    "directory": str(directory.resolve()),
                    "created_directories": [
                        "client/Documents",
                    ],
                    "moves": [
                        {
                            "source": "client/report.pdf",
                            "destination": (
                                "client/Documents/report.pdf"
                            ),
                            "sha256": hashlib.sha256(
                                b"report"
                            ).hexdigest(),
                        },
                    ],
                },
            )
            self.assertTrue(report.is_file())
            self.assertFalse(
                (client / "Documents").exists()
            )


    def test_cli_apply_writes_json_move_receipt(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            receipt_path = directory / "move-receipt.json"
            report.write_text("report", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--apply",
                    "--receipt",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Moved 1 file(s).", result.stdout)
            self.assertIn(
                f"Receipt: {receipt_path}",
                result.stdout,
            )
            self.assertEqual(result.stderr, "")
            self.assertEqual(
                json.loads(
                    receipt_path.read_text(encoding="utf-8")
                ),
                {
                    "receipt_version": 1,
                    "directory": str(directory.resolve()),
                    "created_directories": ["Documents"],
                    "moves": [
                        {
                            "source": "report.pdf",
                            "destination": "Documents/report.pdf",
                            "sha256": hashlib.sha256(
                                b"report"
                            ).hexdigest(),
                        },
                    ],
                },
            )
            self.assertFalse(report.exists())
            self.assertTrue(
                (directory / "Documents" / "report.pdf").is_file()
            )


    def test_existing_receipt_blocks_all_moves_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            receipt_path = directory / "move-receipt.json"

            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")
            receipt_path.write_text(
                "existing receipt",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--apply",
                    "--receipt",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "Error: receipt already exists:",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                receipt_path.read_text(encoding="utf-8"),
                "existing receipt",
            )
            self.assertTrue(report.is_file())
            self.assertTrue(photo.is_file())
            self.assertFalse((directory / "Documents").exists())
            self.assertFalse((directory / "Images").exists())


    def test_plans_undo_moves_from_receipt_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            report = documents / "report.pdf"
            photo = images / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            receipt = {
                "receipt_version": 1,
                "directory": str(directory),
                "moves": [
                    {
                        "source": "report.pdf",
                        "destination": "Documents/report.pdf",
                    },
                    {
                        "source": "photo.jpg",
                        "destination": "Images/photo.jpg",
                    },
                ],
            }

            undo_moves = plan_undo_moves(receipt)

            self.assertEqual(
                undo_moves,
                [
                    (photo, directory / "photo.jpg"),
                    (report, directory / "report.pdf"),
                ],
            )
            self.assertTrue(report.is_file())
            self.assertTrue(photo.is_file())
            self.assertFalse((directory / "report.pdf").exists())
            self.assertFalse((directory / "photo.jpg").exists())


    def test_cli_undo_previews_receipt_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            documents.mkdir()

            organized_report = documents / "report.pdf"
            organized_report.write_text(
                "report",
                encoding="utf-8",
            )
            receipt_path = directory / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn(
                (
                    "UNDO PREVIEW: Documents/report.pdf -> "
                    "report.pdf"
                ),
                result.stdout,
            )
            self.assertIn(
                "No files were changed. Use --apply to approve.",
                result.stdout,
            )
            self.assertTrue(organized_report.is_file())
            self.assertFalse((directory / "report.pdf").exists())


    def test_cli_undo_apply_restores_files_after_approval(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            organized_report = documents / "report.pdf"
            organized_photo = images / "photo.jpg"
            organized_report.write_text(
                "report",
                encoding="utf-8",
            )
            organized_photo.write_text(
                "photo",
                encoding="utf-8",
            )

            receipt_path = directory / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                            },
                            {
                                "source": "photo.jpg",
                                "destination": "Images/photo.jpg",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn(
                "UNDO: Images/photo.jpg -> photo.jpg",
                result.stdout,
            )
            self.assertIn(
                "UNDO: Documents/report.pdf -> report.pdf",
                result.stdout,
            )
            self.assertIn("Restored 2 file(s).", result.stdout)
            self.assertEqual(
                (directory / "report.pdf").read_text(
                    encoding="utf-8"
                ),
                "report",
            )
            self.assertEqual(
                (directory / "photo.jpg").read_text(
                    encoding="utf-8"
                ),
                "photo",
            )
            self.assertFalse(organized_report.exists())
            self.assertFalse(organized_photo.exists())
            self.assertTrue(receipt_path.is_file())


    def test_undo_collision_blocks_every_restore(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            organized_report = documents / "report.pdf"
            organized_photo = images / "photo.jpg"
            existing_report = directory / "report.pdf"

            organized_report.write_text(
                "organized report",
                encoding="utf-8",
            )
            organized_photo.write_text(
                "organized photo",
                encoding="utf-8",
            )
            existing_report.write_text(
                "existing report",
                encoding="utf-8",
            )

            receipt_path = directory / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                            },
                            {
                                "source": "photo.jpg",
                                "destination": "Images/photo.jpg",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "Error: undo destination already exists:",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                existing_report.read_text(encoding="utf-8"),
                "existing report",
            )
            self.assertEqual(
                organized_report.read_text(encoding="utf-8"),
                "organized report",
            )
            self.assertEqual(
                organized_photo.read_text(encoding="utf-8"),
                "organized photo",
            )
            self.assertFalse((directory / "photo.jpg").exists())


    def test_move_receipt_records_source_content_sha256(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            content = b"quarterly report\n"
            report.write_bytes(content)

            receipt = build_move_receipt(
                directory,
                [
                    (
                        report,
                        directory / "Documents" / "report.pdf",
                    ),
                ],
            )

            self.assertEqual(
                receipt["moves"][0]["sha256"],
                hashlib.sha256(content).hexdigest(),
            )
            self.assertEqual(report.read_bytes(), content)
            self.assertFalse(
                (directory / "Documents").exists()
            )


    def test_changed_file_blocks_entire_undo(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            report = documents / "report.pdf"
            photo = images / "photo.jpg"
            original_report = b"original report\n"
            changed_report = b"changed after organization\n"
            photo_content = b"original photo\n"

            report.write_bytes(changed_report)
            photo.write_bytes(photo_content)

            receipt_path = directory / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                                "sha256": hashlib.sha256(
                                    original_report
                                ).hexdigest(),
                            },
                            {
                                "source": "photo.jpg",
                                "destination": "Images/photo.jpg",
                                "sha256": hashlib.sha256(
                                    photo_content
                                ).hexdigest(),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "Error: organized file content changed:",
                result.stderr,
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(report.read_bytes(), changed_report)
            self.assertEqual(photo.read_bytes(), photo_content)
            self.assertFalse((directory / "report.pdf").exists())
            self.assertFalse((directory / "photo.jpg").exists())


    def test_receipt_requires_explicit_apply_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            receipt_path = directory / "move-receipt.json"
            report.write_text("report", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--receipt",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                "Error: --receipt requires --apply.\n",
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertTrue(report.is_file())
            self.assertFalse(receipt_path.exists())
            self.assertFalse((directory / "Documents").exists())


    def test_undo_rejects_directory_argument_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            directory = temporary_root / "files"
            directory.mkdir()
            report = directory / "report.pdf"
            report.write_text("report", encoding="utf-8")

            receipt_path = temporary_root / "receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory.resolve()),
                        "moves": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--undo",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                "Error: directory cannot be used with --undo.\n",
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertTrue(report.is_file())
            self.assertFalse((directory / "Documents").exists())


    def test_undo_rejects_organizer_only_options(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            receipt_path = directory / "receipt.json"
            second_receipt = directory / "second-receipt.json"

            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [],
                    }
                ),
                encoding="utf-8",
            )

            conflicting_options = (
                ["--recursive"],
                ["--receipt", str(second_receipt), "--apply"],
            )

            for options in conflicting_options:
                with self.subTest(options=options):
                    result = subprocess.run(
                        [
                            sys.executable,
                            str(
                                Path(__file__).parents[1]
                                / "main.py"
                            ),
                            "--undo",
                            str(receipt_path),
                            *options,
                        ],
                        capture_output=True,
                        text=True,
                        check=False,
                    )

                    self.assertEqual(result.returncode, 1)
                    self.assertEqual(
                        result.stderr,
                        (
                            "Error: --undo cannot be combined with "
                            "--receipt or --recursive.\n"
                        ),
                    )
                    self.assertNotIn("Traceback", result.stderr)
                    self.assertFalse(second_receipt.exists())


    def test_receipt_write_failure_blocks_moves(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            receipt_path = directory / "move-receipt.json"
            report.write_text("report", encoding="utf-8")
            output = io.StringIO()
            error_output = io.StringIO()
            arguments = parse_args(
                [
                    str(directory),
                    "--apply",
                    "--receipt",
                    str(receipt_path),
                ]
            )

            with mock.patch(
                "main.json.dump",
                side_effect=OSError("simulated disk failure"),
            ):
                exit_code = run(
                    arguments,
                    output=output,
                    error_output=error_output,
                )

            self.assertEqual(exit_code, 1)
            self.assertIn(
                "Error: simulated disk failure",
                error_output.getvalue(),
            )
            self.assertNotIn("Traceback", error_output.getvalue())
            self.assertTrue(report.is_file())
            self.assertEqual(
                report.read_text(encoding="utf-8"),
                "report",
            )
            self.assertFalse((directory / "Documents").exists())
            self.assertFalse(receipt_path.exists())


    def test_receipt_records_only_category_folders_to_create(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            client = directory / "client"
            project = directory / "project"
            existing_images = project / "Images"
            client.mkdir()
            existing_images.mkdir(parents=True)

            report = client / "report.pdf"
            photo = project / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            receipt = build_move_receipt(
                directory,
                [
                    (
                        report,
                        client / "Documents" / "report.pdf",
                    ),
                    (
                        photo,
                        existing_images / "photo.jpg",
                    ),
                ],
            )

            self.assertEqual(
                receipt["created_directories"],
                ["client/Documents"],
            )
            self.assertTrue(existing_images.is_dir())
            self.assertFalse((client / "Documents").exists())


    def test_undo_removes_only_created_empty_category_folders(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            client = directory / "client"
            project = directory / "project"
            existing_images = project / "Images"
            client.mkdir()
            existing_images.mkdir(parents=True)

            report = client / "report.pdf"
            photo = project / "photo.jpg"
            receipt_path = directory / "move-receipt.json"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            organize_result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--recursive",
                    "--apply",
                    "--receipt",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(organize_result.returncode, 0)

            created_documents = client / "Documents"
            self.assertTrue(created_documents.is_dir())
            self.assertTrue(existing_images.is_dir())

            undo_result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(undo_result.returncode, 0)
            self.assertEqual(undo_result.stderr, "")
            self.assertTrue(report.is_file())
            self.assertTrue(photo.is_file())
            self.assertFalse(created_documents.exists())
            self.assertTrue(existing_images.is_dir())
            self.assertTrue(receipt_path.is_file())


    def test_undo_preview_reports_collision_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            documents.mkdir()

            organized_report = documents / "report.pdf"
            existing_report = directory / "report.pdf"
            organized_report.write_text(
                "organized report",
                encoding="utf-8",
            )
            existing_report.write_text(
                "existing report",
                encoding="utf-8",
            )

            receipt_path = directory / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                ],
                capture_output=True,
                               text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "Error: undo destination already exists:",
                result.stderr,
            )
            self.assertNotIn("UNDO PREVIEW:", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                organized_report.read_text(encoding="utf-8"),
                "organized report",
            )
            self.assertEqual(
                existing_report.read_text(encoding="utf-8"),
                "existing report",
            )


    def test_undo_preview_reports_missing_organized_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            receipt_path = directory / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertIn(
                "Error: undo source file does not exist:",
                result.stderr,
            )
            self.assertNotIn("UNDO PREVIEW:", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse((directory / "report.pdf").exists())
            self.assertFalse((directory / "Documents").exists())


    def test_cli_undo_directory_previews_relocated_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            original_directory = (
                temporary_root / "original-files"
            ).resolve()
            relocated_directory = (
                temporary_root / "relocated-files"
            ).resolve()
            documents = relocated_directory / "Documents"
            documents.mkdir(parents=True)

            organized_report = documents / "report.pdf"
            organized_report.write_text(
                "report",
                encoding="utf-8",
            )

            receipt_path = temporary_root / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(original_directory),
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--undo-directory",
                    str(relocated_directory),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn(
                (
                    "UNDO PREVIEW: Documents/report.pdf -> "
                    "report.pdf"
                ),
                result.stdout,
            )
            self.assertIn(
                "No files were changed. Use --apply to approve.",
                result.stdout,
            )
            self.assertTrue(organized_report.is_file())
            self.assertFalse(
                (relocated_directory / "report.pdf").exists()
            )


    def test_cli_undo_directory_restores_relocated_workspace(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            original_directory = (
                temporary_root / "original-files"
            ).resolve()
            relocated_directory = (
                temporary_root / "relocated-files"
            ).resolve()
            documents = relocated_directory / "Documents"
            documents.mkdir(parents=True)

            organized_report = documents / "report.pdf"
            content = b"relocated report\n"
            organized_report.write_bytes(content)

            receipt_path = temporary_root / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(original_directory),
                        "created_directories": ["Documents"],
                        "moves": [
                            {
                                "source": "report.pdf",
                                "destination": (
                                    "Documents/report.pdf"
                                ),
                                "sha256": hashlib.sha256(
                                    content
                                ).hexdigest(),
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--undo-directory",
                    str(relocated_directory),
                    "--apply",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            restored_report = relocated_directory / "report.pdf"

            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stderr, "")
            self.assertIn(
                (
                    "UNDO: Documents/report.pdf -> "
                    "report.pdf"
                ),
                result.stdout,
            )
            self.assertIn("Restored 1 file(s).", result.stdout)
            self.assertEqual(restored_report.read_bytes(), content)
            self.assertFalse(organized_report.exists())
            self.assertFalse(documents.exists())
            self.assertTrue(receipt_path.is_file())


    def test_undo_directory_requires_undo_without_changes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            report = directory / "report.pdf"
            report.write_text("report", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    str(directory),
                    "--undo-directory",
                    str(directory),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                "Error: --undo-directory requires --undo.\n",
            )
            self.assertNotIn("PREVIEW:", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertTrue(report.is_file())
            self.assertFalse((directory / "Documents").exists())


    def test_undo_directory_rejects_missing_directory(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            original_directory = (
                temporary_root / "original-files"
            ).resolve()
            missing_directory = (
                temporary_root / "missing-files"
            ).resolve()
            receipt_path = temporary_root / "move-receipt.json"

            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(original_directory),
                        "moves": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--undo-directory",
                    str(missing_directory),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                (
                    "Error: undo directory does not exist: "
                    f"{missing_directory}\n"
                ),
            )
            self.assertNotIn("UNDO PREVIEW:", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertFalse(missing_directory.exists())
            self.assertTrue(receipt_path.is_file())


    def test_undo_directory_rejects_file_path(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            original_directory = (
                temporary_root / "original-files"
            ).resolve()
            file_path = temporary_root / "not-a-directory.txt"
            file_path.write_text(
                "unchanged",
                encoding="utf-8",
            )

            receipt_path = temporary_root / "move-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "directory": str(original_directory),
                        "moves": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                    "--undo-directory",
                    str(file_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                (
                    "Error: undo path is not a directory: "
                    f"{file_path.resolve()}\n"
                ),
            )
            self.assertNotIn("UNDO PREVIEW:", result.stdout)
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(
                file_path.read_text(encoding="utf-8"),
                "unchanged",
            )
            self.assertTrue(receipt_path.is_file())


    def test_undo_receipt_without_directory_has_no_traceback(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            receipt_path = directory / "invalid-receipt.json"
            receipt_path.write_text(
                json.dumps(
                    {
                        "receipt_version": 1,
                        "moves": [],
                    }
                ),
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "main.py"),
                    "--undo",
                    str(receipt_path),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 1)
            self.assertEqual(
                result.stderr,
                "Error: invalid move receipt structure.\n",
            )
            self.assertNotIn("Traceback", result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue(receipt_path.is_file())


    def test_move_failure_rolls_back_completed_moves(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            report.write_text("report", encoding="utf-8")
            photo.write_text("photo", encoding="utf-8")

            report_destination = documents / "report.pdf"
            photo_destination = images / "photo.jpg"
            planned_moves = [
                (report, report_destination),
                (photo, photo_destination),
            ]

            original_rename = Path.rename

            def simulated_rename(source, destination):
                if source == photo:
                    raise OSError("simulated move failure")

                return original_rename(source, destination)

            with mock.patch(
                "pathlib.Path.rename",
                new=simulated_rename,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "simulated move failure",
                ):
                    move_files(
                        planned_moves,
                        approved=True,
                    )

            self.assertEqual(
                report.read_text(encoding="utf-8"),
                "report",
            )
            self.assertEqual(
                photo.read_text(encoding="utf-8"),
                "photo",
            )
            self.assertFalse(report_destination.exists())
            self.assertFalse(photo_destination.exists())


    def test_cli_move_failure_removes_receipt_and_created_folders(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            photo = directory / "photo.jpg"
            report = directory / "report.pdf"
            receipt_path = directory / "move-receipt.json"
            photo.write_text("photo", encoding="utf-8")
            report.write_text("report", encoding="utf-8")

            arguments = parse_args(
                [
                    str(directory),
                    "--apply",
                    "--receipt",
                    str(receipt_path),
                ]
            )
            output = io.StringIO()
            error_output = io.StringIO()
            original_rename = Path.rename

            def simulated_rename(source, destination):
                if source == report:
                    raise OSError("simulated move failure")

                return original_rename(source, destination)

            with mock.patch(
                "pathlib.Path.rename",
                new=simulated_rename,
            ):
                exit_code = run(
                    arguments,
                    output=output,
                    error_output=error_output,
                )

            self.assertEqual(exit_code, 1)
            self.assertEqual(
                error_output.getvalue(),
                "Error: simulated move failure\n",
            )
            self.assertNotIn("Moved", output.getvalue())
            self.assertEqual(
                photo.read_text(encoding="utf-8"),
                "photo",
            )
            self.assertEqual(
                report.read_text(encoding="utf-8"),
                "report",
            )
            self.assertFalse(receipt_path.exists())
            self.assertFalse((directory / "Images").exists())
            self.assertFalse((directory / "Documents").exists())


    def test_undo_failure_rolls_back_completed_restores(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            organized_report = documents / "report.pdf"
            organized_photo = images / "photo.jpg"
            organized_report.write_text(
                "report",
                encoding="utf-8",
            )
            organized_photo.write_text(
                "photo",
                encoding="utf-8",
            )

            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            undo_moves = [
                (organized_report, report),
                (organized_photo, photo),
            ]
            original_rename = Path.rename

            def simulated_rename(source, destination):
                if source == organized_photo:
                    raise OSError("simulated undo failure")

                return original_rename(source, destination)

            with mock.patch(
                "pathlib.Path.rename",
                new=simulated_rename,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "simulated undo failure",
                ):
                    undo_files(
                        undo_moves,
                        directory,
                        approved=True,
                    )

            self.assertEqual(
                organized_report.read_text(encoding="utf-8"),
                "report",
            )
            self.assertEqual(
                organized_photo.read_text(encoding="utf-8"),
                "photo",
            )
            self.assertFalse(report.exists())
            self.assertFalse(photo.exists())


    def test_move_rollback_never_overwrites_new_source_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory)
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            report.write_text(
                "original report",
                encoding="utf-8",
            )
            photo.write_text("photo", encoding="utf-8")

            report_destination = documents / "report.pdf"
            photo_destination = images / "photo.jpg"
            planned_moves = [
                (report, report_destination),
                (photo, photo_destination),
            ]
            original_rename = Path.rename

            def simulated_rename(source, destination):
                if source == photo:
                    report.write_text(
                        "new arrival",
                        encoding="utf-8",
                    )
                    raise OSError("simulated move failure")

                return original_rename(source, destination)

            with mock.patch(
                "pathlib.Path.rename",
                new=simulated_rename,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "rollback destination already exists",
                ):
                    move_files(
                        planned_moves,
                        approved=True,
                    )

            self.assertEqual(
                report.read_text(encoding="utf-8"),
                "new arrival",
            )
            self.assertEqual(
                report_destination.read_text(encoding="utf-8"),
                "original report",
            )
            self.assertEqual(
                photo.read_text(encoding="utf-8"),
                "photo",
            )
            self.assertFalse(photo_destination.exists())


    def test_undo_rollback_never_overwrites_new_organized_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            directory = Path(temporary_directory).resolve()
            documents = directory / "Documents"
            images = directory / "Images"
            documents.mkdir()
            images.mkdir()

            organized_report = documents / "report.pdf"
            organized_photo = images / "photo.jpg"
            organized_report.write_text(
                "original report",
                encoding="utf-8",
            )
            organized_photo.write_text(
                "photo",
                encoding="utf-8",
            )

            report = directory / "report.pdf"
            photo = directory / "photo.jpg"
            undo_moves = [
                (organized_report, report),
                (organized_photo, photo),
            ]
            original_rename = Path.rename

            def simulated_rename(source, destination):
                if source == organized_photo:
                    organized_report.write_text(
                        "new arrival",
                        encoding="utf-8",
                    )
                    raise OSError("simulated undo failure")

                return original_rename(source, destination)

            with mock.patch(
                "pathlib.Path.rename",
                new=simulated_rename,
            ):
                with self.assertRaisesRegex(
                    OSError,
                    "rollback destination already exists",
                ):
                    undo_files(
                        undo_moves,
                        directory,
                        approved=True,
                    )

            self.assertEqual(
                organized_report.read_text(encoding="utf-8"),
                "new arrival",
            )
            self.assertEqual(
                report.read_text(encoding="utf-8"),
                "original report",
            )
            self.assertEqual(
                organized_photo.read_text(encoding="utf-8"),
                "photo",
            )
            self.assertFalse(photo.exists())


if __name__ == "__main__":
    unittest.main()
