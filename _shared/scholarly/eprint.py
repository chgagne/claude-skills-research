# _shared/scholarly/eprint.py
"""Unpack an arXiv e-print (tarball or single gzipped .tex) into one string."""
import gzip, io, tarfile


def tex_from_eprint(blob):
    if not blob:
        return ""
    try:
        with tarfile.open(fileobj=io.BytesIO(blob), mode="r:*") as tf:
            names = [n for n in sorted(tf.getnames()) if n.lower().endswith(".tex")]
            parts = []
            for n in names:
                fh = tf.extractfile(n)
                if fh:
                    parts.append(fh.read().decode("utf-8", "replace"))
            return "\n".join(parts)
    except (tarfile.TarError, EOFError):
        pass
    try:
        return gzip.decompress(blob).decode("utf-8", "replace")
    except (OSError, EOFError):
        return ""
