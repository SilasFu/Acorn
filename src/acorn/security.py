from __future__ import annotations

import re
from pathlib import Path
from typing import Any

DANGEROUS_PATTERNS: list[tuple[str, str, str]] = [
    (r"RUN\s+(curl|wget)\s+\S+\s*\|\s*(bash|sh)", "high", "Shell pipe from curl/wget"),
    (r"RUN\s+curl\s+\S+\s+--output\s+/dev/null", "medium", "Potentially suspicious curl usage"),
    (r"ADD\s+https?://\S+", "medium", "ADD from remote URL"),
    (r"USER\s+root", "low", "Running as root"),
    (r"RUN\s+(chmod\s+777|chmod\s+-R\s+777)", "high", "Overly permissive file permissions"),
    (r"ENV\s+(PASSWORD|SECRET|TOKEN|API_KEY)\s*=", "high", "Hardcoded secret in ENV"),
    (r"RUN\s+apt-get\s+install\s+-y\s+.*?(telnet|netcat)", "medium", "Potentially unsafe packages"),
    (r"RUN\s+sudo\s+", "medium", "Unnecessary sudo usage"),
    (r"COPY\s+--from=\S+\s+/root/", "low", "Copying from /root in multi-stage"),
]

SENSITIVE_PATTERNS: list[str] = [
    r"(?i)(password|passwd|secret|token|api[_-]?key|private[_-]?key)\s*[:=]\s*['\"][^'\"]+['\"]",
    r"(?i)AKIA[0-9A-Z]{16}",
    r"(?i)(-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----)",
]


def scan_file_for_dangerous(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not path.is_file():
        return findings

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for pattern, severity, message in DANGEROUS_PATTERNS:
        for match in re.finditer(pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            findings.append({
                "file": str(path),
                "line": line_num,
                "severity": severity,
                "message": message,
                "match": match.group(0)[:80],
            })

    return findings


def scan_template(template_dir: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for f in template_dir.rglob("*"):
        if f.is_file() and f.suffix in ("", ".sh", ".py", ".yaml", ".yml", ".json"):
            findings.extend(scan_file_for_dangerous(f))
    return findings


def check_sensitive_info(path: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not path.is_file():
        return findings

    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for pattern in SENSITIVE_PATTERNS:
        for match in re.finditer(pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            findings.append({
                "file": str(path),
                "line": line_num,
                "severity": "high",
                "message": "Possible sensitive information leak",
                "match": match.group(0)[:60],
            })

    return findings


def format_findings(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return ""
    lines = ["\nSecurity Scan Results:"]
    for f in findings:
        sev = f["severity"]
        tag = {"high": "⚠ HIGH", "medium": "  MED", "low": "  LOW"}.get(sev, "  ???")
        lines.append(f"  [{tag}] {f['message']}")
        lines.append(f"         {f['file']}:{f['line']}")
    return "\n".join(lines)
