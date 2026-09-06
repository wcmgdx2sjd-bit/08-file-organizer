import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from main import (
    create_category_folders,
    file_category,
    file_extension,
    list_files,
    move_files,
    parse_args,
    plan_moves,
    run,
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


if __name__ == "__main__":
    unittest.main()
