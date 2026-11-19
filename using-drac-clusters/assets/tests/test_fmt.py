"""Display formatters (stdlib only)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dracmonlib.tui import fmt  # noqa: E402


class FmtTests(unittest.TestCase):
    def test_fmt_duration(self):
        self.assertEqual(fmt.duration(3893), "1:04:53")
        self.assertEqual(fmt.duration(2 * 86400 + 3 * 3600), "2-03:00:00")
        self.assertEqual(fmt.duration(59), "0:00:59")
        self.assertEqual(fmt.duration(None), "–")
        self.assertEqual(fmt.duration(-5), "–")

    def test_fmt_bytes(self):
        self.assertEqual(fmt.bytes_(int(16.5 * 2**30)), "16.5 GiB")
        self.assertEqual(fmt.bytes_(512), "512 B")
        self.assertEqual(fmt.bytes_(2048), "2.0 KiB")
        self.assertEqual(fmt.bytes_(5 * 2**40), "5.0 TiB")
        self.assertEqual(fmt.bytes_(None), "–")

    def test_fmt_pct(self):
        self.assertEqual(fmt.pct(41, 100), "41 %")
        self.assertEqual(fmt.pct(478000, 500000), "96 %")
        self.assertEqual(fmt.pct(1, 0), "–")
        self.assertEqual(fmt.pct(None, 10), "–")

    def test_fmt_bar(self):
        b = fmt.bar(31, 48, 8)
        self.assertEqual(len(b), 8)
        self.assertEqual(b.count("▓"), 5)
        self.assertEqual(b, "▓▓▓▓▓░░░")
        self.assertEqual(fmt.bar(48, 48, 8), "▓" * 8)
        self.assertEqual(fmt.bar(0, 0, 4), "░" * 4)
        self.assertEqual(fmt.bar(60, 48, 4), "▓" * 4)  # never longer than the width

    def test_fmt_age(self):
        self.assertEqual(fmt.age(1000 - 180, 1000), "3 min")
        self.assertEqual(fmt.age(10000 - 2 * 3600, 10000), "2 h")
        self.assertEqual(fmt.age(100 - 20, 100), "20 s")
        self.assertEqual(fmt.age(0, 3 * 86400), "3 d")
        self.assertEqual(fmt.age(None, 100), "never")

    def test_fmt_level(self):
        self.assertEqual(fmt.level(92), "warn")
        self.assertEqual(fmt.level(79.9), "ok")
        self.assertEqual(fmt.level(80), "warn")
        self.assertEqual(fmt.level(95), "crit")
        self.assertEqual(fmt.level(None), "ok")

    def test_fmt_hm(self):
        self.assertEqual(fmt.hm(3 * 3600 + 10 * 60), "3h10")
        self.assertEqual(fmt.hm(45 * 60), "45m")
        self.assertEqual(fmt.hm(2 * 86400 + 3 * 3600), "2d03h")
        self.assertEqual(fmt.hm(None), "–")

    def test_fmt_hours(self):
        self.assertEqual(fmt.hours(628.3177), "628.3")
        self.assertEqual(fmt.hours(5011.2), "5,011")
        self.assertEqual(fmt.hours(0), "0")


if __name__ == "__main__":
    unittest.main()
