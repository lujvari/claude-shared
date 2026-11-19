"""Tests for lib/ado-profile.sh.

Each case runs the resolver in a clean env, called exactly as run.sh calls it
(`ado_profile_resolve || exit 1` under set -euo pipefail), and reads back the
variables it set.

Run: python3 -m unittest lib/test_ado_profile.py
"""

import os
import shutil
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "ado-profile.sh")

OUT_VARS = ["ADO_PROFILE", "ADO_OP_REF_VAR", "ADO_OP_REF",
            "AZURE_DEVOPS_EXT_PAT", "CLAUDE_DOCKER_ADO_ORG",
            "CLAUDE_DOCKER_ADO_HOSTS"]

SCRIPT = ('set -euo pipefail; . "$0"; ado_profile_resolve || exit 1; '
          + "".join(f'printf "%s=%s\\n" {v} "${{{v}-<unset>}}"; '
                    for v in OUT_VARS))

APG = {"WITH_ADO": "1", "CLAUDE_DOCKER_ADO_PROFILE": "apg",
       "CLAUDE_DOCKER_ADO_APG_OP_REF": "op://v/APG/credential",
       "CLAUDE_DOCKER_ADO_APG_ORGS": "aamnld"}


def run(env):
    e = {"PATH": os.environ["PATH"]}
    e.update(env)
    p = subprocess.run([shutil.which("bash"), "-c", SCRIPT, LIB], env=e,
                       capture_output=True, text=True, timeout=10)
    out = dict(l.split("=", 1) for l in p.stdout.splitlines() if "=" in l)
    return p.returncode, out, p.stderr


class AdoProfileTest(unittest.TestCase):
    def assertAborts(self, env, needle):
        rc, out, err = run(env)
        self.assertEqual(rc, 1, err)
        self.assertIn(needle, err)
        self.assertEqual(out, {})

    def test_no_profile_passes_through(self):
        rc, out, err = run({"WITH_ADO": "1",
                            "CLAUDE_DOCKER_ADO_OP_REF": "op://v/SBP/credential",
                            "CLAUDE_DOCKER_ADO_ORG": "sbp-controltower",
                            "AZURE_DEVOPS_EXT_PAT": "host"})
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out["ADO_PROFILE"], "")
        self.assertEqual(out["ADO_OP_REF"], "op://v/SBP/credential")
        self.assertEqual(out["AZURE_DEVOPS_EXT_PAT"], "host")
        self.assertEqual(out["CLAUDE_DOCKER_ADO_ORG"], "sbp-controltower")
        self.assertEqual(out["CLAUDE_DOCKER_ADO_HOSTS"], "<unset>")

    def test_profile_ok(self):
        rc, out, err = run(dict(APG, CLAUDE_DOCKER_ADO_OP_REF="op://v/SBP/x",
                                CLAUDE_DOCKER_ADO_ORG="sbp-controltower",
                                CLAUDE_DOCKER_ADO_HOSTS="dev.azure.com",
                                CLAUDE_DOCKER_ADO_APG_ORGS="aamnld,apgnld"))
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out["ADO_PROFILE"], "apg")
        self.assertEqual(out["ADO_OP_REF_VAR"], "CLAUDE_DOCKER_ADO_APG_OP_REF")
        self.assertEqual(out["ADO_OP_REF"], "op://v/APG/credential")
        self.assertEqual(out["CLAUDE_DOCKER_ADO_ORG"], "aamnld,apgnld")
        self.assertEqual(out["CLAUDE_DOCKER_ADO_HOSTS"],
                         "dev.azure.com/aamnld,dev.azure.com/apgnld")

    def test_host_pat_dropped_with_note(self):
        rc, out, err = run(dict(APG, AZURE_DEVOPS_EXT_PAT="sbp-token"))
        self.assertEqual(rc, 0, err)
        self.assertEqual(out["AZURE_DEVOPS_EXT_PAT"], "<unset>")
        self.assertIn("ignoring AZURE_DEVOPS_EXT_PAT", err)
        self.assertNotIn("sbp-token", err)

    def test_missing_op_ref(self):
        env = dict(APG, CLAUDE_DOCKER_ADO_OP_REF="op://v/SBP/credential")
        del env["CLAUDE_DOCKER_ADO_APG_OP_REF"]
        self.assertAborts(env, "CLAUDE_DOCKER_ADO_APG_OP_REF")

    def test_bad_orgs(self):
        for orgs in ["", "a/b", "a,,b", ",a", "a,", "a b", "a;b"]:
            with self.subTest(orgs=orgs):
                self.assertAborts(dict(APG, CLAUDE_DOCKER_ADO_APG_ORGS=orgs),
                                  "CLAUDE_DOCKER_ADO_APG_ORGS")
        env = dict(APG)
        del env["CLAUDE_DOCKER_ADO_APG_ORGS"]
        self.assertAborts(env, "CLAUDE_DOCKER_ADO_APG_ORGS")

    def test_bad_names(self):
        for name in ["apg;x", "APG", "a-b", "a b"]:
            with self.subTest(name=name):
                self.assertAborts(dict(APG, CLAUDE_DOCKER_ADO_PROFILE=name),
                                  "CLAUDE_DOCKER_ADO_PROFILE")

    def test_admin_refused(self):
        for ado in ["1", "0"]:
            with self.subTest(with_ado=ado):
                self.assertAborts(dict(APG, WITH_ADO=ado, WITH_ADO_ADMIN="1"),
                                  "--ado-admin")

    def test_profile_without_ado_is_inert(self):
        rc, out, err = run(dict(APG, WITH_ADO="0", AZURE_DEVOPS_EXT_PAT="x"))
        self.assertEqual((rc, err), (0, ""))
        self.assertEqual(out["ADO_PROFILE"], "")
        self.assertEqual(out["ADO_OP_REF"], "")
        self.assertEqual(out["AZURE_DEVOPS_EXT_PAT"], "x")
        self.assertEqual(out["CLAUDE_DOCKER_ADO_HOSTS"], "<unset>")


if __name__ == "__main__":
    unittest.main()
