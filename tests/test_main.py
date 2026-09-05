import tempfile
import unittest
from pathlib import Path

from main import (
    create_category_folders,
    file_category,
    file_extension,
    list_files,
    plan_moves,
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



if __name__ == "__main__":
    unittest.main()
