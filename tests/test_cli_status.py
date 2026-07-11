import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import json
import sys
import io

from src.cli.commands import status

class TestCliStatus(unittest.TestCase):
    @patch("src.cli.commands.status.get_book_root")
    def test_status_missing_file(self, mock_get_book_root):
        # Setup mock book root that has no status.json
        mock_path = MagicMock(spec=Path)
        mock_status_file = MagicMock(spec=Path)
        mock_status_file.is_file.return_value = False
        
        # Mock book_path / "status.json" operation
        mock_path.__truediv__.return_value = mock_status_file
        mock_get_book_root.return_value = mock_path

        args = MagicMock()
        args.book = "dummy-book"

        # Capture output
        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            exit_code = status.run(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(exit_code, 1)
        self.assertIn("status.json does not exist for book 'dummy-book'", captured_output.getvalue())
        mock_get_book_root.assert_called_once_with("dummy-book")

    @patch("src.cli.commands.status.get_book_root")
    @patch("builtins.open")
    def test_status_existing_file(self, mock_open, mock_get_book_root):
        mock_path = MagicMock(spec=Path)
        mock_status_file = MagicMock(spec=Path)
        mock_status_file.is_file.return_value = True
        
        mock_path.__truediv__.return_value = mock_status_file
        mock_get_book_root.return_value = mock_path

        # Mock reading status.json
        status_data = {"status": "initialized", "chapters": {}}
        mock_file = MagicMock()
        mock_file.__enter__.return_value = mock_file
        mock_file.read.return_value = json.dumps(status_data)
        mock_open.return_value = mock_file

        args = MagicMock()
        args.book = "dummy-book"

        captured_output = io.StringIO()
        sys.stdout = captured_output

        try:
            exit_code = status.run(args)
        finally:
            sys.stdout = sys.__stdout__

        self.assertEqual(exit_code, 0)
        self.assertIn("BOOK STATUS DASHBOARD", captured_output.getvalue())
        self.assertIn("DUMMY-BOOK", captured_output.getvalue())
        mock_get_book_root.assert_called_once_with("dummy-book")

if __name__ == "__main__":
    unittest.main()
