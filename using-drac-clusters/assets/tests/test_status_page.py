import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib import status_page, store  # noqa: E402
from dracmonlib.config import Config  # noqa: E402

FIXTURE = (HERE / "fixtures" / "status_page.html").read_text(encoding="utf-8")


class Parse(unittest.TestCase):
    def test_fixture_states(self):
        s = status_page.parse_status(FIXTURE)
        self.assertEqual(s["fir"].state, "outage")
        self.assertTrue(s["fir"].title.startswith("Planned Outage"))
        self.assertEqual(s["rorqual"].state, "conditions")
        self.assertIn("/project", s["rorqual"].title)
        self.assertEqual(s["rorqual"].since, "2026-11-18")
        self.assertEqual(s["narval"].state, "ok")
        self.assertEqual(s["narval"].title, "")
        self.assertIsNone(s["narval"].since)
        self.assertEqual(s["tamia"].state, "ok")

    def test_icon_mapping_and_unknown(self):
        html = ("<table><tr><td><a href='/system/X'>Alpha</a></td>"
                "<td><i class='material-icons'>event</i></td>"
                "<td><a href='/view_incident?incident=1'> One </a>"
                "<a href='/view_incident?incident=2'>Two</a></td></tr>"
                "<tr><td><a href='/system/Y'>Beta</a></td>"
                "<td><i class='material-icons'>weird</i></td><td></td></tr></table>")
        s = status_page.parse_status(html)
        self.assertEqual(s["alpha"].state, "scheduled")
        self.assertEqual(s["alpha"].titles, ("One", "Two"))
        self.assertEqual(s["alpha"].title, "One")
        self.assertEqual(s["beta"].state, "unknown")

    def test_garbage_is_empty(self):
        self.assertEqual(status_page.parse_status("<html>nothing</html>"), {})


class Fetch(unittest.TestCase):
    def test_fetch_failure_is_none(self):
        with mock.patch("urllib.request.urlopen", side_effect=urllib.error.URLError("down")):
            self.assertIsNone(status_page.fetch_status())

    def test_fetch_sends_generic_agent_and_parses(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = FIXTURE.encode()
        with mock.patch("urllib.request.urlopen", return_value=resp) as uo:
            out = status_page.fetch_status()
        req = uo.call_args[0][0]
        self.assertEqual(req.get_header("User-agent"), "dracmon")
        self.assertEqual(uo.call_args[1]["timeout"], 10)
        self.assertEqual(out["fir"].state, "outage")

    def test_unparseable_page_is_none(self):
        resp = mock.MagicMock()
        resp.__enter__.return_value.read.return_value = b"<html>maintenance</html>"
        with mock.patch("urllib.request.urlopen", return_value=resp):
            self.assertIsNone(status_page.fetch_status())


class Cache(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.tmp = tempfile.TemporaryDirectory()
        self.conn = store.open_store(Path(self.tmp.name) / "d.db")
        self.cfg = Config()
        self.data = {"fir": status_page.StatusEntry("outage", "T", None, ("T", "U"))}

    def tearDown(self):
        self.conn.close()
        self.tmp.cleanup()

    def test_refresh_respects_cadence(self):
        f = mock.Mock(return_value=self.data)
        status_page.refresh(self.conn, self.cfg, 1000.0, f)
        status_page.refresh(self.conn, self.cfg, 1500.0, f)
        self.assertEqual(f.call_count, 1)
        status_page.refresh(self.conn, self.cfg, 1000.0 + 900, f)
        self.assertEqual(f.call_count, 2)
        self.assertEqual(status_page.load(self.conn, self.cfg, 2000.0), self.data)

    def test_failure_not_retried_within_cadence_and_expires(self):
        status_page.refresh(self.conn, self.cfg, 1000.0, lambda: self.data)
        f = mock.Mock(return_value=None)
        status_page.refresh(self.conn, self.cfg, 1900.0, f)
        status_page.refresh(self.conn, self.cfg, 2000.0, f)
        self.assertEqual(f.call_count, 1)
        # last good data still shown while younger than 2 cadences, then dropped
        self.assertEqual(status_page.load(self.conn, self.cfg, 2000.0), self.data)
        self.assertEqual(status_page.load(self.conn, self.cfg, 1000.0 + 1800), {})

    def test_never_fetched_is_empty(self):
        self.assertEqual(status_page.load(self.conn, self.cfg, 5.0), {})

    def test_fetch_exception_swallowed(self):
        def boom():
            raise RuntimeError("x")
        status_page.refresh(self.conn, self.cfg, 1.0, boom)
        self.assertEqual(status_page.load(self.conn, self.cfg, 2.0), {})


class Column(unittest.TestCase):
    def test_column_text_and_dash(self):
        try:
            from dracmonlib.tui import clusters
        except ImportError:
            self.skipTest("textual missing")
        self.assertEqual(clusters.status_cell(None).plain, "–")
        e = status_page.StatusEntry("outage", "Planned Outage - Arrêt planifié and a very long tail",
                                    None, ("Planned Outage - Arrêt planifié and a very long tail", "B"))
        t = clusters.status_cell(e)
        self.assertTrue(t.plain.startswith("outage "))
        self.assertLessEqual(len(t.plain), clusters.STATUS_WIDTH)
        self.assertEqual(clusters.status_cell(status_page.StatusEntry("ok", "", None)).plain, "ok")
        self.assertIn("B", clusters.status_detail(e).plain)

    def test_load_clusters_carries_status_and_expires(self):
        try:
            from dracmonlib.tui import clusters
        except ImportError:
            self.skipTest("textual missing")
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            conn = store.open_store(Path(d) / "d.db")
            cfg = Config()
            data = {"narval": status_page.StatusEntry("ok", "", None)}
            status_page.refresh(conn, cfg, 1000.0, lambda: data)
            rows = {r.name: r for r in clusters.load_clusters(conn, cfg, 1100.0)}
            self.assertEqual(rows["narval"].status, data["narval"])
            self.assertIsNone(rows["fir"].status)
            rows = clusters.load_clusters(conn, cfg, 1000.0 + 1800)
            self.assertTrue(all(r.status is None for r in rows))
            conn.close()


if __name__ == "__main__":
    unittest.main()
