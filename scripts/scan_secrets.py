"""Scan tracked history and current files; print only file/revision and rule, never secret values."""
import re
import subprocess
from pathlib import Path

PATTERNS = {
    "private-key": re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "openai-key": re.compile(rb"sk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{40,}"),
    "github-key": re.compile(rb"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})"),
    "aws-key": re.compile(rb"(?:AKIA|ASIA)[A-Z0-9]{16}"),
    "assigned-secret": re.compile(rb"(?im)^(?:INTERNAL_API_TOKEN|SESSION_SIGNING_SECRET|OPENAI_API_KEY|TURSO_AUTH_TOKEN)=[A-Za-z0-9_./-]{24,}$"),
}

def git(*args: str) -> bytes:
    return subprocess.check_output(["git", *args])


def main() -> None:
    failures = []
    seen = set()
    entries = git("rev-list", "--objects", "--all").decode().splitlines()
    for entry in entries:
        key, _, name = entry.partition(" ")
        if not name or key in seen:
            continue
        seen.add(key)
        if git("cat-file", "-t", key).strip() != b"blob":
            continue
        data = git("cat-file", "blob", key)
        for rule, pattern in PATTERNS.items():
            if pattern.search(data):
                failures.append(f"{name} ({key[:12]}): {rule}")
    for name in git("ls-files", "-z").decode().split("\0"):
        if name and Path(name).is_file():
            for rule, pattern in PATTERNS.items():
                if pattern.search(Path(name).read_bytes()):
                    failures.append(f"{name} (working tree): {rule}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Secret patterns: clean across {len(seen)} historical objects and tracked working files.")

if __name__ == "__main__":
    main()
