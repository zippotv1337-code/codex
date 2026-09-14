from __future__ import annotations

import argparse
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


TEXT_SUFFIXES = {
    ".bat", ".cmd", ".css", ".env", ".example", ".html", ".ini", ".js",
    ".json", ".md", ".ps1", ".py", ".sh", ".toml", ".txt", ".yaml", ".yml",
}

FIXED_PATTERNS = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:gh[psou]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{50,})\b")),
    ("aws-access-key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\.[A-Za-z0-9_-]{12,}\b")),
    ("url-basic-auth", re.compile(r"https?://[^\s/:]+:[^\s/@]{8,}@", re.IGNORECASE)),
)

QUOTED_ASSIGNMENT = re.compile(
    r"(?i)\b(password|passwd|pwd|access[_-]?token|api[_-]?key|client[_-]?secret)"
    r"\s*[:=]\s*(['\"])([^'\"\r\n]{8,})\2"
)
ENV_ASSIGNMENT = re.compile(
    r"^\s*([A-Z][A-Z0-9_]*(?:PASSWORD|PASSWD|TOKEN|SECRET|API_KEY|PRIVATE_KEY)[A-Z0-9_]*)"
    r"\s*=\s*([^\s#]{8,})\s*$"
)


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    kind: str


def _placeholder(value: str, key: str = "") -> bool:
    normalized = value.strip().strip("'\"").lower()
    if not normalized:
        return True
    if key.endswith(("_ALIAS", "_NAMESPACE", "_PROVIDER")):
        return True
    return (
        normalized.startswith(("secret://", "${", "$env:", "%", "<", "your-", "your_"))
        or normalized in {"none", "null", "false", "true", "disabled", "changeme", "replace-me"}
        or "example" in normalized
        or "placeholder" in normalized
        or normalized.startswith("test-only-")
    )


def scan_text(text: str, path: str = "<memory>") -> list[Finding]:
    findings: list[Finding] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for kind, pattern in FIXED_PATTERNS:
            if pattern.search(line):
                findings.append(Finding(path, number, kind))
        for match in QUOTED_ASSIGNMENT.finditer(line):
            if not _placeholder(match.group(3), match.group(1).upper()):
                findings.append(Finding(path, number, "literal-secret-assignment"))
        env_match = ENV_ASSIGNMENT.match(line)
        if env_match and not _placeholder(env_match.group(2), env_match.group(1)):
            findings.append(Finding(path, number, "literal-secret-environment"))
    return findings


def scan_file(path: Path, *, display_path: str | None = None) -> list[Finding]:
    if path.suffix.lower() not in TEXT_SUFFIXES and path.name not in {".env", ".env.example"}:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return scan_text(text, display_path or str(path))


def tracked_files(project_root: Path) -> list[Path]:
    project_root = project_root.resolve()
    repo_root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    ).resolve()
    relative = project_root.relative_to(repo_root).as_posix()
    result = subprocess.run(
        ["git", "ls-files", "--", relative],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=True,
    )
    return [repo_root / line for line in result.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Fail closed when tracked project files contain likely secrets")
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--tracked", action="store_true")
    args = parser.parse_args(argv)
    paths = tracked_files(args.root) if args.tracked else [path.resolve() for path in args.paths]
    if not paths:
        parser.error("provide files or --tracked")
    findings = [finding for path in paths for finding in scan_file(path)]
    if findings:
        print("SECRET LEAK CHECK: BLOCKED")
        for finding in findings:
            print(f"{finding.path}:{finding.line}: {finding.kind}")
        return 1
    print(f"SECRET LEAK CHECK: OK ({len(paths)} files checked)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
