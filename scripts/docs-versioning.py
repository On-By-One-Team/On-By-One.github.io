#!/usr/bin/env python3
"""Update document change logs from Pull Request and review events."""

from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("CHANGELOG_ROOT", Path(__file__).resolve().parents[1]))
TEX_ROOT = ROOT / "docs" / "tex"
TEMPLATES_ROOT = TEX_ROOT / "templates"
PR_MARKER = "% change-log-pr:"
RECIPIENTS = {
    "client": r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin",
    "proposer": r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin \newline Vimar S.p.A.",
}
ACCOUNT_NAMES = {
    "37457532": "Daniele Nuzzaci",
    "263198226": "Federico Temporin",
    "344313264": "Alvise Greggio",
    "239207104": "Sara Ballardin",
    "263850856": "Simone Giuliano",
    "103838799": "Shuhui Chen",
    "237098663": "Tommaso Zorzetto",
}
VERSION = re.compile(r"^\d+\.\d+\.\d+$")
VERSION_KINDS = ("completed-milestone", "major", "minor")


@dataclass(frozen=True)
class ChangeRow:
    version: str
    date: str
    author: str
    description: str
    verifier: str


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
    }
    return "".join(replacements.get(character, character) for character in value)


def extract_description(body: str) -> str:
    """Extract LaTeX description from <!-- description -->...<!-- /description --> in a PR body."""
    match = re.search(
        r"<!--\s*description\s*-->(.*?)<!--\s*/description\s*-->",
        body,
        re.DOTALL,
    )
    if match is None:
        return "-"
    text = " ".join(match.group(1).split())
    return text if text else "-"


def description_escape(value: str) -> str:
    """Escape only unescaped & for a LaTeX description that is otherwise raw LaTeX."""
    return re.sub(r"(?<!\\)&", r"\\&", value)


def iso_date(value: str) -> str:
    if value == "-":
        return value
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"Data non interpretabile: {value}") from error
    return parsed.date().isoformat()


def split_cells(row: str) -> list[str]:
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for character in row:
        if character == "&" and not escaped:
            cells.append("".join(current).strip())
            current = []
        else:
            current.append(character)
        escaped = character == "\\" and not escaped
        if character != "\\":
            escaped = False
    value = "".join(current).strip()
    if value.endswith(r"\\"):
        value = value[:-2].rstrip()
    cells.append(value)
    return cells


def row_from_line(line: str) -> ChangeRow | None:
    if PR_MARKER in line:
        line = line.split(PR_MARKER, 1)[0]
    if "&" not in line or r"\\" not in line:
        return None
    cells = split_cells(line)
    if len(cells) != 5:
        return None
    return ChangeRow(*cells)


def registry_bounds(lines: list[str]) -> tuple[int, int]:
    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if r"\section*{Registro delle modifiche}" in line
        )
        end = next(
            index
            for index in range(start + 1, len(lines))
            if r"\end{tabularx}" in lines[index]
        )
    except StopIteration as error:
        raise ValueError("Registro delle modifiche non trovato") from error
    return start, end


def information_bounds(lines: list[str]) -> tuple[int, int, int]:
    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if r"\textbf{Informazioni documento}" in line
        )
        header = next(
            index
            for index in range(start, len(lines))
            if r"\textbf{Destinatari}" in lines[index]
        )
        table_end = next(
            index
            for index in range(header + 1, len(lines))
            if r"\end{tabularx}" in lines[index]
        )
        separator = next(
            index
            for index in range(header + 1, table_end)
            if r"\hline" in lines[index]
        )
        end = next(
            (
                index
                for index in range(separator + 1, table_end)
                if r"\hline" in lines[index]
            ),
            table_end,
        )
    except StopIteration as error:
        raise ValueError("Tabella Informazioni documento non trovata") from error
    return separator, end, start


def marker_line(lines: list[str], start: int, end: int, pr_number: int) -> int | None:
    marker = f"{PR_MARKER} {pr_number}"
    for index in range(start, end):
        if marker in lines[index]:
            return index
    return None


def row_line(row: ChangeRow, indentation: str, pr_number: int) -> str:
    return (
        f"{indentation}{latex_escape(row.version)} & "
        f"{latex_escape(row.date)} & {latex_escape(row.author)} & "
        f"{row.description} & {latex_escape(row.verifier)} "
        f"\\\\ {PR_MARKER} {pr_number}\n"
    )


def information_row_line(
    version: str, date: str, status: str, recipient_type: str, indentation: str
) -> str:
    try:
        recipients = RECIPIENTS[recipient_type]
    except KeyError as error:
        raise ValueError("La PR deve avere una sola label tra client e proposer") from error
    return (
        f"{indentation}{latex_escape(version)} & {latex_escape(date)} & "
        f"{latex_escape(status)} & {recipients} \\\\\n"
    )


def ensure_hline_after(lines: list[str], index: int, indentation: str) -> None:
    for next_index in range(index + 1, len(lines)):
        stripped = lines[next_index].strip()
        if not stripped:
            continue
        if stripped.startswith(r"\hline"):
            return
        break
    lines.insert(index + 1, f"{indentation}\\hline\n")


def update_information(
    path: Path, version: str, date: str, status: str, recipient_type: str
) -> bool:
    date = iso_date(date)
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    separator, end, _ = information_bounds(lines)
    indentation = re.match(r"\s*", lines[separator]).group(0)
    replacement = information_row_line(
        version, date, status, recipient_type, indentation
    )
    lines[separator + 1 : end] = [replacement]
    ensure_hline_after(lines, separator + 1, indentation)
    updated = "".join(lines)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def insert_row(lines: list[str], start: int, end: int, row: ChangeRow, pr_number: int) -> None:
    header = next(
        (
            index
            for index in range(start, end)
            if r"\textbf{Verificatore}" in lines[index]
        ),
        None,
    )
    if header is None:
        raise ValueError("Intestazione del registro non trovata")
    separator = next(
        (index for index in range(header + 1, end) if r"\hline" in lines[index]),
        None,
    )
    if separator is None:
        raise ValueError("Separatore dell'intestazione non trovato")
    indentation = re.match(r"\s*", lines[separator]).group(0)
    lines.insert(separator + 1, row_line(row, indentation, pr_number))
    ensure_hline_after(lines, separator + 1, indentation)


def update_pr_row(path: Path, row: ChangeRow, pr_number: int) -> bool:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    start, end = registry_bounds(lines)
    existing = marker_line(lines, start, end, pr_number)
    if existing is None:
        insert_row(lines, start, end, row, pr_number)
    else:
        indentation = re.match(r"\s*", lines[existing]).group(0)
        lines[existing] = row_line(row, indentation, pr_number)
        ensure_hline_after(lines, existing, indentation)
    updated = "".join(lines)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def changed_documents(base_sha: str, head_sha: str) -> list[Path]:
    import subprocess

    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}...{head_sha}", "--", "docs/tex"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    documents = []
    for relative in result.stdout.splitlines():
        path = ROOT / relative
        if (
            relative.endswith(".tex")
            and path.is_file()
            and not path.is_relative_to(TEMPLATES_ROOT)
        ):
            documents.append(path)
    return documents


def author_name(account_id: str) -> str:
    try:
        return ACCOUNT_NAMES[account_id]
    except KeyError as error:
        raise ValueError(f"Account GitHub non mappato: {account_id}") from error


def normalize_whitespace(value: str) -> str:
    return " ".join(value.split())


def current_recipient_type(content: str) -> str | None:
    """Detect the recipient type from the Informazioni documento table."""
    lines = content.splitlines(keepends=True)
    try:
        separator, end, _ = information_bounds(lines)
    except ValueError:
        return None
    table_content = normalize_whitespace("".join(lines[separator + 1 : end]))
    for key in sorted(RECIPIENTS, key=lambda k: len(RECIPIENTS[k]), reverse=True):
        if normalize_whitespace(RECIPIENTS[key]) in table_content:
            return key
    return None


def resolve_recipient_type(path: Path, explicit: str) -> str:
    """Return *explicit* when provided, otherwise detect from the document."""
    if explicit:
        if explicit not in RECIPIENTS:
            raise ValueError("La PR deve avere una sola label tra client e proposer")
        return explicit
    content = path.read_text(encoding="utf-8")
    detected = current_recipient_type(content)
    if detected is None:
        raise ValueError(
            f"Destinatari non rilevabili in {path.name}: "
            "usare la label client o proposer nella PR"
        )
    return detected


def current_document_version(content: str) -> str | None:
    info = content.split(r"\textbf{Informazioni documento}", 1)
    if len(info) != 2:
        return None
    info = info[1].split(r"\end{tabularx}", 1)[0]
    for line in info.splitlines():
        match = re.match(r"\s*(\d+\.\d+\.\d+|-)\s*&", line)
        if match:
            return match.group(1) if VERSION.fullmatch(match.group(1)) else None
    return None


def numeric_versions(path: Path, pr_number: int) -> list[tuple[int, int, int]]:
    content = path.read_text(encoding="utf-8")
    start, end = registry_bounds(content.splitlines(keepends=True))
    versions = []
    for line in content.splitlines()[start:end]:
        if f"{PR_MARKER} {pr_number}" in line:
            continue
        row = row_from_line(line)
        if row and VERSION.fullmatch(row.version):
            versions.append(tuple(map(int, row.version.split("."))))
    return versions


def next_version(path: Path, pr_number: int, kind: str | None) -> str:
    if kind not in VERSION_KINDS:
        raise ValueError(
            "La Pull Request deve avere esattamente una label tra "
            "completed-milestone, major e minor"
        )
    versions = numeric_versions(path, pr_number)
    if not versions:
        return "1.0.0"
    major, minor, patch = versions[0]
    if kind == "completed-milestone":
        return f"{major + 1}.0.0"
    if kind == "major":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def update_review_row(path: Path, pr_number: int, version: str, verifier: str) -> bool:
    original = path.read_text(encoding="utf-8")
    lines = original.splitlines(keepends=True)
    start, end = registry_bounds(lines)
    index = marker_line(lines, start, end, pr_number)
    if index is None:
        raise ValueError(f"Riga della PR #{pr_number} non trovata in {path}")
    row = row_from_line(lines[index])
    if row is None:
        raise ValueError(f"Riga della PR #{pr_number} non interpretabile in {path}")
    updated_row = ChangeRow(version, row.date, row.author, row.description, verifier)
    indentation = re.match(r"\s*", lines[index]).group(0)
    lines[index] = row_line(updated_row, indentation, pr_number)
    ensure_hline_after(lines, index, indentation)
    updated = "".join(lines)
    if updated == original:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def update_pr(args: argparse.Namespace) -> int:
    author = author_name(args.author_id)
    body = os.environ.get("PR_BODY", "")
    description = description_escape(extract_description(body))
    changed = False
    for path in changed_documents(args.base_sha, args.head_sha):
        try:
            registry_bounds(path.read_text(encoding="utf-8").splitlines(keepends=True))
        except ValueError:
            continue
        recipient_type = resolve_recipient_type(path, args.recipient_type)
        changed |= update_pr_row(
            path,
            ChangeRow("-", iso_date(args.date), author, description, "-"),
            args.pr_number,
        )
        changed |= update_information(
            path, "-", "-", "Bozza", recipient_type
        )
    return int(changed)


def update_review(args: argparse.Namespace) -> int:
    verifier = author_name(args.reviewer_id)
    paths = changed_documents(args.base_sha, args.head_sha)
    changed = False
    for path in paths:
        try:
            registry_bounds(path.read_text(encoding="utf-8").splitlines(keepends=True))
        except ValueError:
            continue
        recipient_type = resolve_recipient_type(path, args.recipient_type)
        version = next_version(path, args.pr_number, args.kind)
        changed |= update_review_row(path, args.pr_number, version, verifier)
        if args.state == "approved":
            changed |= update_information(
                path, version, iso_date(args.date), "Approvato", recipient_type
            )
        else:
            changed |= update_information(
                path, "-", "-", "Bozza", recipient_type
            )
    return int(changed)


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    pr = subparsers.add_parser("pr")
    pr.add_argument("--base-sha", required=True)
    pr.add_argument("--head-sha", required=True)
    pr.add_argument("--pr-number", type=int, required=True)
    pr.add_argument("--author-id", required=True)
    pr.add_argument("--date", required=True)
    pr.add_argument("--recipient-type", default="")
    pr.set_defaults(function=update_pr)
    review = subparsers.add_parser("review")
    review.add_argument("--base-sha", required=True)
    review.add_argument("--head-sha", required=True)
    review.add_argument("--pr-number", type=int, required=True)
    review.add_argument("--reviewer-id", required=True)
    review.add_argument("--state", choices=("approved", "changes_requested"), required=True)
    review.add_argument("--kind", choices=VERSION_KINDS)
    review.add_argument("--date", required=True)
    review.add_argument("--recipient-type", default="")
    review.set_defaults(function=update_review)
    return parser


if __name__ == "__main__":
    arguments = parser().parse_args()
    try:
        arguments.function(arguments)
    except (ValueError, FileNotFoundError) as error:
        print(f"::error::{error}", file=sys.stderr)
        raise SystemExit(1)
