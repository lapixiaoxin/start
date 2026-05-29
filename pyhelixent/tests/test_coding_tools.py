from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pyhelixent.coding import bash_tool, grep_search_tool, list_files_tool, read_file_tool, write_file_tool


class CodingToolsTest(unittest.TestCase):
    def test_file_tools_stay_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            write = write_file_tool(root)
            read = read_file_tool(root)

            write_result = write.run({"path": "notes/example.txt", "content": "alpha\nbeta\n"})
            read_result = read.run({"path": "notes/example.txt", "start_line": 2, "end_line": 2})
            outside_result = read.run({"path": "../outside.txt"})

            self.assertTrue(write_result["ok"])
            self.assertEqual(read_result, "2: beta")
            self.assertEqual(outside_result["code"], "INVALID_PATH")

    def test_list_and_grep_tools_return_workspace_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "a.txt").write_text("agent\n", encoding="utf-8")
            (root / "b.txt").write_text("plain\nagent again\n", encoding="utf-8")

            files = list_files_tool(root).run({"path": "."})
            matches = grep_search_tool(root).run({"path": ".", "pattern": "agent"})

            self.assertEqual(files["files"], ["a.txt", "b.txt"])
            self.assertEqual([match["path"] for match in matches["matches"]], ["a.txt", "b.txt"])
            self.assertEqual(matches["matches"][1]["line"], 2)

            invalid = grep_search_tool(root).run({"path": ".", "pattern": "["})
            self.assertEqual(invalid["code"], "INVALID_PATTERN")

    def test_bash_tool_runs_safe_commands_and_blocks_destructive_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            tool = bash_tool(temp_dir)

            safe = tool.run({"command": "printf hello"})
            blocked = tool.run({"command": "rm -rf something"})

            self.assertTrue(safe["ok"])
            self.assertEqual(safe["stdout"], "hello")
            self.assertEqual(blocked["code"], "COMMAND_BLOCKED")


if __name__ == "__main__":
    unittest.main()
