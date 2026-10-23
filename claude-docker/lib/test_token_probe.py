"""Tests for lib/token-probe.sh, driven through a stub curl.

The stub reads the curl config from stdin, looks up the url in a scripted
response table and records its argv and stdin, so the tests can check the
warnings, the quiet cases, and that no token ever reaches argv or stderr.

Run: python3 -m unittest lib/test_token_probe.py
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "token-probe.sh")

STUB = r"""#!/usr/bin/env python3
import json, os, re, sys, uuid
cfg = sys.stdin.read()
log = os.environ["STUB_LOG"]
with open(os.path.join(log, uuid.uuid4().hex + ".json"), "w") as f:
    json.dump({"argv": sys.argv[1:], "stdin": cfg}, f)
url = re.search(r'^url = "(.*)"$', cfg, re.M).group(1)
table = json.load(open(os.environ["STUB_TABLE"]))
resp = next((v for k, v in table.items() if k in url), {"code": "200"})
out = sys.argv[sys.argv.index("-o") + 1]
with open(out, "w") as f:
    f.write(resp.get("body", ""))
sys.stdout.write(resp.get("code", "000"))
sys.exit(resp.get("exit", 0))
"""

# Tools the library calls besides curl; the no-curl test gets only these.
TOOLS = ["bash", "cat", "grep", "mktemp", "rm", "env", "python3"]

TOKENS = {
    "GH_TOKEN": "ghp_SECRETgh111",
    "GITLAB_TOKEN": "glpat-SECRETgl222",
    "AZURE_DEVOPS_EXT_PAT": "SECRETado333",
    "AZURE_DEVOPS_ADMIN_PAT": "SECRETadoadmin444",
    "JIRA_API_TOKEN": "SECRETjira555",
    "SUPABASE_ACCESS_TOKEN": "sbp_SECRETsb666",
    "CLOUDFLARE_API_TOKEN": "SECRETcf777",
    "OPENROUTER_API_KEY": "sk-or-SECRETor888",
    "SONAR_TOKEN": "SECRETsonar999",
    "TF_TOKEN_app_terraform_io": "SECRETtfe000",
    "HCLOUD_TOKEN": "SECREThc121",
}
FLAGS = ["WITH_GH", "WITH_GLAB", "WITH_ADO", "WITH_ADO_ADMIN", "WITH_JIRA",
         "WITH_SUPABASE", "WITH_CLOUDFLARE", "WITH_OPENROUTER", "WITH_SONAR",
         "WITH_TFE", "WITH_HETZNER_INFRA"]


class TokenProbeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bin = os.path.join(self.tmp, "bin")
        self.tools = os.path.join(self.tmp, "tools")
        self.log = os.path.join(self.tmp, "log")
        for d in (self.bin, self.tools, self.log):
            os.mkdir(d)
        for t in TOOLS:
            os.symlink(shutil.which(t), os.path.join(self.tools, t))
        curl = os.path.join(self.bin, "curl")
        with open(curl, "w") as f:
            f.write(STUB)
        os.chmod(curl, os.stat(curl).st_mode | stat.S_IEXEC)
        self.table = os.path.join(self.tmp, "table.json")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_probe(self, table=None, env=None, with_curl=True):
        with open(self.table, "w") as f:
            json.dump(table or {}, f)
        path = self.tools if not with_curl else self.bin + ":" + self.tools
        e = {"PATH": path, "STUB_LOG": self.log, "STUB_TABLE": self.table,
             "TMPDIR": self.tmp}
        e.update(env or {})
        p = subprocess.run(
            [shutil.which("bash"), "-c",
             'set -euo pipefail; . "$0"; token_probe_all; '
             'printf %s "$TOKEN_PROBE_REJECTED"', LIB],
            env=e, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.rejected = p.stdout
        return p.stderr

    def calls(self):
        out = []
        for n in os.listdir(self.log):
            with open(os.path.join(self.log, n)) as f:
                out.append(json.load(f))
        return out

    def all_on(self, **extra):
        env = dict(TOKENS)
        env.update({f: "1" for f in FLAGS})
        env.update({"CLAUDE_DOCKER_ADO_ORG": "sbp-controltower",
                    "JIRA_BASE_URL": "https://example.atlassian.net",
                    "JIRA_USER_EMAIL": "me@example.com"})
        env.update(extra)
        return env

    def test_401_warns_for_each_flag(self):
        stderr = self.run_probe({"": {"code": "401"}}, self.all_on())
        for flag in ["--gh", "--glab", "--ado", "--ado-admin", "--jira",
                     "--supabase", "--cloudflare", "--openrouter", "--sonar",
                     "--tfe", "--hetzner-infra"]:
            self.assertIn(
                f"claude-docker: {flag} token rejected (HTTP 401) - rotate it "
                "on the host before relying on this box", stderr)

    def test_200_is_quiet(self):
        self.assertEqual(self.run_probe({}, self.all_on()), "")
        self.assertEqual(len(self.calls()), 11)

    def test_offline_timeout_5xx_403_are_quiet(self):
        for resp in ({"code": "000", "exit": 6}, {"code": "000", "exit": 28},
                     {"code": "503"}, {"code": "404"}):
            self.assertEqual(self.run_probe({"": resp}, self.all_on(
                WITH_CLOUDFLARE="0")), "", resp)
        self.assertEqual(self.run_probe({"": {"code": "403"}}, self.all_on(
            WITH_CLOUDFLARE="0")), "")

    def test_no_token_in_argv_or_stderr(self):
        stderr = self.run_probe({"": {"code": "401"}}, self.all_on())
        calls = self.calls()
        self.assertTrue(calls)
        for c in calls:
            argv = " ".join(c["argv"])
            self.assertEqual(c["argv"][:2], ["-K", "-"])
            for tok in TOKENS.values():
                self.assertNotIn(tok, argv)
        for tok in TOKENS.values():
            self.assertNotIn(tok, stderr)
        # ...and the tokens did reach curl, on stdin
        stdin = "".join(c["stdin"] for c in calls)
        for tok in TOKENS.values():
            self.assertIn(tok, stdin)

    def test_basic_auth_uses_user_line(self):
        self.run_probe({}, {"WITH_ADO": "1", "CLAUDE_DOCKER_ADO_ORG": "org1",
                            "AZURE_DEVOPS_EXT_PAT": "p@ss\"w\\d"})
        (c,) = self.calls()
        self.assertIn('url = "https://dev.azure.com/org1/_apis/connectionData"',
                      c["stdin"])
        self.assertIn('user = ":p@ss\\"w\\\\d"', c["stdin"])
        self.assertIn('header = "X-TFS-FedAuthRedirect: Suppress"', c["stdin"])

    def test_ado_skipped_without_org(self):
        self.run_probe({}, {"WITH_ADO": "1", "AZURE_DEVOPS_EXT_PAT": "x"})
        self.assertEqual(self.calls(), [])

    def test_jira_skipped_without_base_url(self):
        self.run_probe({}, {"WITH_JIRA": "1", "JIRA_API_TOKEN": "x",
                            "JIRA_USER_EMAIL": "me@example.com"})
        self.assertEqual(self.calls(), [])

    def test_glab_warns_only_when_every_host_rejects(self):
        env = {"WITH_GLAB": "1", "GITLAB_TOKEN": "t",
               "glab_hosts": "gitlab.com gitlab.sbp.example"}
        one = {"gitlab.com": {"code": "401"}, "gitlab.sbp": {"code": "200"}}
        self.assertEqual(self.run_probe(one, env), "")
        both = {"gitlab": {"code": "401"}}
        self.assertIn("--glab token rejected", self.run_probe(both, env))

    def test_sonar_valid_false(self):
        env = {"WITH_SONAR": "1", "SONAR_TOKEN": "t"}
        bad = {"sonarcloud.io": {"code": "200", "body": '{"valid": false}'}}
        self.assertIn("--sonar token rejected (HTTP 200, valid:false)",
                      self.run_probe(bad, env))
        good = {"sonarcloud.io": {"code": "200", "body": '{"valid":true}'}}
        self.assertEqual(self.run_probe(good, env), "")

    def test_cloudflare_account_token_fallback(self):
        env = {"WITH_CLOUDFLARE": "1", "CLOUDFLARE_API_TOKEN": "t",
               "CLOUDFLARE_ACCOUNT_ID": "acc1"}
        acct_ok = {"/user/": {"code": "401"}, "/accounts/": {"code": "200"}}
        self.assertEqual(self.run_probe(acct_ok, env), "")
        both_bad = {"/user/": {"code": "401"}, "/accounts/": {"code": "403"}}
        self.assertIn("--cloudflare token rejected (HTTP 401)",
                      self.run_probe(both_bad, env))

    def test_rejected_list_for_statusline(self):
        env = {"WITH_GH": "1", "GH_TOKEN": "a", "WITH_SONAR": "1",
               "SONAR_TOKEN": "b", "WITH_SUPABASE": "1",
               "SUPABASE_ACCESS_TOKEN": "c"}
        self.run_probe({"github": {"code": "401"},
                        "sonarcloud": {"code": "200", "body": '{"valid":false}'}},
                       env)
        self.assertEqual(self.rejected, "gh,sonar")
        self.run_probe({}, env)
        self.assertEqual(self.rejected, "")

    def test_opt_out(self):
        env = self.all_on(CLAUDE_DOCKER_NO_TOKEN_PROBE="1")
        self.assertEqual(self.run_probe({"": {"code": "401"}}, env), "")
        self.assertEqual(self.calls(), [])

    def test_no_curl_is_silent(self):
        self.assertEqual(self.run_probe({}, self.all_on(), with_curl=False), "")

    def test_flag_without_token_is_skipped(self):
        self.run_probe({}, {"WITH_GH": "1"})
        self.assertEqual(self.calls(), [])

    def test_temp_dir_removed(self):
        self.run_probe({"": {"code": "401"}}, self.all_on())
        left = [n for n in os.listdir(self.tmp)
                if n.startswith("claude-docker-probe.")]
        self.assertEqual(left, [])


if __name__ == "__main__":
    unittest.main()
