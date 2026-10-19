#!/usr/bin/env python3
"""deny-secret-reads: refuse shell commands that would print a credential.

PreToolUse hook for Bash and PowerShell. Denies a command when one of its
pipelines would print

  * the contents of a file that holds credentials in plaintext (shell rc and
    history files, .env, .netrc, .pgpass, git/gh/glab/docker/kube/npm/pypi
    credential files, the op/ and claude-docker env files, SSH private keys,
    /proc/*/environ, backups of any of these), or a recursive grep over a tree
    that holds them (~, ~/.config, ~/.aws, ...), or
  * the process environment (`env`, `printenv`, `export -p`, `gci env:`) or a
    secret-named variable (`echo $GH_TOKEN`, `$env:GH_TOKEN`),

unless that same pipeline is already redaction-shaped (counts, names only, a
substitution that drops the value, `${#VAR}`).

Why: "where is this configured?" and "what is its value?" are different
questions, and one `grep -n NAME ~/.bashrc` answers both. A credential printed
into a session transcript is on disk and cannot be unwritten; the only remedy is
rotation (2026-09-22). This is a guard against carelessness, not an adversarial
control: a determined command (python -c, git show, xargs) gets past it, and
that is accepted. The careless form fails loudly and names the safe one. The
Read/Grep/Glob tools are fenced by `permissions.deny` rules instead, which cost
no process per call.

Parsing is best-effort tokenisation, not a shell. Heredoc and here-string
BODIES are dropped first: a commit message or written-out doc names these files
as prose, and a guard that blocks ordinary commits gets switched off.

Runs on the Windows host (python) and in claude-docker boxes (python3); stdlib
only. Any internal error allows the command; it never breaks a session.
Tests: test_deny_secret_reads.py beside this file.
"""

import json
import re
import shlex
import sys

# --- what is a secret ---------------------------------------------------------

SECRET_BASENAMES = {
    ".bashrc", ".bash_profile", ".profile", ".zshrc", ".zprofile", ".envrc",
    ".bash_history", ".zsh_history", ".netrc", ".pgpass", ".git-credentials",
    ".npmrc", ".pypirc", ".claude.json", ".credentials.json",
    "consolehost_history.txt",  # PowerShell PSReadLine history
}
# Matched as a path suffix; each starts on a "/" boundary.
SECRET_SUFFIXES = (
    "/.aws/credentials", "/.config/gh/hosts.yml", "/.config/glab-cli/config.yml",
    "/.docker/config.json", "/.kube/config", "/claude-docker/env",
    "/.config/ai-transcribe/api-key",
)
SECRET_DIRS = ("/.config/op/",)
SECRET_NAME_RE = re.compile(
    r"^(id_(rsa|dsa|ecdsa|ed25519)|.+\.key|.+\.tfstate|.*service-account-token.*)$")
ENV_TEMPLATE_SUFFIXES = (".example", ".sample", ".template", ".dist")
BACKUP_RE = re.compile(r"(\.(bak|backup|orig|old|save)[^/]*|~)$")
# Directories a recursive grep must not sweep: home, and the credential dirs in it.
SECRET_TREE_RE = re.compile(
    r"^(~|\$\{?home\}?|\$env:userprofile|/root|/home/[^/]+|(/|[a-z]:/)users/[^/]+)"
    r"(/\.(config|aws|ssh|docker|kube)(/op)?)?$")

SECRET_VAR_RE = re.compile(
    r"TOKEN|SECRET|PASSW|API_?KEY|ACCESS_KEY|PRIVATE_KEY|CREDENTIAL|COOKIE"
    r"|(^|_)PAT($|_)|(^|_)AUTH$|_KEY$", re.I)
BASH_VAR_RE = re.compile(r"\$\{?([A-Za-z_][A-Za-z0-9_]*)")
PS_VAR_RE = re.compile(r"\$env:([A-Za-z_][A-Za-z0-9_]*)", re.I)


def norm(tok: str) -> str:
    return tok.strip("'\"").replace("\\", "/").lower()


def is_secret_path(tok: str) -> bool:
    p = norm(tok)
    if not p or p.startswith("-"):
        return False
    if p.startswith("/proc/") and p.endswith("/environ"):
        return True
    p = BACKUP_RE.sub("", p)
    slashed = "/" + p
    if any(d in slashed for d in SECRET_DIRS):
        return True
    if slashed.endswith(SECRET_SUFFIXES):
        return True
    name = p.rsplit("/", 1)[-1]
    if name in SECRET_BASENAMES or SECRET_NAME_RE.match(name):
        return True
    if name == ".env" or name.startswith(".env.") or (name.endswith(".env") and len(name) > 4):
        return not name.endswith(ENV_TEMPLATE_SUFFIXES)
    return False


def is_secret_tree(tok: str) -> bool:
    return bool(SECRET_TREE_RE.match(norm(tok).rstrip("/") or "/"))


def secret_vars(tok: str, ps: bool = False) -> bool:
    names = (PS_VAR_RE if ps else BASH_VAR_RE).findall(tok)
    return any(SECRET_VAR_RE.search(n) for n in names)


# --- bash ---------------------------------------------------------------------

GREPS = {"grep", "egrep", "fgrep", "zgrep", "rg"}
READERS = GREPS | {
    "cat", "tac", "sed", "awk", "gawk", "head", "tail", "less", "more",
    "strings", "od", "xxd", "hexdump", "nl", "base64", "bat", "diff", "sort",
    "uniq", "cut", "jq", "yq",
}
PATTERN_FIRST = GREPS | {"sed", "awk", "gawk", "jq", "yq"}
PATTERN_OPTS = {"-e", "-f", "--regexp", "--file"}  # pattern given by option
VALUE_OPTS = {  # options that consume the next word, per pattern-first tool
    "grep": {"-A", "-B", "-C", "-m", "--max-count"},
    "rg": {"-A", "-B", "-C", "-m", "-g", "-t", "-T", "-M", "--max-count", "--glob", "--type"},
    "awk": {"-F", "-v"}, "gawk": {"-F", "-v"},
}
SHELLS = {"bash", "sh", "zsh", "dash"}
POWERSHELLS = {"powershell", "powershell.exe", "pwsh", "pwsh.exe"}
SHELL_C_FLAGS = {"-c", "-ic", "-lc", "-lic", "-ci", "-command"}
PREFIXES = {"sudo", "command", "exec", "time", "nice", "nohup", "builtin", "timeout", "xargs"}
PREFIX_VALUE_OPTS = {"-u", "-g", "-n", "-s", "-k"}
# Commands whose payload is a later word (docker exec box cat x) or a quoted string.
WRAPPERS = {"docker", "kubectl", "wsl", "wsl.exe", "ssh", "watch"}
PUNCT = set(";&|<>(){}")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(cmd: str) -> str:
    out, marker = [], None
    for line in cmd.split("\n"):
        if marker is not None:
            if line.strip() == marker:
                marker = None
            continue
        m = HEREDOC_RE.search(line.replace("<<<", "   "))
        if m:
            marker = m.group(2)
        out.append(line)
    return "\n".join(out)


def strip_comments(cmd: str) -> str:
    """Drop unquoted `# ...` to end of line; `${#X}`, `a#b` and `'#'` stay."""
    out, quote, i = [], None, 0
    while i < len(cmd):
        ch = cmd[i]
        if quote:
            if ch == "\\" and quote == '"':
                out.append(cmd[i:i + 2])
                i += 2
                continue
            if ch == quote:
                quote = None
        elif ch == "\\":
            out.append(cmd[i:i + 2])
            i += 2
            continue
        elif ch in "'\"":
            quote = ch
        elif ch == "#" and (i == 0 or cmd[i - 1] in " \t\n;&|("):
            j = cmd.find("\n", i)
            i = len(cmd) if j < 0 else j
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def tokenize_bash(cmd: str) -> list:
    cmd = strip_comments(cmd)
    cmd = cmd.replace("\\\n", " ").replace("`", " ; ").replace("\n", " ; ")
    try:
        lex = shlex.shlex(cmd, posix=True, punctuation_chars=";&|<>(){}")
        lex.whitespace_split = True
        lex.commenters = ""  # `${#VAR}` must not swallow the rest of the line
        return list(lex)
    except ValueError:  # unbalanced quotes: fall back to a plain split
        for c in ";|()":
            cmd = cmd.replace(c, f" {c} ")
        return cmd.split()


def bash_pipelines(tokens: list) -> list:
    """[[{argv, inputs}]]: pipelines of commands with their `<` input files."""
    pipelines, pipe, cur = [], [], {"argv": [], "inputs": []}

    def flush_cmd():
        nonlocal cur
        if cur["argv"] or cur["inputs"]:
            pipe.append(cur)
        cur = {"argv": [], "inputs": []}

    def flush_pipe():
        nonlocal pipe
        flush_cmd()
        if pipe:
            pipelines.append(pipe)
        pipe = []

    it = iter(tokens)
    for tok in it:
        if not set(tok) <= PUNCT:
            cur["argv"].append(tok)
        elif tok == "<":
            cur["inputs"].append(next(it, ""))
        elif ">" in tok and set(tok) <= set("<>&|"):
            next(it, "")  # output redirect: its target is not read
        elif tok.strip("(){}") in ("|", "|&"):
            flush_cmd()
        else:
            flush_pipe()  # ; && || & ( ) { } <( and friends
    flush_pipe()
    return pipelines


def base(tok: str) -> str:
    return tok.replace("\\", "/").rsplit("/", 1)[-1].lower()


def strip_prefixes(argv: list) -> list:
    i = 0
    while i < len(argv):
        b = base(argv[i])
        if re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", argv[i]):
            i += 1
        elif b in PREFIXES:
            i += 1
            while i < len(argv) and argv[i].startswith("-"):
                i += 2 if argv[i] in PREFIX_VALUE_OPTS else 1
            if b == "timeout" and i < len(argv) and re.match(r"^\d+(\.\d+)?[smhd]?$", argv[i]):
                i += 1
        elif b == "env":
            j = i + 1  # `env [-opts] [VAR=x] cmd` launches cmd; bare `env` dumps
            while j < len(argv) and (argv[j].startswith("-") or "=" in argv[j]):
                j += 1
            if j == len(argv):
                break
            i = j
        else:
            break
    return argv[i:]


def file_args(name: str, args: list) -> list:
    positional, skip_next, pattern_given = [], False, False
    for a in args:
        if skip_next:
            skip_next = False
        elif a in PATTERN_OPTS:
            skip_next = pattern_given = True
        elif a.startswith(("--regexp=", "--file=")):
            pattern_given = True
        elif a in VALUE_OPTS.get(name, ()):
            skip_next = True
        elif not a.startswith("-") or a == "-":
            positional.append(a)
    if name in PATTERN_FIRST and not pattern_given:
        positional = positional[1:]
    return positional


def short_flags(args: list) -> set:
    out = set()
    for a in args:
        if a.startswith("-") and not a.startswith("--"):
            out.update(a[1:])
    return out


def is_redaction(cmd: dict) -> bool:
    argv = strip_prefixes(cmd["argv"])
    if not argv:
        return False
    name, args = base(argv[0]), argv[1:]
    joined = " ".join(argv)
    if "len=" in joined or "${#" in joined or "redact" in joined.lower():
        return True
    if name == "wc":
        return True
    if name in GREPS and (short_flags(args) & set("clLq") or any(a in (
            "--count", "--count-matches", "--files-with-matches",
            "--files-without-match", "--quiet", "--silent") for a in args)):
        return True
    if name == "cut" and re.search(r"(-d\s*=|--delimiter==)", joined) \
            and re.search(r"(-f\s*1\b|--fields=1\b)", joined):
        return True
    if name in ("sed", "awk", "gawk") and re.search(r"s([/|#])=\.[*+]\1|sub\(/=\.[*+]/", joined):
        return True
    if name in ("awk", "gawk") and re.search(r"-F\s*=", joined) and re.search(r"print \$1\s*}", joined):
        return True
    return False


def is_env_dump(argv: list) -> bool:
    name, args = base(argv[0]), argv[1:]
    if name == "env":
        return True  # strip_prefixes keeps `env` only when nothing follows it
    if name == "printenv":
        return not args or any(SECRET_VAR_RE.search(a) for a in args)
    if name in ("export", "declare", "typeset"):
        flags = [a for a in args if a.startswith("-")]
        names = [a for a in args if not a.startswith("-")]
        if not names:
            return name == "export" or any("p" in f or "x" in f for f in flags)
        return any("p" in f for f in flags) and any(SECRET_VAR_RE.search(n) for n in names)
    if name == "set":
        return not args
    if name in ("echo", "printf", "print"):
        return any(secret_vars(a) for a in args)
    return False


def bash_reason(cmd: str, depth: int = 0):
    if depth > 3:
        return None
    for pipe in bash_pipelines(tokenize_bash(strip_heredocs(cmd))):
        hit = None
        for c in pipe:
            if any(is_secret_path(f) for f in c["inputs"]):
                hit = hit or "file"
            argv = strip_prefixes(c["argv"])
            if not argv:
                continue
            name, args = base(argv[0]), argv[1:]
            hit = hit or nested_reason(name, args, depth)
            if name in READERS and not (name == "sed" and "i" in short_flags(args)):
                files = file_args(name, args)
                if any(is_secret_path(f) for f in files):
                    hit = hit or "file"
                recursive = name == "rg" or short_flags(args) & set("rR") or "--recursive" in args
                if name in GREPS and recursive and any(is_secret_tree(f) for f in files):
                    hit = hit or "file"
            if is_env_dump(argv):
                hit = hit or "env"
        if hit and not any(is_redaction(c) for c in pipe):
            return hit
    return None


def nested_reason(name: str, args: list, depth: int):
    """Commands that carry another command: `bash -c '...'`, `pwsh -Command`,
    `docker exec box cat x`, `ssh host '...'`."""
    if name in SHELLS or name in POWERSHELLS:
        for i, a in enumerate(args[:-1]):
            if a.lower() in SHELL_C_FLAGS:
                inner = args[i + 1]
                return (ps_reason(inner, depth + 1) if name in POWERSHELLS
                        else bash_reason(inner, depth + 1))
        return None
    if name in WRAPPERS:
        for i, a in enumerate(args):
            if " " in a:
                r = bash_reason(a, depth + 1)
                if r:
                    return r
            elif base(a) in READERS | SHELLS | POWERSHELLS | {"env", "printenv", "echo", "printf"}:
                return bash_reason(shlex.join(args[i:]), depth + 1)
    return None


# --- PowerShell ---------------------------------------------------------------

PS_READERS = {"get-content", "gc", "cat", "type", "select-string", "sls",
              "format-hex", "fhx", "more", "import-csv"}
PS_PATH_OPTS = {"-path", "-literalpath", "-lp"}
PS_VALUE_OPTS = {"-encoding", "-totalcount", "-tail", "-first", "-head",
                 "-delimiter", "-readcount", "-context"}
PS_REDACTION_RE = re.compile(
    r"measure-object|\bmeasure\b|-quiet\b|test-path|\.count\b|\.length\b|\.name\b"
    r"|-replace\s+['\"]=\.[*+]|redact"
    r"|select(-object)?\s+(-property\s+)?name\b|-expandproperty\s+name\b", re.I)
PS_ECHO = {"write-output", "echo", "write-host", "write-information", "write"}
PS_LISTERS = {"get-childitem", "gci", "ls", "dir", "get-item", "gi"}
HERESTRING_RE = re.compile(r"@(['\"])\r?\n.*?\r?\n\1@", re.S)
PS_TOKEN_RE = re.compile(r"'[^']*'|\"[^\"]*\"|[^\s|;{}()]+")


def ps_reader_hit(name: str, args: list) -> bool:
    need_pattern = name in ("select-string", "sls")
    skip_next = False
    for i, a in enumerate(args):
        low = a.lower()
        if skip_next:
            skip_next = False
        elif low in PS_PATH_OPTS:
            if i + 1 < len(args) and is_secret_path(args[i + 1]):
                return True
            skip_next = True
        elif low == "-pattern":
            need_pattern, skip_next = False, True
        elif low in PS_VALUE_OPTS:
            skip_next = True
        elif a.startswith("-"):
            continue
        elif need_pattern:
            need_pattern = False
        elif is_secret_path(a):
            return True
    return False


def ps_reason(cmd: str, depth: int = 0):
    if depth > 3:
        return None
    cmd = HERESTRING_RE.sub("''", cmd)
    for segment in re.split(r";|\n|&&|\|\|", cmd):
        hit = None
        for part in segment.split("|"):
            toks = PS_TOKEN_RE.findall(part)
            if not toks:
                continue
            name, args = toks[0].lower(), toks[1:]
            if name in PS_READERS and ps_reader_hit(name, args):
                hit = hit or "file"
            elif base(name) in READERS | SHELLS | POWERSHELLS | WRAPPERS:
                # a native tool (rg, wsl, bash -c) called from PowerShell
                inner = [t.strip("'\"") for t in toks]
                hit = hit or bash_reason(shlex.join(inner), depth + 1)
            if name in PS_LISTERS and any(
                    norm(a).rstrip("/") == "env:" or
                    (norm(a).startswith("env:") and SECRET_VAR_RE.search(norm(a)[4:].lstrip("/")))
                    for a in args):
                hit = hit or "env"
            if (name in PS_ECHO and any(secret_vars(a, ps=True) for a in args)) \
                    or secret_vars(toks[0], ps=True):
                hit = hit or "env"
            if name.startswith("[environment]::getenvironmentvariable"):
                if name.endswith("variables") or any(SECRET_VAR_RE.search(a) for a in args):
                    hit = hit or "env"
        if hit and not PS_REDACTION_RE.search(segment):
            return hit
    return None


# --- hook ---------------------------------------------------------------------

REASON = {
    "file": "this would print the contents of a file that holds credentials in "
            "plaintext (a shell rc or history file, .env, .netrc, .pgpass, a "
            "git/gh/glab/docker/kube/npm credential file, an op/ or claude-docker "
            "env file, a private key, a backup of one, or a recursive grep over "
            "a directory that holds them)",
    "env": "this would print the process environment or a secret-named variable",
}
SAFE_FORMS = (
    " Finding WHERE something is configured must not echo its value. Use: "
    "`grep -c NAME <file>` to confirm it is there; "
    "`grep -n NAME <file> | sed -E 's/=.*/=<redacted>/'` to see the line with the "
    "value stripped; `env | cut -d= -f1` for variable names; "
    "`echo \"len=${#VAR}\"` to prove a variable is populated. PowerShell: "
    "`Select-String NAME <file> -Quiet`, `(Get-ChildItem env:).Name`, "
    "`$env:VAR.Length`. If you genuinely need a value, ask the user to read it "
    "themselves.")


def decide(payload: dict):
    tool = payload.get("tool_name") or ""
    cmd = (payload.get("tool_input") or {}).get("command") or ""
    if not cmd:
        return None
    return ps_reason(cmd) if tool == "PowerShell" else bash_reason(cmd)


def main() -> int:
    try:
        hit = decide(json.loads(sys.stdin.read() or "{}"))
    except Exception as e:  # never break a session on a guard bug
        sys.stderr.write(f"deny-secret-reads: {e}\n")
        return 0
    if hit:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": "Blocked: " + REASON[hit] + "." + SAFE_FORMS,
        }}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
