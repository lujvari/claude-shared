#!/usr/bin/env bash
# PreToolUse/Bash guard: refuse commands that would print the contents of a
# known secret-bearing file.
#
# Why this exists: "where is this configured?" and "what is its value?" are
# different questions, and one `grep -n NAME <shell rc>` answers both. Asking
# the first and getting the second prints a live credential into a session
# transcript — which is on disk and cannot be unwritten, so the only remedy is
# to rotate. Nothing in the loop distinguished the two questions. This does.
#
# It is a guard against carelessness, not an adversarial control: the
# redaction-shaped allowance below is trivially spoofable, and that is fine.
# The point is that the careless form fails loudly and names the safe one.
#
# No jq: the CLI is absent on the Windows host, and this same file runs under
# Git Bash there and at /root/.claude/hooks/ in every container.
set -u

payload=$(cat)

# Narrow to the command field when the payload has the expected shape, so a
# `description` mentioning a dotfile cannot trip the reader test. Falls back to
# the whole payload, which only ever over-denies — the safe direction.
cmd=$(printf '%s' "$payload" \
  | sed -e 's/.*"command"[[:space:]]*:[[:space:]]*"//' \
        -e 's/","description".*//' \
        -e 's/"[[:space:]]*}.*//')
[ -n "$cmd" ] || cmd="$payload"

# Drop heredoc BODIES before matching. A commit message or a written-out doc
# routinely names a shell rc or an env file as prose, and any reader elsewhere
# in the same command then made that a match — this hook blocked its own fix
# that way. A guard that blocks ordinary commits is a guard that gets switched
# off, so prose is excluded. Bodies only: the redirection line itself stays, and
# so does everything after the terminator, so a real read placed after a
# heredoc is still caught.
#
# The command arrives JSON-escaped on one line, so \n becomes a real newline
# first. Other escapes (\t, \") are irrelevant to the tests below.
cmd=$(printf '%s' "$cmd" | sed 's/\\n/\
/g' | awk '
  {
    if (inhere) {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      if (line == marker) inhere = 0
      next
    }
    if (match($0, /<<-?['"'"'"]?[A-Za-z_][A-Za-z0-9_]*['"'"'"]?/)) {
      marker = substr($0, RSTART, RLENGTH)
      sub(/^<<-?['"'"'"]?/, "", marker)
      sub(/['"'"'"]$/, "", marker)
      inhere = 1
    }
    print
  }
')

# Already redaction-shaped: counts, paths-only, or a substitution that drops the
# value. Checked first so the safe form is never blocked.
REDACTED='grep -c|grep -l|grep -L|grep -q|rg -c|rg -l|--count|--files-with-matches|wc -|cut -d|redact|=<|s/=|len=|\$\{#'

# Commands that emit file contents. `cut` and `wc` are deliberately absent —
# they are in the allowance above.
READERS='(^|[|;&(]|[[:space:]])(grep|egrep|fgrep|rg|cat|tac|sed|awk|head|tail|less|more|strings|od|xxd|nl)([[:space:]]|$)'

# Files that hold credentials in plaintext. The home-directory ones must be
# path-anchored — preceded by `~` or `/` — so prose naming them in backticks or
# quotes does not match. Anchored loosely on the stem so a `.bak` /
# `.bak.20260922` copy of any of them is caught too.
SECRETS='[~/]\.(bashrc|bash_profile|profile|zshrc|bash_history|zsh_history|netrc|pgpass|claude\.json|credentials\.json)|[~/]\.aws/credentials|/\.config/op/|config/claude-docker/env|(^|[[:space:]])\.env([^[:alnum:]_-]|$)'

if printf '%s' "$cmd" | grep -Eq "$REDACTED"; then
  exit 0
fi

if printf '%s' "$cmd" | grep -Eq "$READERS" \
   && printf '%s' "$cmd" | grep -Eq "$SECRETS"; then
  cat <<'JSON'
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Blocked: this would print the contents of a file that holds credentials in plaintext (a shell rc, a history file, an env file, .netrc, .pgpass, a Claude credentials file, an op/ or claude-docker env file, or a .bak of one). Finding WHERE something is configured must not echo its value. Use one of these instead: `grep -c NAME <file>` to confirm it is there; `grep -n NAME <file> | sed -E 's/=.*/=<redacted>/'` to see the line with the value stripped; `sed -n '10,20p' <file> | sed -E 's/=.*/=<redacted>/'` for context; `echo \"len=${#VAR}\"` to prove a variable is populated. If you genuinely need a value, ask the user to read it themselves."}}
JSON
  exit 0
fi

exit 0
