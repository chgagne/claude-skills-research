import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dracmonlib.cells import (CellEvent, aggregate, eta_seconds, glob_progress,  # noqa: E402
                              is_open, parse_cells_section)


def ev(ts, job, event, cell="", detail=""):
    return CellEvent(float(ts), job, event, cell, detail)


def agg(*items):
    return aggregate(items)


class ParseTests(unittest.TestCase):
    def test_parse_basic(self):
        body = "#file 25 25 c1/7.log\n10\t7\tplan\t\t5\n11\t7\tstart\tA\t\n"
        (ch,) = parse_cells_section(body)
        self.assertEqual((ch.relpath, ch.campaign, ch.size, ch.start_offset), ("c1/7.log", "c1", 25, 0))
        self.assertEqual(ch.end, 25)
        self.assertEqual(ch.events[0], CellEvent(10.0, "7", "plan", "", "5"))
        self.assertEqual(ch.events[1].cell, "A")
        self.assertEqual(ch.consumed, len(body.split("\n", 1)[1]))

    def test_torn_line_not_consumed(self):
        good = "11\t7\tstart\tA\t\n"
        body = "#file 99 18 c1/7.log\n" + good + "12\t7\tdone\tA\tok"
        (ch,) = parse_cells_section(body, {"c1/7.log": 5})
        self.assertEqual(len(ch.events), 1)  # the torn line is re-read next poll
        self.assertEqual(ch.consumed, len(good))
        self.assertEqual(ch.start_offset, 5)

    def test_torn_garbage_skipped_and_never_raises(self):
        body = "#file 9 9 c/1.log\nxx\n1\t1\tbogus\tA\t\nabc\t1\tstart\tA\t\n3\t1\tstart\n4\t1\tstart\tA\xff\n5\t1\tfail\tB\n"
        (ch,) = parse_cells_section(body)
        self.assertEqual([(e.event, e.cell) for e in ch.events], [("start", "A\xff"), ("fail", "B")])

    def test_consumed_is_raw_byte_count(self):
        raw = b"1\t7\tstart\tA\xff\t\n2\t7\tdone\tA\xff\t\n"
        body = b"#file 99 99 c/7.log\n" + raw
        (ch,) = parse_cells_section(body.decode("utf-8", "surrogateescape"))
        self.assertEqual(ch.consumed, len(raw))
        self.assertEqual([e.cell for e in ch.events], ["A\ufffd", "A\ufffd"])

    def test_odd_separators_inside_detail(self):
        raw = ("1\t1\tstart\tA\t50%\r60%\x0b\x85\u2028\u2029\x1c\n"
               "2\t1\tdone\tA\tx y\n").encode("utf-8")
        body = b"#file 99 99 c/1.log\n" + raw
        (ch,) = parse_cells_section(body.decode("utf-8", "surrogateescape"))
        self.assertEqual([e.event for e in ch.events], ["start", "done"])
        self.assertEqual(ch.consumed, len(raw))

    def test_event_offsets_are_raw_line_starts(self):
        l1 = "1\t7\tstart\tA\xff\t\n".encode("utf-8", "surrogateescape")
        junk = b"garbage\n"
        l2 = b"2\t7\tdone\tA\t\n"
        body = b"#file 999 999 c/7.log\n" + l1 + junk + l2
        (ch,) = parse_cells_section(body.decode("utf-8", "surrogateescape"), {"c/7.log": 100})
        self.assertEqual(ch.event_offsets, [100, 100 + len(l1) + len(junk)])
        self.assertEqual(len(ch.event_offsets), len(ch.events))

    def test_reset_when_size_below_offset(self):
        (ch,) = parse_cells_section("#file 10 10 c1/7.log\n", {"c1/7.log": 500})
        self.assertEqual((ch.start_offset, ch.events, ch.consumed, ch.size), (0, [], 0, 10))

    def test_relpath_with_spaces(self):
        body = "#file 20 20 my camp/job 1.log\n1\t1\tstart\tA\t\n#file 0 0 other/2.log\n"
        a, b = parse_cells_section(body, {"my camp/job 1.log": 0})
        self.assertEqual((a.relpath, a.campaign, a.size), ("my camp/job 1.log", "my camp", 20))
        self.assertEqual(len(a.events), 1)
        self.assertEqual((b.relpath, b.events), ("other/2.log", []))

    def test_end_from_marker(self):
        # the remote filter dropped a line: <end> still covers it
        body = "#file 30 30 c/1.log\n1\t1\tstart\tA\t\n"
        (ch,) = parse_cells_section(body, {"c/1.log": 5})
        self.assertEqual((ch.start_offset, ch.end, len(ch.events)), (5, 30, 1))

    def test_marker_without_end_rejected(self):
        (ch,) = parse_cells_section("#file 20 20 c/1.log\n")
        self.assertEqual(ch.end, 20)
        self.assertEqual(parse_cells_section("#file 20 c/1.log\n1\t1\tstart\tA\t\n"), [])
        self.assertEqual(parse_cells_section("#file 20 x c/1.log\n"), [])


class AggregateTests(unittest.TestCase):
    def test_resume_does_not_double_count(self):
        s = agg(("n", ev(1, "1", "start", "A")), ("n", ev(5, "1", "done", "A")),
                ("n", ev(10, "2", "start", "A")), ("n", ev(12, "2", "done", "A")))
        self.assertEqual(s.done, {"A"})
        self.assertEqual(s.durations, [4.0, 2.0])
        self.assertEqual(s.running, set())

    def test_done_beats_later_fail(self):
        s = agg(("n", ev(1, "1", "start", "A")), ("n", ev(2, "1", "done", "A")),
                ("n", ev(3, "2", "fail", "A", "oom")))
        self.assertEqual(s.done, {"A"})
        self.assertEqual(s.failed, {})

    def test_running_and_failed(self):
        s = agg(("n", ev(1, "1", "start", "A")), ("n", ev(2, "1", "start", "B")),
                ("n", ev(3, "1", "fail", "B", "oom")), ("n", ev(4, "1", "start", "C")))
        self.assertEqual(s.running, {"A", "C"})
        self.assertEqual(s.failed, {"B": "oom"})
        self.assertEqual(s.last_failure, ("B", "oom", 3.0))
        self.assertEqual(s.last_event, 4.0)

    def test_retry_after_fail_is_running(self):
        s = agg(("n", ev(1, "1", "fail", "A", "x")), ("n", ev(2, "2", "start", "A")))
        self.assertEqual((s.running, s.failed), ({"A"}, {}))

    def test_plan_latest_wins(self):
        s = agg(("n", ev(1, "1", "plan", "", "10")), ("n", ev(9, "2", "plan", "", "12")),
                ("n", ev(5, "1", "plan", "", "11")))
        self.assertEqual(s.plan, 12)
        self.assertIsNone(agg().plan)

    def test_eta_median_concurrency(self):
        evs = [("n", ev(0, "1", "plan", "", "10"))]
        t = 1
        for i, d in enumerate([60, 60, 120, 60]):
            evs += [("n", ev(t, "1", "start", f"c{i}")), ("n", ev(t + d, "1", "done", f"c{i}"))]
            t += d + 1
        evs += [("n", ev(t, "1", "start", "r1")), ("n", ev(t, "1", "start", "r2"))]
        self.assertEqual(eta_seconds(aggregate(evs)), 180.0)

    def test_eta_none(self):
        self.assertIsNone(eta_seconds(agg(("n", ev(1, "1", "plan", "", "5")))))
        self.assertIsNone(eta_seconds(agg(("n", ev(1, "1", "start", "A")), ("n", ev(2, "1", "done", "A")))))

    def test_cross_cluster_union(self):
        s = agg(("narval", ev(1, "1", "start", "A")), ("narval", ev(2, "1", "done", "A")),
                ("rorqual", ev(1, "1", "start", "A")), ("rorqual", ev(3, "1", "done", "A")))
        self.assertEqual(s.done, {"A"})
        self.assertEqual(s.clusters, {"narval", "rorqual"})
        self.assertEqual(sorted(s.durations), [1.0, 2.0])

    def test_open_window(self):
        s = agg(("n", ev(1000, "1", "start", "A")))
        self.assertTrue(is_open(s, False, 1000 + 86399))
        self.assertFalse(is_open(s, False, 1000 + 86401))
        self.assertTrue(is_open(s, True, 1000 + 10 ** 6))
        self.assertFalse(is_open(agg(), False, 5))

    def test_glob_progress(self):
        s = glob_progress(3, 10)
        self.assertEqual((len(s.done), s.plan), (3, 10))


if __name__ == "__main__":
    unittest.main()
