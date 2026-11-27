"""Tests for run.sh --brain-notion (spec 0004), run through to `docker run`.

run.sh runs in a clean env (temp HOME, temp env file, no bus) with stubs on
PATH: `op` answers whoami, logs each ref it is asked to read and prints a fake
value; `docker` records the argv of `run` and the values of its `-e NAME`
variables, and launches nothing.

Run: python3 -m unittest lib/test_brain_notion.py
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.join(os.path.dirname(HERE), "run.sh")
DEFAULT_REF = "op://claude-docker/brain-notion-token/credential"
TOKEN = "fake-notion-token"
DB_ID = "fake-db-id"

DOCKER = r"""#!/usr/bin/env python3
import json, os, sys
if len(sys.argv) > 1 and sys.argv[1] == "run":
    a = sys.argv[1:]
    names = [a[i + 1] for i, x in enumerate(a[:-1]) if x == "-e" and "=" not in a[i + 1]]
    with open(os.environ["STUB_DOCKER_LOG"], "w") as f:
        json.dump({"argv": a, "env": {n: os.environ.get(n) for n in names}}, f)
sys.exit(0)
"""

OP = """#!/bin/sh
case "$1" in
  whoami) exit 0 ;;
  read) echo "$2" >> "$STUB_OP_LOG"; printf '%s' "${STUB_OP_VALUE-fake-notion-token}"; exit 0 ;;
esac
exit 0
"""


class BrainNotionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.bin = os.path.join(self.tmp, "bin")
        self.home = os.path.join(self.tmp, "home")
        self.ws = os.path.join(self.tmp, "ws")
        for d in (self.bin, os.path.join(self.home, ".claude"),
                  os.path.join(self.home, ".inat", "rules"), self.ws):
            os.makedirs(d)
        self._exe("docker", DOCKER)
        self._exe("op", OP)
        self.env_file = os.path.join(self.tmp, "env")
        self.docker_log = os.path.join(self.tmp, "docker.json")
        self.op_log = os.path.join(self.tmp, "op.log")

    def _exe(self, name, text):
        path = os.path.join(self.bin, name)
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)

    def run_sh(self, *flags, env_file="", **env):
        with open(self.env_file, "w") as f:
            f.write(env_file)
        e = {"PATH": f"{self.bin}:/usr/local/bin:/usr/bin:/bin", "HOME": self.home,
             "CLAUDE_DOCKER_ENV_FILE": self.env_file, "CLAUDE_DOCKER_BUS_DIR": "",
             "OP_SERVICE_ACCOUNT_TOKEN": "dummy",
             "STUB_DOCKER_LOG": self.docker_log, "STUB_OP_LOG": self.op_log, **env}
        return subprocess.run(["bash", RUN, *flags, self.ws], env=e,
                              capture_output=True, text=True)

    def docker_run(self):
        if not os.path.exists(self.docker_log):
            return None
        with open(self.docker_log) as f:
            return json.load(f)

    def op_reads(self):
        if not os.path.exists(self.op_log):
            return []
        with open(self.op_log) as f:
            return f.read().split()

    def assertNoValues(self, r):
        for v in (TOKEN, DB_ID):
            self.assertNotIn(v, r.stdout + r.stderr)

    # REQ-1
    def test_token_from_default_ref(self):
        r = self.run_sh("--brain-notion", env_file=f"BRAIN_NOTION_TEST_DATABASE_ID={DB_ID}\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.op_reads(), [DEFAULT_REF])
        self.assertEqual(self.docker_run()["env"]["BRAIN_NOTION_TOKEN"], TOKEN)

    def test_empty_ref_switches_op_off(self):
        r = self.run_sh("--brain-notion", env_file=f"BRAIN_NOTION_TEST_DATABASE_ID={DB_ID}\n",
                        CLAUDE_DOCKER_BRAIN_NOTION_OP_REF="")
        self.assertEqual(self.op_reads(), [])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--brain-notion skipped: BRAIN_NOTION_TOKEN", r.stderr)
        self.assertSkipped()

    def test_host_token_wins(self):
        r = self.run_sh("--brain-notion", BRAIN_NOTION_TOKEN="host-token",
                        BRAIN_NOTION_TEST_DATABASE_ID=DB_ID)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.op_reads(), [])
        self.assertEqual(self.docker_run()["env"]["BRAIN_NOTION_TOKEN"], "host-token")

    # REQ-2
    def test_database_id_from_env_file(self):
        self.run_sh("--brain-notion", env_file=f"BRAIN_NOTION_TEST_DATABASE_ID={DB_ID}\n")
        self.assertEqual(self.docker_run()["env"]["BRAIN_NOTION_TEST_DATABASE_ID"], DB_ID)
        self.assertEqual(self.op_reads(), [DEFAULT_REF])

    # REQ-3
    def assertSkipped(self):
        argv = self.docker_run()["argv"]
        self.assertNotIn("BRAIN_NOTION", " ".join(argv))
        self.assertFalse(any(a.startswith("CLAUDE_DOCKER_FLAGS=") and "brain-notion" in a
                             for a in argv))
        self.assertEqual(self.docker_run()["env"].get("BRAIN_NOTION_TEST_DATABASE_ID"), None)

    def test_missing_database_id_skips_flag_before_op(self):
        r = self.run_sh("--brain-notion")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--brain-notion skipped: BRAIN_NOTION_TEST_DATABASE_ID", r.stderr)
        self.assertEqual(self.op_reads(), [])
        self.assertSkipped()
        self.assertNoValues(r)

    def test_missing_token_skips_flag(self):
        r = self.run_sh("--brain-notion", env_file=f"BRAIN_NOTION_TEST_DATABASE_ID={DB_ID}\n",
                        STUB_OP_VALUE="")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--brain-notion skipped: BRAIN_NOTION_TOKEN", r.stderr)
        self.assertSkipped()
        self.assertNoValues(r)

    # REQ-4
    def test_flag_listed(self):
        self.run_sh("--brain-notion", env_file=f"BRAIN_NOTION_TEST_DATABASE_ID={DB_ID}\n")
        self.assertIn("CLAUDE_DOCKER_FLAGS=brain-notion", self.docker_run()["argv"])

    def test_without_flag_nothing_forwarded(self):
        r = self.run_sh(BRAIN_NOTION_TOKEN="host-token", BRAIN_NOTION_TEST_DATABASE_ID=DB_ID)
        self.assertEqual(r.returncode, 0, r.stderr)
        argv = " ".join(self.docker_run()["argv"])
        self.assertNotIn("BRAIN_NOTION", argv)
        self.assertEqual(self.op_reads(), [])


if __name__ == "__main__":
    unittest.main()
