"""Tests of the static stability pattern in core.do_work (no cluster needed).

core.call_dep is replaced by fake functions, like in the QazMarket example.
"""
import time
import unittest
import urllib.error

import core

ORIGINAL_CALL_DEP = core.call_dep


def dep_ok(version):
    def fake(timeout=None):
        return {"plan_version": version, "waypoints": [{"id": "NEW"}], "issued_at": time.time()}
    return fake


def dep_503(timeout=None):
    raise urllib.error.HTTPError("http://dep-a/", 503, "Service Unavailable", None, None)


def dep_slow(timeout=None):
    time.sleep(min(timeout or 10, 3))          # honours the timeout like urllib would
    raise TimeoutError("timed out")


class TestStaticStability(unittest.TestCase):
    def setUp(self):
        core.VERBOSE = False
        core.PATTERN = True
        core.PLAN_REFRESH_S = 1.0
        core.PLAN_MAX_AGE_S = 60.0
        core.DEP_TIMEOUT_ON_S = 0.3
        core.reset_state()

    def tearDown(self):
        core.call_dep = ORIGINAL_CALL_DEP

    def test_1_dep_ok_plan_refreshed(self):
        core.call_dep = dep_ok(7)
        r = core.do_work()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["plan_version"], 7)

    def test_2_dep_503_answer_from_memory(self):
        core.call_dep = dep_ok(3)
        core.do_work()                               # plan v3 in memory
        core._state["last_try"] = 0                  # force the next refresh
        core.call_dep = dep_503
        start = time.time()
        r = core.do_work()                           # must not raise
        self.assertLess(time.time() - start, 0.5)
        self.assertEqual(r["status"], "static")
        self.assertEqual(r["plan_version"], 3)

    def test_3_dep_slow_answer_faster_than_client_timeout(self):
        core.call_dep = dep_slow
        start = time.time()
        r = core.do_work()
        self.assertLess(time.time() - start, 1.5)
        self.assertEqual(r["status"], "static")

    def test_4_cold_start_without_dep_uses_preflight_plan(self):
        core.call_dep = dep_503
        r = core.do_work()
        self.assertEqual(r["status"], "static")
        self.assertEqual(r["plan_version"], core.PREFLIGHT_PLAN["plan_version"])
        self.assertEqual(r["next_waypoint"]["id"], "WP1")

    def test_5_plan_older_than_max_age_goes_failsafe(self):
        core.reset_state(plan_time=time.time() - 100)   # plan is 100 s old
        core.call_dep = dep_503
        with self.assertRaises(core.Failsafe):
            core.do_work()

    def test_6_pattern_off_calls_dep_directly(self):
        core.PATTERN = False
        core.call_dep = dep_503
        with self.assertRaises(urllib.error.HTTPError):
            core.do_work()

    def test_7_recovery_returns_to_ok_with_new_plan(self):
        core.call_dep = dep_503
        self.assertEqual(core.do_work()["status"], "static")
        core._state["last_try"] = 0
        core.call_dep = dep_ok(12)
        r = core.do_work()
        self.assertEqual(r["status"], "ok")
        self.assertEqual(r["plan_version"], 12)

    def test_8_only_one_thread_refreshes(self):
        calls = []

        def slow_counting_dep(timeout=None):
            calls.append(1)
            time.sleep(0.2)
            return {"plan_version": 5, "waypoints": [{"id": "X"}]}

        core.call_dep = slow_counting_dep
        import threading
        threads = [threading.Thread(target=core.do_work) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
