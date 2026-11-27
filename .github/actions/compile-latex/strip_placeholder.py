#!/usr/bin/env python3
"""Temporarily strip empty changelog placeholder rows before PDF compilation."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

PLACEHOLDER_DESCRIPTION = "Descrizione mancante"


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


def is_placeholder_line(line: str) -> bool:
    if "&" not in line or r"\\" not in line:
        return False
    cells = split_cells(line)
    if len(cells) != 5:
        return False
    return cells == ["-", "-", "-", PLACEHOLDER_DESCRIPTION, "-"]


def strip_placeholder_rows(content: str) -> str:
    lines = content.splitlines(keepends=True)
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
    except StopIteration:
        return content

    result: list[str] = []
    skip_next_hline = False
    for index, line in enumerate(lines):
        if start < index < end and is_placeholder_line(line):
            skip_next_hline = True
            continue
        if skip_next_hline:
            if not line.strip():
                continue
            if line.strip().startswith(r"\hline"):
                skip_next_hline = False
                continue
            skip_next_hline = False
        result.append(line)
    return "".join(result)


def main(file_list_path: str, backup_dir_path: str) -> int:
    file_list = Path(file_list_path)
    backup_dir = Path(backup_dir_path)
    backed_up: list[str] = []
    for raw_line in file_list.read_text(encoding="utf-8").splitlines():
        rel_path = raw_line.strip()
        if not rel_path or rel_path.startswith("docs/tex/templates/"):
            continue
        tex_path = Path(rel_path)
        if not tex_path.is_file():
            continue
        original = tex_path.read_text(encoding="utf-8")
        if "documentclass" not in original:
            continue
        stripped = strip_placeholder_rows(original)
        if stripped != original:
            backup_path = backup_dir / rel_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tex_path, backup_path)
            tex_path.write_text(stripped, encoding="utf-8")
            backed_up.append(rel_path)
    (backup_dir / "files.txt").write_text(
        "\n".join(backed_up) + ("\n" if backed_up else ""),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1], sys.argv[2]))
