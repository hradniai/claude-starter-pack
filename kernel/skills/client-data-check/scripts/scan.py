#!/usr/bin/env python3
"""
client-data-check / scan.py

Offline PII and sensitive-data scan for files and directories.

Usage:
  python3 scan.py <path>

Outputs a markdown summary table to stdout. Matched values are never printed
in full — only redacted previews (first/last char preserved) and file:line
references.

Designed for the agency power-user cohort: Czech + EU context (rodné číslo,
IČO, DIČ, IBAN) plus universal patterns (emails, phones, cards, API keys).
"""
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

MAX_FILE_BYTES = 5 * 1024 * 1024  # Skip files larger than 5 MB.

TEXT_EXTENSIONS = {
    ".md", ".txt", ".csv", ".tsv", ".json", ".jsonl", ".yaml", ".yml",
    ".html", ".htm", ".xml", ".eml", ".log", ".ini", ".cfg", ".toml",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".rb", ".go", ".rs",
    ".java", ".kt", ".swift", ".php", ".sql", ".env.example",
}

SKIP_DIRS = {".git", "node_modules", "dist", "build", ".next", ".venv", "venv", "__pycache__", ".cache"}


@dataclass(frozen=True)
class Pattern:
    name: str
    regex: re.Pattern[str]
    label: str  # User-facing Czech label.


def luhn_check(num: str) -> bool:
    digits = [int(d) for d in num if d.isdigit()]
    if len(digits) < 13 or len(digits) > 19:
        return False
    checksum = 0
    parity = len(digits) % 2
    for i, d in enumerate(digits):
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        checksum += d
    return checksum % 10 == 0


PATTERNS: list[Pattern] = [
    Pattern(
        "email",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
        "e-mail",
    ),
    Pattern(
        "phone_cz",
        re.compile(r"(?:\+420[\s-]?)?\d{3}[\s-]?\d{3}[\s-]?\d{3}\b"),
        "telefon (CZ formát)",
    ),
    Pattern(
        "phone_intl",
        re.compile(r"\+\d{1,3}[\s-]?\d{2,4}[\s-]?\d{2,4}[\s-]?\d{2,4}\b"),
        "telefon (mezinárodní)",
    ),
    Pattern(
        "rodne_cislo",
        re.compile(r"\b\d{6}\s?/?\s?\d{3,4}\b"),
        "rodné číslo (pravděpodobné)",
    ),
    Pattern(
        "ico",
        re.compile(r"(?i)(?:IČO?|IČ\.|ICO|IC)\s*[:.]?\s*\d{8}\b"),
        "IČO",
    ),
    Pattern(
        "dic",
        re.compile(r"\bCZ\d{8,10}\b"),
        "DIČ (CZ)",
    ),
    Pattern(
        "iban",
        re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b"),
        "IBAN",
    ),
    Pattern(
        "aws_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "AWS access key",
    ),
    Pattern(
        "anthropic_key",
        re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}"),
        "Anthropic API klíč",
    ),
    Pattern(
        "openai_key",
        re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{20,}"),
        "OpenAI API klíč (pravděpodobný)",
    ),
    Pattern(
        "github_token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
        "GitHub token",
    ),
    Pattern(
        "jwt",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "JWT token",
    ),
    Pattern(
        "high_entropy_secret",
        re.compile(
            r"(?i)(?:secret|password|passwd|api[_-]?key|token|auth)\s*[:=]\s*['\"]?([A-Za-z0-9_\-+/=]{20,})",
        ),
        "secret/password/token přiřazení",
    ),
    Pattern(
        "credit_card_candidate",
        re.compile(r"\b(?:\d[ -]?){12,18}\d\b"),
        "možné číslo karty (Luhn check)",
    ),
    Pattern(
        "cz_postal",
        re.compile(r"\b\d{3}\s?\d{2}\b"),
        "PSČ (CZ)",
    ),
]


@dataclass
class Match:
    pattern_name: str
    label: str
    file_path: Path
    line_number: int
    preview: str


@dataclass
class ScanResult:
    matches: list[Match] = field(default_factory=list)
    files_scanned: int = 0
    files_skipped: int = 0


def redact(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return f"{value[0]}{'*' * (len(value) - 2)}{value[-1]}"


def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    # Best-effort check: read first 1024 bytes, look for null byte.
    try:
        with path.open("rb") as fh:
            chunk = fh.read(1024)
        if b"\x00" in chunk:
            return False
        chunk.decode("utf-8")
        return True
    except (OSError, UnicodeDecodeError):
        return False


def iter_files(root: Path) -> Iterable[Path]:
    if root.is_file():
        yield root
        return
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith(".")]
        for name in filenames:
            yield Path(dirpath) / name


def scan_file(path: Path, result: ScanResult) -> None:
    try:
        size = path.stat().st_size
    except OSError:
        result.files_skipped += 1
        return
    if size > MAX_FILE_BYTES:
        result.files_skipped += 1
        return
    if not is_text_file(path):
        result.files_skipped += 1
        return

    try:
        with path.open("r", encoding="utf-8", errors="replace") as fh:
            lines = fh.readlines()
    except OSError:
        result.files_skipped += 1
        return

    result.files_scanned += 1
    for lineno, line in enumerate(lines, start=1):
        for pat in PATTERNS:
            for match in pat.regex.finditer(line):
                raw = match.group(0)
                if pat.name == "credit_card_candidate" and not luhn_check(raw):
                    continue
                if pat.name == "cz_postal":
                    # PSČ alone is low signal — skip unless near address words.
                    surroundings = line.lower()
                    if not any(token in surroundings for token in ("praha", "brno", "ostrava", "ulice", "nám", "adresa", "psč")):
                        continue
                result.matches.append(
                    Match(
                        pattern_name=pat.name,
                        label=pat.label,
                        file_path=path,
                        line_number=lineno,
                        preview=redact(raw),
                    )
                )


def report(result: ScanResult, root: Path) -> str:
    out: list[str] = []
    out.append(f"# Client Data Check — scan report")
    out.append("")
    out.append(f"Path: `{root}`")
    out.append(f"Files scanned: {result.files_scanned}, skipped: {result.files_skipped}")
    out.append("")

    if not result.matches:
        out.append("No regex-matchable PII patterns found.")
        out.append("")
        out.append("Reminder: regex catches **form**, not meaning. Strategic content, client opinions, pricing, internal context — none of that is detected by this scan. You are still the judge.")
        return "\n".join(out)

    by_label: dict[str, list[Match]] = {}
    for m in result.matches:
        by_label.setdefault(m.label, []).append(m)

    out.append(f"Findings: {len(result.matches)} match(es) across {len(by_label)} categor(ies)")
    out.append("")
    out.append("| Category | Count | Files (with line numbers) |")
    out.append("|----------|-------|---------------------------|")
    for label, matches in sorted(by_label.items(), key=lambda kv: -len(kv[1])):
        by_file: dict[Path, list[int]] = {}
        for m in matches:
            by_file.setdefault(m.file_path, []).append(m.line_number)
        file_refs = "; ".join(
            f"`{path}`: " + ", ".join(str(n) for n in sorted(set(lines)))
            for path, lines in by_file.items()
        )
        out.append(f"| {label} | {len(matches)} | {file_refs} |")
    out.append("")
    out.append("Matched values are not printed. Open the file:line to inspect. Decide per category whether to anonymize before sharing.")
    return "\n".join(out)


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: scan.py <path>", file=sys.stderr)
        return 2
    root = Path(sys.argv[1]).expanduser().resolve()
    if not root.exists():
        print(f"Path does not exist: {root}", file=sys.stderr)
        return 2

    result = ScanResult()
    for path in iter_files(root):
        scan_file(path, result)

    print(report(result, root))
    return 0 if not result.matches else 1


if __name__ == "__main__":
    sys.exit(main())
