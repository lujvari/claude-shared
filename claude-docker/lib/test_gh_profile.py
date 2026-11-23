"""Tests for lib/gh-profile.sh.

Each case runs the resolver in a clean env, called exactly as run.sh calls it
(`gh_profile_resolve || exit 1` under set -euo pipefail), and reads back the
variables it set.

Run: python3 -m unittest lib/test_gh_profile.py
"""

import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "gh-profile.sh")

OUT_VARS = ["GH_PROFILE", "GH_OP_REF_VAR", "GH_TOKEN", "GITHUB_TOKEN",
            "CLAUDE_DOCKER_GITHUB_OP_REF", "CLAUDE_DOCKER_GITHUB_HOSTS"]

SCRIPT = ('set -euo pipefail; . "$0"; gh_profile_resolve || exit 1; '
          + "".join(f'printf "%s=%s\\n" {v} "${{{v}-<unset>}}"; '
                    for v in OUT_VARS))

INAT = {"WITH_GH": "1", "CLAUDE_DOCKER_GITHUB_PROFILE": "inat",
        "CLAUDE_DOCKER_GITHUB_INAT_OP_REF": "op://v/inat/credential"}


def run(env):
    e = {"PATH": os.environ["PATH"]}
    e.update(env)
    p = subprocess.run([shutil.which("bash"), "-c", SCRIPT, LIB], env=e,
                       capture_output=True, text=True, timeout=10)
    out = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    return p.returncode, out, p.stderr


class GhProfileTest(unittest.TestCase):
    def assertAborts(self, env, needle):
        rc, out, err = run(env)
        self.assertEqual(rc, 1, err)
        self.assertIn(needle, err)
        self.assertEqual(out, {})

    def test_no_profile_passes_through(self):
        rc, out, err = run({"WITH_GH": "1", "GH_TOKEN": "host",
                            "CLAUDE_DOCKER_GITHUB_OP_REF": "op://v/pat/credential",
                            "CLAUDE_DOCKER_GITHUB_HOSTS": "github.com,ghe.example"})
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out["GH_PROFILE"], "")
        self.assertEqual(out["GH_TOKEN"], "host")
        self.assertEqual(out["CLAUDE_DOCKER_GITHUB_OP_REF"], "op://v/pat/credential")
        self.assertEqual(out["CLAUDE_DOCKER_GITHUB_HOSTS"], "github.com,ghe.example")

    def test_profile_ok(self):
        rc, out, err = run(dict(INAT,
                                CLAUDE_DOCKER_GITHUB_OP_REF="op://v/pat/credential",
                                CLAUDE_DOCKER_GITHUB_HOSTS="github.com,ghe.example"))
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out["GH_PROFILE"], "inat")
        self.assertEqual(out["GH_OP_REF_VAR"], "CLAUDE_DOCKER_GITHUB_INAT_OP_REF")
        self.assertEqual(out["CLAUDE_DOCKER_GITHUB_OP_REF"], "op://v/inat/credential")
        self.assertEqual(out["CLAUDE_DOCKER_GITHUB_HOSTS"], "github.com")

    def test_host_tokens_dropped_with_note(self):
        rc, out, err = run(dict(INAT, GH_TOKEN="personal-1", GITHUB_TOKEN="personal-2"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(out["GH_TOKEN"], "<unset>")
        self.assertEqual(out["GITHUB_TOKEN"], "<unset>")
        self.assertIn("ignoring GH_TOKEN", err)
        self.assertIn("ignoring GITHUB_TOKEN", err)
        self.assertNotIn("personal-", err)

    def test_missing_op_ref(self):
        env = dict(INAT, CLAUDE_DOCKER_GITHUB_OP_REF="op://v/pat/credential")
        del env["CLAUDE_DOCKER_GITHUB_INAT_OP_REF"]
        self.assertAborts(env, "needs CLAUDE_DOCKER_GITHUB_INAT_OP_REF")
        self.assertAborts(dict(INAT, CLAUDE_DOCKER_GITHUB_INAT_OP_REF=""),
                          "needs CLAUDE_DOCKER_GITHUB_INAT_OP_REF")

    def test_bad_names(self):
        for name in ["Inat", "in-at", "in at", "inat;x", "../x"]:
            with self.subTest(name=name):
                self.assertAborts(dict(INAT, CLAUDE_DOCKER_GITHUB_PROFILE=name),
                                  "is not a profile name")

    def test_profile_without_gh_is_inert(self):
        rc, out, err = run({"WITH_GH": "0", "GH_TOKEN": "host",
                            "CLAUDE_DOCKER_GITHUB_PROFILE": "inat"})
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out["GH_PROFILE"], "")
        self.assertEqual(out["GH_TOKEN"], "host")
        self.assertEqual(out["CLAUDE_DOCKER_GITHUB_HOSTS"], "<unset>")


if __name__ == "__main__":
    unittest.main()
