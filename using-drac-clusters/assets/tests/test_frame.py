import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dracmonlib.frame import Section, parse_frames, render_frames  # noqa: E402


class FrameTests(unittest.TestCase):
    def test_frames_roundtrip(self):
        text = ("banner noise\n@@dracmon begin env\nuser=jdoe\nnow=5\n@@dracmon end env rc=0\n"
                "@@dracmon begin queue\n@@dracmon end queue rc=0\n"
                "@@dracmon begin disk\n@@dracmon end disk rc=127\n")
        secs = parse_frames(text)
        self.assertEqual(secs["env"], Section("env", 0, "user=jdoe\nnow=5\n", True))
        self.assertEqual(secs["queue"].body, "")
        self.assertEqual(secs["disk"].rc, 127)
        again = parse_frames(render_frames(secs.values()))
        self.assertEqual(again, secs)

    def test_truncated_section_incomplete(self):
        text = ("@@dracmon begin env\nuser=jdoe\n@@dracmon end env rc=0\n"
                "@@dracmon begin queue\n101|a|b\n102|c")
        secs = parse_frames(text)
        self.assertTrue(secs["env"].complete)
        self.assertFalse(secs["queue"].complete)
        self.assertIsNone(secs["queue"].rc)
        self.assertEqual(render_frames(secs.values()).count("begin"), 1)

    def test_body_split_on_newline_only(self):
        # \r, \x0b, \x0c, \x1c-\x1e, \x85, U+2028/9 are not line ends: cells byte
        # offsets count the body exactly as the remote sent it
        body = "1\ta\r\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029b\n2\tc\r\n"
        text = f"@@dracmon begin cells\n{body}@@dracmon end cells rc=0\n"
        secs = parse_frames(text)
        self.assertEqual(secs["cells"].body, body)
        self.assertTrue(secs["cells"].complete)

    def test_missing_end_before_next_begin(self):
        text = ("@@dracmon begin queue\nx\n@@dracmon begin disk\ny\n@@dracmon end disk rc=0\n")
        secs = parse_frames(text)
        self.assertFalse(secs["queue"].complete)
        self.assertTrue(secs["disk"].complete)


if __name__ == "__main__":
    unittest.main()
