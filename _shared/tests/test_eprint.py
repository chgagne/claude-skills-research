# _shared/tests/test_eprint.py
import gzip, io, pathlib, sys, tarfile, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scholarly.eprint import tex_from_eprint  # noqa: E402

def tarball(files):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tf:
        for name, text in files.items():
            data = text.encode(); ti = tarfile.TarInfo(name); ti.size = len(data)
            tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()

class TestEprint(unittest.TestCase):
    def test_tarball_concatenates_tex_files_sorted(self):
        out = tex_from_eprint(tarball({"b.tex": "B", "a.tex": "A", "fig.pdf": "x"}))
        self.assertEqual(out, "A\nB")

    def test_single_gzipped_tex(self):
        self.assertEqual(tex_from_eprint(gzip.compress(b"solo")), "solo")

    def test_garbage_is_empty(self):
        self.assertEqual(tex_from_eprint(b"not an archive"), "")
        self.assertEqual(tex_from_eprint(None), "")
