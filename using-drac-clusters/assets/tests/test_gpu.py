import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from dracmonlib import gpu  # noqa: E402
from dracmonlib.frame import parse_frames  # noqa: E402
from dracmonlib.parse import PartitionRow, parse_sinfo  # noqa: E402

FIX = HERE / "fixtures"


def sinfo(cluster):
    body = parse_frames((FIX / f"{cluster}.txt").read_text())["partitions"].body
    return parse_sinfo(body, cluster)


class GpuCountTests(unittest.TestCase):
    def test_gpu_whole_mig_shard(self):
        self.assertEqual(gpu.gpu_count("gres/gpu=2", {}), 2.0)
        self.assertAlmostEqual(gpu.gpu_count("gres/gpu:a100_3g.20gb=1", {}), 3 / 7)
        self.assertEqual(gpu.gpu_count("gres/shard:l40s=4", {"l40s": 4}), 1.0)
        self.assertEqual(gpu.gpu_count("cpu=4,mem=8G", {}), 0.0)

    def test_typed_and_untyped_counted_once(self):
        tres = "billing=48800,cpu=24,energy=800042,gres/gpu:h100=4,gres/gpu=4,mem=200G,node=1"
        self.assertEqual(gpu.gpu_count(tres, {}), 4.0)
        tres = "billing=3485,cpu=4,gres/gpu:nvidia_h100_80gb_hbm3_2g.20gb=1,gres/gpu=1,mem=62G,node=1"
        self.assertAlmostEqual(gpu.gpu_count(tres, {}), 2 / 7)
        # typed only (TamIA)
        self.assertEqual(gpu.gpu_count("billing=1,cpu=64,gres/gpu:h200=8,mem=1000000M,node=1", {}), 8.0)

    def test_mig_names(self):
        self.assertAlmostEqual(gpu.gpu_count("gres/gpu:nvidia_h100_80gb_hbm3_2g.20gb=1", {}), 2 / 7)
        self.assertAlmostEqual(gpu.gpu_count("gres/gpu:a100_3g.20gb=1", {}), 3 / 7)
        self.assertAlmostEqual(gpu.gpu_count("gres/gpu:a100_1g.5gb=2", {}), 2 / 7)

    def test_squeue_forms(self):
        self.assertEqual(gpu.gpu_count("gres/gpu:h100:4", {}), 4.0)
        self.assertEqual(gpu.gpu_count("gpu:a100:2", {}), 2.0)
        self.assertEqual(gpu.gpu_count("gres:gpu:1", {}), 1.0)
        self.assertEqual(gpu.gpu_count("gres:gpu:h100:1", {}), 1.0)
        self.assertEqual(gpu.gpu_count("gres/gpu:h100:4(IDX:0-3)", {}), 4.0)
        self.assertEqual(gpu.gpu_count("N/A", {}), 0.0)
        self.assertEqual(gpu.gpu_count("", {}), 0.0)

    def test_shard_unknown_model_quarter(self):
        self.assertEqual(gpu.gpu_count("gres/shard:l40s=2", {}), 0.5)
        self.assertEqual(gpu.gpu_count("gres/shard=1", {"l40s": 4}), 0.25)
        self.assertEqual(gpu.gpu_count("gres/shard:l40s:8", {"l40s": 4}), 2.0)

    def test_garbage_is_zero_not_error(self):
        self.assertEqual(gpu.gpu_count("gres/gpu=x,gres/gpu:h100=", {}), 0.0)


class ShardsPerCardTests(unittest.TestCase):
    def test_from_gres(self):
        rows = [PartitionRow("c", "p", "up", 3600, 1, "mixed", "gpu:l40s:4,shard:l40s:16")]
        self.assertEqual(gpu.shards_per_card(rows), {"l40s": 4})

    def test_vulcan_recorded(self):
        self.assertEqual(gpu.shards_per_card(sinfo("vulcan")), {"l40s": 4})

    def test_no_shards_elsewhere(self):
        for c in ("narval", "rorqual", "nibi", "tamia", "killarney"):
            self.assertEqual(gpu.shards_per_card(sinfo(c)), {}, c)

    def test_socket_suffix_tolerated(self):
        rows = [PartitionRow("c", "p", "up", 3600, 1, "mixed",
                             "gpu:l40s:4(S:0-1),shard:l40s:16(S:0-1)")]
        self.assertEqual(gpu.shards_per_card(rows), {"l40s": 4})


if __name__ == "__main__":
    unittest.main()
