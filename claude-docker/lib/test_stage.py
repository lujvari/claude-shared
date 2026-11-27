"""Tests for lib/stage.sh and run.sh's --stage parsing, driven through stubs.

The stub broker records each call and answers `register` with scripted exit
codes; the stub docker answers `ps` with a scripted container id. Covers a
clean register and teardown, both live-box refusals, crash-leftover recovery,
a broker refusal, and the flag checks run.sh makes before anything else.

Run: python3 -m unittest lib/test_stage.py
"""

import fcntl
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "stage.sh")
RUN = os.path.join(os.path.dirname(HERE), "run.sh")

BROKER = r"""#!/usr/bin/env python3
import json, os, sys
log = os.environ["STUB_LOG"]
calls = json.load(open(log)) if os.path.exists(log) else []
calls.append({"argv": sys.argv[1:], "bus": os.environ.get("CLAUDE_DOCKER_BUS_DIR")})
json.dump(calls, open(log, "w"))
if sys.argv[1] == "register":
    codes = os.environ.get("STUB_REGISTER", "0").split(",")
    n = sum(1 for c in calls if c["argv"][0] == "register")
    rc = int(codes[min(n, len(codes)) - 1])
    if rc:
        print("unknown project: nope" if rc == 2 else "already registered")
    sys.exit(rc)
sys.exit(int(os.environ.get("STUB_TEARDOWN", "0")))
"""

DOCKER = """#!/bin/sh
[ "$1" = ps ] && printf '%s' "${STUB_PS:-}"
exit 0
"""


class StageTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = os.path.join(self.tmp, "bin")
        os.makedirs(self.bin)
        self.broker = os.path.join(self.tmp, "stage_broker.py")
        self._write(self.broker, BROKER)
        self._write(os.path.join(self.bin, "docker"), DOCKER)
        self.log = os.path.join(self.tmp, "calls.json")

    def _write(self, path, text):
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def run_lib(self, body, **env):
        script = f'set -euo pipefail\n. "{LIB}"\n{body}\n'
        e = {"PATH": f"{self.bin}:{os.environ['PATH']}", "HOME": self.tmp,
             "STUB_LOG": self.log, **env}
        return subprocess.run(["bash", "-c", script], env=e, capture_output=True, text=True)

    def calls(self):
        if not os.path.exists(self.log):
            return []
        import json
        with open(self.log) as f:
            return [c["argv"] for c in json.load(f)]

    def start(self, **env):
        return self.run_lib(
            f'stage_start "{self.broker}" /bus-dir laslo.demo demo && echo "key=$STAGE_KEY"; '
            'stage_teardown; echo "after=$STAGE_KEY"', **env)

    def test_registers_then_tears_down(self):
        r = self.start()
        self.assertIn("key=laslo.demo", r.stdout)
        self.assertIn("after=", r.stdout)
        self.assertEqual(self.calls(), [["register", "laslo.demo", "demo"],
                                        ["teardown", "laslo.demo"]])

    def test_broker_gets_the_bus_dir(self):
        self.start()
        import json
        with open(self.log) as f:
            self.assertTrue(all(c["bus"] == "/bus-dir" for c in json.load(f)))

    def test_held_lock_refuses_without_registering(self):
        locks = os.path.join(self.tmp, ".cache", "claude-docker", "locks")
        os.makedirs(locks)
        with open(os.path.join(locks, "stage-laslo.demo.lock"), "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            r = self.start()
        self.assertNotIn("key=", r.stdout)
        self.assertIn("a live box already has the key laslo.demo", r.stderr)
        self.assertEqual(self.calls(), [])

    def test_running_container_with_key_refuses(self):
        r = self.start(STUB_PS="abc123\n")
        self.assertNotIn("key=", r.stdout)
        self.assertIn("a running container already has the key", r.stderr)
        self.assertEqual(self.calls(), [])

    def test_crash_leftover_is_torn_down_then_registered(self):
        r = self.start(STUB_REGISTER="1,0")
        self.assertIn("key=laslo.demo", r.stdout)
        self.assertIn("crash leftover", r.stderr)
        self.assertEqual([c[0] for c in self.calls()],
                         ["register", "teardown", "register", "teardown"])

    def test_broker_refusal_fails_and_leaves_nothing_to_tear_down(self):
        r = self.start(STUB_REGISTER="2")
        self.assertNotIn("key=", r.stdout)
        self.assertIn("--stage demo: unknown project: nope", r.stderr)
        self.assertEqual(self.calls(), [["register", "laslo.demo", "demo"]])

    def test_missing_broker_refuses(self):
        r = self.run_lib('stage_start /nonexistent/stage_broker.py /b k p || echo refused')
        self.assertIn("refused", r.stdout)
        self.assertIn("no broker at /nonexistent/stage_broker.py", r.stderr)

    def test_teardown_failure_reports_but_never_fails(self):
        r = self.start(STUB_TEARDOWN="1")
        self.assertEqual(r.returncode, 0)
        self.assertIn("stage teardown failed; run: stage_broker.py teardown laslo.demo", r.stderr)

    def test_teardown_without_start_is_a_noop(self):
        r = self.run_lib("stage_teardown")
        self.assertEqual(r.returncode, 0)
        self.assertEqual(self.calls(), [])


class RunFlagTest(unittest.TestCase):
    """run.sh rejects a bad --stage before mounting, reading or launching anything."""

    def run_sh(self, *args):
        return subprocess.run(["bash", RUN, *args], capture_output=True, text=True,
                              env={**os.environ, "CLAUDE_DOCKER_BUS_DIR": ""})

    def test_bad_values_rejected(self):
        for args in (["--stage"], ["--stage="], ["--stage=Bad"], ["--stage", "-x"],
                     ["--stage", "a/b"]):
            r = self.run_sh(*args)
            self.assertEqual(r.returncode, 1, args)
            self.assertIn("--stage needs a project name", r.stderr, args)

    def test_needs_mailbox(self):
        r = self.run_sh("--stage", "demo", tempfile.gettempdir())
        self.assertEqual(r.returncode, 1)
        self.assertIn("--stage needs the agent-bus mailbox", r.stderr)


if __name__ == "__main__":
    unittest.main()
