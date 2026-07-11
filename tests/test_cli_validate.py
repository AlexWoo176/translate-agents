import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import sys
import io

from src.cli.commands import validate

class TestCliValidate(unittest.TestCase):
    @patch("src.cli.commands.validate.get_book_root")
    def test_validate_nonexistent_book_dir(self, mock_get_book_root):
        mock_path = MagicMock(spec=Path)
        mock_path.is_dir.return_value = False
        mock_get_book_root.return_value = mock_path

        args = MagicMock()
        args.book = "no-book"

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            exit_code = validate.run(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(exit_code, 1)
        self.assertIn("does not exist", captured_output.getvalue())

    @patch("src.cli.commands.validate.get_book_root")
    def test_validate_all_exist(self, mock_get_book_root):
        mock_path = MagicMock(spec=Path)
        mock_path.is_dir.return_value = True
        
        # All nested files/folders exist
        mock_child = MagicMock(spec=Path)
        mock_child.is_file.return_value = True
        mock_child.is_dir.return_value = True
        mock_path.__truediv__.return_value = mock_child

        mock_get_book_root.return_value = mock_path

        args = MagicMock()
        args.book = "valid-book"

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            exit_code = validate.run(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(exit_code, 0)
        self.assertIn("Validation outcome: PASS", captured_output.getvalue())

    @patch("src.cli.commands.validate.get_book_root")
    def test_validate_some_missing(self, mock_get_book_root):
        mock_path = MagicMock(spec=Path)
        mock_path.is_dir.return_value = True
        
        # Some are missing
        mock_child = MagicMock(spec=Path)
        mock_child.is_file.return_value = False
        mock_child.is_dir.return_value = False
        mock_path.__truediv__.return_value = mock_child

        mock_get_book_root.return_value = mock_path

        args = MagicMock()
        args.book = "invalid-book"

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            exit_code = validate.run(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(exit_code, 1)
        self.assertIn("Validation outcome: FAIL", captured_output.getvalue())

if __name__ == "__main__":
    unittest.main()
