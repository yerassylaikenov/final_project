"""metrics.py on the 20-request example from the slides: 0.30 / 1 / 360 / 0.70 / 45-1003-1004."""
import os
import tempfile
import unittest

import metrics

# 2 requests per second, t = 0.0, 0.5, ..., 9.5
STATUSES = ([200, 200] * 4            # seconds 0-3
            + [500, 500, 500, 503, 503, 500]  # seconds 4, 5, 6
            + [200, 200] * 3)         # seconds 7-9
OK_LAT = [38, 39, 39, 40, 40, 41, 42, 43, 44, 45, 46, 47, 51, 180]
FAIL_LAT = [1000, 1001, 1001, 1002, 1003, 1004]


def example_rows():
    ok, fail = iter(OK_LAT), iter(FAIL_LAT)
    return [(i * 0.5, s, next(ok) if s == 200 else next(fail)) for i, s in enumerate(STATUSES)]


class TestMetricsExample(unittest.TestCase):
    def setUp(self):
        self.m = metrics.compute(example_rows())

    def test_pofod(self):
        self.assertAlmostEqual(self.m["pofod"], 0.30)

    def test_episodes_and_rocof(self):
        self.assertEqual(self.m["episodes"], 1)
        self.assertAlmostEqual(self.m["rocof_per_h"], 360.0)

    def test_avail(self):
        self.assertAlmostEqual(self.m["avail"], 0.70)

    def test_percentiles(self):
        self.assertEqual((self.m["p50_ms"], self.m["p95_ms"], self.m["p99_ms"]), (45, 1003, 1004))

    def test_csv_roundtrip(self):
        path = os.path.join(tempfile.mkdtemp(), "example.csv")
        with open(path, "w") as f:
            f.write("t,status,latency_ms\n")
            for t, s, l in example_rows():
                f.write(f"{t},{s},{l}\n")
        self.assertEqual(metrics.compute(metrics.load(path)), self.m)


if __name__ == "__main__":
    unittest.main()
