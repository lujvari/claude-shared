"""Tests for deny-secret-reads.py. Run: python3 -m unittest test_deny_secret_reads
(from this directory), or `python3 test_deny_secret_reads.py`."""

import importlib.util
import io
import json
import os
import sys
import unittest
from unittest import mock

_spec = importlib.util.spec_from_file_location(
    "deny_secret_reads", os.path.join(os.path.dirname(os.path.abspath(__file__)), "deny-secret-reads.py"))
hook = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(hook)


def bash(cmd):
    return hook.decide({"tool_name": "Bash", "tool_input": {"command": cmd}})


def ps(cmd):
    return hook.decide({"tool_name": "PowerShell", "tool_input": {"command": cmd}})


class Cases(unittest.TestCase):
    def deny(self, fn, cmds, kind=None):
        for c in cmds:
            with self.subTest(cmd=c):
                got = fn(c)
                self.assertIsNotNone(got, f"allowed: {c}")
                if kind:
                    self.assertEqual(got, kind)

    def allow(self, fn, cmds):
        for c in cmds:
            with self.subTest(cmd=c):
                self.assertIsNone(fn(c), f"denied: {c}")


class BashFiles(Cases):
    def test_historical_true_positives(self):
        # Commands that actually ran (or were blocked) in past sessions.
        self.deny(bash, [
            'grep -n "OP_SERVICE_ACCOUNT_TOKEN" ~/.bashrc',
            "cat ~/.config/op/service-account-token",
            "head -c 20 /mnt/c/dev/infra/.config/op/service-account-token",
            "sed -n '1,40p' ~/.config/claude-docker/env",
        ], "file")

    def test_historical_false_positives(self):
        self.allow(bash, [
            "head -5 ~/.claude/settings.json",
            "sed -i 's/# old comment/# new comment/' ~/.bashrc",
            'grep "\\.env" docker-compose.yml',
            "python3 - <<'EOF'\nimport re\np = 'OPEN.md'\n# cat ~/.bashrc and .env\nEOF",
            'git commit -m "$(cat <<\'EOF\'\nstop printing ~/.bashrc and .env\nEOF\n)"',
        ])

    def test_readers_on_secret_files(self):
        self.deny(bash, [
            "cat .env", "cat ./app/.env.local", "cat config/prod.env",
            "tail -n 5 ~/.bash_history", "less ~/.netrc", "cat ~/.pgpass",
            "cat ~/.aws/credentials", "cat ~/.git-credentials", "cat ~/.npmrc",
            "cat ~/.docker/config.json", "cat ~/.kube/config",
            "cat ~/.config/gh/hosts.yml", "cat ~/.config/glab-cli/config.yml",
            "cat ~/.ssh/id_ed25519", "cat server.key", "cat terraform.tfstate",
            "cat terraform.tfstate.backup", "cat ~/.bashrc.bak-2026-10-01",
            "cat ~/.bashrc~", "cat /proc/self/environ", "cat /proc/1/environ | tr '\\0' '\\n'",
            "jq . ~/.claude.json", "base64 ~/.claude/.credentials.json",
            "grep -e TOKEN ~/.zshrc", "grep -A 3 TOKEN ~/.profile",
            "awk '{print}' .env", "xxd ~/.netrc", "diff ~/.bashrc ~/.bashrc.orig",
            "cat 'C:\\Users\\me\\.aws\\credentials'", "cat ~/.config/ai-transcribe/api-key",
            "cat ~/.envrc",
        ], "file")

    def test_input_redirect(self):
        self.deny(bash, ["while read l; do echo \"$l\"; done < ~/.bashrc", "tr a b < .env"])
        self.allow(bash, ["grep -c TOKEN < ~/.bashrc"])

    def test_recursive_grep_over_home(self):
        self.deny(bash, ["grep -rn TOKEN ~", "grep -R TOKEN ~/.config/", "rg TOKEN $HOME",
                         "rg -n OP_ /root"])
        self.allow(bash, ["grep -rn TOKEN src/", "rg TOKEN ~/projects/app", "grep -rl TOKEN ~"])

    def test_non_secret_files(self):
        self.allow(bash, [
            "cat .env.example", "cat .env.sample", "cat README.md",
            "cat ~/.ssh/id_ed25519.pub", "cat ~/.ssh/config", "cat keys.py",
            "cat ~/.claude/settings.json", "cat docker-compose.yml",
            "cat api.key.example", "cat environment.md",
        ])

    def test_non_readers_on_secret_files(self):
        self.allow(bash, [
            "source ~/.bashrc", "cp ~/.bashrc /tmp/x", "ls -la ~/.config/op/",
            "chmod 600 ~/.netrc", "test -f .env && echo yes", "vim .env",
            "find . -name .env",
        ])

    def test_redaction_shapes(self):
        self.allow(bash, [
            "grep -c OP_SERVICE_ACCOUNT_TOKEN ~/.bashrc",
            "grep -l TOKEN ~/.bashrc ~/.profile",
            "grep -q TOKEN ~/.bashrc && echo set",
            "grep -cn TOKEN ~/.bashrc",
            "rg --count TOKEN ~/.bashrc",
            "grep -n NAME ~/.bashrc | sed -E 's/=.*/=<redacted>/'",
            "sed -n '10,20p' ~/.bashrc | sed -E 's/=.*/=<redacted>/'",
            "cut -d= -f1 .env",
            "awk -F= '{print $1}' .env",
            "cat ~/.bashrc | wc -l",
            'echo "len=${#OP_SERVICE_ACCOUNT_TOKEN}"',
        ])

    def test_redaction_is_per_pipeline(self):
        self.deny(bash, [
            "grep -c X ~/.bashrc; cat ~/.bashrc",
            "wc -l ~/.bashrc && grep TOKEN ~/.bashrc",
            'echo "len=${#X}"; cat .env',
        ])

    def test_fake_redaction(self):
        self.deny(bash, [
            "sed 's/=/: /' ~/.bashrc",
            "grep -C 3 TOKEN ~/.bashrc",
            "cat ~/.bashrc # redact",
            "grep '# export' ~/.bashrc",
            "grep \"#TOKEN\" ~/.bashrc",
        ])

    def test_comments(self):
        self.allow(bash, ["ls  # cat ~/.bashrc", "# cat .env\nls"])
        self.deny(bash, ["ls # note\ncat .env", "echo a#b; cat .env"])

    def test_compound_syntax(self):
        self.deny(bash, [
            "echo $(cat ~/.bashrc)", "echo `cat .env`", "x=1; cat .env",
            "true && head ~/.bashrc", "(cd /tmp && cat ~/.netrc)",
            "{ cat .env; }", "cat .env 2>/dev/null | head",
            "cat \\\n  ~/.bashrc", "diff <(cat ~/.bashrc) /dev/null",
            "echo ${#X}; cat .env",
        ])

    def test_prefixes(self):
        self.deny(bash, [
            "sudo cat /root/.bashrc", "sudo -u root cat /root/.bashrc",
            "timeout 5 cat .env", "FOO=1 cat .env", "env FOO=1 cat .env",
            "command cat .env",
        ])

    def test_nested_shells(self):
        self.deny(bash, [
            "bash -c 'cat ~/.bashrc'", "bash -lc \"grep TOKEN ~/.bashrc\"",
            "wsl.exe -e bash -ic 'cat ~/.bashrc'", "docker exec box cat /root/.bashrc",
            "ssh host 'cat ~/.netrc'", "docker exec box env",
            "pwsh -Command 'Get-Content ~/.bashrc'",
        ])
        self.allow(bash, ["bash -c 'grep -c TOKEN ~/.bashrc'", "docker exec box ls /root",
                          "bash -c 'cat ~/.bashrc' | wc -l"])

    def test_unbalanced_quotes_fall_back(self):
        self.deny(bash, ["cat .env 'oops"])


class BashEnv(Cases):
    def test_dumps(self):
        self.deny(bash, [
            "env", "env | sort", "printenv", "printenv GH_TOKEN", "export -p",
            "export", "declare -p", "declare -x", "set", "env | grep TOKEN",
            "sudo env", "env -0", "declare -p GH_TOKEN",
        ], "env")

    def test_secret_variables(self):
        self.deny(bash, [
            "echo $GH_TOKEN", 'echo "${OP_SERVICE_ACCOUNT_TOKEN}"',
            "printf '%s' \"$AWS_SECRET_ACCESS_KEY\"", "echo $DB_PASSWORD",
            "echo $GITLAB_PAT", "echo $ANTHROPIC_API_KEY",
        ], "env")

    def test_allowed(self):
        self.allow(bash, [
            "env | cut -d= -f1", "env | grep -c TOKEN", "printenv PATH",
            "echo $PATH", "echo $HOME $SSH_AUTH_SOCK", 'echo "len=${#GH_TOKEN}"',
            "echo ${#GH_TOKEN}", "env FOO=1 make", "env -u X make", "set -euo pipefail",
            "export FOO=bar", "declare -a arr", "export PATH=$PATH:/x",
        ])


class PowerShell(Cases):
    def test_files(self):
        self.deny(ps, [
            "Get-Content ~/.bashrc", "gc $HOME\\.aws\\credentials",
            "Get-Content -Path C:\\Users\\me\\.netrc -Raw",
            "Select-String -Path ~\\.bashrc -Pattern TOKEN",
            "Select-String TOKEN .env", "type .env",
            "cat $env:APPDATA\\Microsoft\\Windows\\PowerShell\\PSReadLine\\ConsoleHost_history.txt",
            "Get-Content .env | Select-Object -First 5",
            "rg TOKEN ~/.bashrc", "wsl -e bash -c 'cat ~/.bashrc'",
            "bash -c 'cat ~/.netrc'",
        ], "file")

    def test_env(self):
        self.deny(ps, [
            "Get-ChildItem env:", "gci env:GH_TOKEN", "ls Env:\\",
            "$env:GH_TOKEN", "Write-Output $env:OP_SERVICE_ACCOUNT_TOKEN",
            '"token is $env:GH_TOKEN"',
            "[Environment]::GetEnvironmentVariable('GH_TOKEN')",
            "[Environment]::GetEnvironmentVariables()",
        ], "env")

    def test_allowed(self):
        self.allow(ps, [
            "Select-String TOKEN ~/.bashrc -Quiet",
            "(Select-String TOKEN ~/.bashrc).Count",
            "Get-Content .env | Measure-Object -Line",
            "(Get-ChildItem env:).Name", "Get-ChildItem env: | Select-Object Name",
            "$env:GH_TOKEN.Length", "Test-Path ~/.bashrc", "Get-Content README.md",
            "gci env:PATH", "$env:PATH", "ls env", "Get-ChildItem C:\\dev",
            "[Environment]::GetEnvironmentVariable('PATH')",
            "(Get-Content .env) -replace '=.*','=<redacted>'",
            "git commit -m @'\nnever Get-Content .env again\n'@",
            "Select-String -Pattern TOKEN -Path ~\\.bashrc -Quiet",
        ])

    def test_fake_redaction(self):
        self.deny(ps, ["(Get-Content .env) -replace 'a','b'"])


class Hook(unittest.TestCase):
    def run_main(self, stdin):
        out = io.StringIO()
        with mock.patch.object(sys, "stdin", io.StringIO(stdin)), \
                mock.patch.object(sys, "stdout", out), \
                mock.patch.object(sys, "stderr", io.StringIO()):
            rc = hook.main()
        return rc, out.getvalue()

    def test_deny_json(self):
        rc, out = self.run_main(json.dumps({"tool_name": "Bash", "tool_input": {"command": "cat .env"}}))
        self.assertEqual(rc, 0)
        o = json.loads(out)["hookSpecificOutput"]
        self.assertEqual(o["permissionDecision"], "deny")
        self.assertEqual(o["hookEventName"], "PreToolUse")
        self.assertIn("grep -c NAME", o["permissionDecisionReason"])

    def test_allow_is_silent(self):
        self.assertEqual(self.run_main(json.dumps(
            {"tool_name": "Bash", "tool_input": {"command": "ls"}})), (0, ""))

    def test_fails_open(self):
        for bad in ["not json", "[]", "", json.dumps({"tool_input": None})]:
            with self.subTest(stdin=bad):
                self.assertEqual(self.run_main(bad), (0, ""))


if __name__ == "__main__":
    unittest.main()
