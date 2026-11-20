#!/usr/bin/env python3
"""Generate the document sections in website/index.html from configured PDF paths."""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import date
from fnmatch import fnmatchcase
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS_ROOT = ROOT / "docs"
PDF_ROOT = ROOT / "docs" / "pdf"
DIARY_ROOT = ROOT / "docs" / "diari-di-bordo" / "pdf"
TEX_ROOT = ROOT / "docs" / "tex"
INDEX = ROOT / "website" / "index.html"
CONFIG = ROOT / "scripts" / "site-sections.json"
START_MARKER = "        <!-- GENERATED DOCUMENTS START -->"
END_MARKER = "        <!-- GENERATED DOCUMENTS END -->"

VERSION_ROW = re.compile(
    r"^\s*([0-9]+\.[0-9]+\.[0-9]+)\s*&\s*[^&]+&", re.MULTILINE
)
DRAFT_VERSION_ROW = re.compile(r"^\s*-\s*&", re.MULTILINE)
DATE_IN_NAME = re.compile(r"(?<!\d)(\d{4}-\d{2}-\d{2})(?!\d)")
PDF_OBJECT = re.compile(rb"\d+\s+\d+\s+obj(.*?)endobj", re.DOTALL)
PDF_TITLE = re.compile(rb"/Title\s*\(([^)]*)\)")


@dataclass(frozen=True)
class Document:
    path: Path
    version: str | None

    @property
    def relative_path(self) -> str:
        return self.path.relative_to(ROOT).as_posix()

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def date(self) -> date | None:
        match = DATE_IN_NAME.search(self.name)
        return date.fromisoformat(match.group(1)) if match else None


def pdf_info_title(pdf_path: Path) -> str | None:
    for pdf_object in PDF_OBJECT.finditer(pdf_path.read_bytes()):
        body = pdf_object.group(1)
        if b"/Title" not in body or not (
            b"/Creator" in body or b"/Producer" in body
        ):
            continue
        match = PDF_TITLE.search(body)
        if match:
            return match.group(1).decode("latin-1").strip()
    return None


def version_for(pdf_path: Path) -> str | None:
    try:
        relative = pdf_path.relative_to(PDF_ROOT)
    except ValueError:
        return None
    tex_path = TEX_ROOT / relative.with_suffix(".tex")
    if not tex_path.exists():
        return None

    content = tex_path.read_text(encoding="utf-8")
    document_info = content.split(r"\textbf{Informazioni documento}", 1)
    if len(document_info) != 2:
        return None

    info_table = document_info[1].split(r"\end{tabularx}", 1)[0]
    if r"\textbf{Versione}" not in info_table:
        return None
    if DRAFT_VERSION_ROW.search(info_table):
        return None
    match = VERSION_ROW.search(info_table)
    if not match:
        raise ValueError(f"Versione corrente non interpretabile: {tex_path}")
    return match.group(1)


def documents() -> list[Document]:
    result = []
    for path in DOCS_ROOT.rglob("*.pdf"):
        document = Document(path, version_for(path))
        title = pdf_info_title(path)
        if title and title != path.stem:
            raise ValueError(f"Titolo PDF non coerente con il nome file: {path}")
        result.append(document)
    return result


def configuration() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def path_matches(document: Document, entry: dict) -> bool:
    configured_path = entry["path"]
    configured = ROOT / configured_path
    try:
        relative = document.path.relative_to(configured)
    except ValueError:
        return False
    return bool(relative.parts) and (
        entry.get("recursive", True) or len(relative.parts) == 1
    )


def date_matches_period(document: Document, section: dict) -> bool:
    if not document.date:
        return False
    date_start = section.get("date_start")
    date_end = section.get("date_end")
    if date_start and document.date < date.fromisoformat(date_start):
        return False
    if date_end and document.date > date.fromisoformat(date_end):
        return False
    return True


def configured_documents(
    items: list[Document],
    entry: dict,
    section: dict | None = None,
) -> list[Document]:
    matches = [
        item
        for item in items
        if path_matches(item, entry)
        and (
            not entry.get("filename_pattern")
            or fnmatchcase(item.name, entry["filename_pattern"])
        )
        and (
            not entry.get("filter_by_date")
            or (
                section is not None
                and date_matches_period(item, section)
            )
        )
    ]
    if not matches:
        return []
    return sort_documents(matches)


def sort_documents(items: list[Document]) -> list[Document]:
    return sorted(
        items,
        key=lambda item: (
            item.date is None,
            -(item.date.toordinal() if item.date else 0),
            item.name.casefold(),
            item.relative_path.casefold(),
        ),
    )


def link(document: Document, compact: bool = False) -> str:
    indent = "                            " if compact else "                        "
    version = (
        f'\n{indent}        <span class="doc-version">v{html.escape(document.version)}</span>'
        if document.version
        else ""
    )
    return (
        f'{indent}<li>\n'
        f'{indent}    <a href="../{html.escape(document.relative_path)}" '
        f'target="_blank" rel="noopener">\n'
        f'{indent}        <span class="doc-name">{html.escape(document.name)}</span>{version}\n'
        f'{indent}    </a>\n'
        f'{indent}</li>'
    )


def list_markup(items: list[Document], compact: bool = False) -> str:
    if not items:
        return '                        <p class="no-docs">- Ancora nulla -</p>'
    indent = "                        " if not compact else "                        "
    class_name = "doc-list compact" if compact else "doc-list"
    return (
        f'{indent}<ul class="{class_name}">\n'
        + "\n".join(link(item, compact) for item in sort_documents(items))
        + f'\n{indent}</ul>'
    )


def card(title: str | None, items: list[Document]) -> str:
    title_markup = (
        f'                    <h3>{html.escape(title)}</h3>\n'
        if title
        else ""
    )
    return (
        '                <div class="card">\n'
        f'{title_markup}'
        f'{list_markup(items)}\n'
        '                </div>'
    )


def accordion(title: str, items: list[Document]) -> str:
    return (
        '                    <details class="accordion">\n'
        f'                        <summary>{html.escape(title)}</summary>\n'
        f'{list_markup(items, compact=True)}\n'
        '                    </details>'
    )


def badge_for_status(status: str | None) -> dict | None:
    statuses = {
        "completed": {"class": "badge-success", "text": "Completata"},
        "in_progress": {"class": "badge-inprogress", "text": "In corso"},
        "not_started": {"class": "badge-notstarted", "text": "Non iniziata"},
    }
    return statuses.get(status) if status else None


def section(
    section_id: str,
    title: str,
    content: str,
    tag: str | None = None,
    badge: dict | None = None,
) -> str:
    tag_markup = ""
    if tag:
        tag_markup = f'\n                    <span class="milestone-tag">{html.escape(tag)}</span>'
    badge_markup = ""
    if badge:
        badge_markup = (
            f'\n                <span class="badge {html.escape(badge["class"])}">'
            f'{html.escape(badge["text"])}</span>'
        )
    return f"""        <section id="{section_id}" class="milestone-section" aria-labelledby="title-{section_id}">
            <div class="milestone-header">
                <div>{tag_markup}
                    <h2 id="title-{section_id}">{html.escape(title)}</h2>
                </div>{badge_markup}
            </div>

            <div class="milestone-grid">
{content}
            </div>
        </section>"""


def generated_sections(items: list[Document]) -> str:
    config = configuration()
    matched_paths = set()
    sections = []
    for section_config in sorted(config["sections"], key=lambda item: item["order"]):
        date_start = section_config.get("date_start")
        date_end = section_config.get("date_end")
        if date_start and date_end and date.fromisoformat(date_start) > date.fromisoformat(date_end):
            raise ValueError(
                f"Intervallo date non valido nella sezione {section_config['id']}"
            )

        cards = {}
        for entry in section_config["entries"]:
            documents_for_entry = configured_documents(items, entry, section_config)
            matched_paths.update(
                item.path
                for item in items
                if path_matches(item, entry)
            )
            card = cards.setdefault(entry["card"], {"title": entry["card_title"], "entries": []})
            card["entries"].append((entry, documents_for_entry))

        if not section_config.get("show_if_empty", True) and not any(
            documents_for_entry
            for card_config in cards.values()
            for _, documents_for_entry in card_config["entries"]
        ):
            continue

        card_markup = []
        for card_config in cards.values():
            contents = []
            for entry, documents_for_entry in card_config["entries"]:
                if entry.get("group"):
                    contents.append(accordion(entry["group"], documents_for_entry))
                else:
                    contents.append(list_markup(documents_for_entry))
            title_markup = (
                f'                    <h3>{html.escape(card_config["title"])}</h3>\n'
                if card_config["title"]
                else ""
            )
            card_markup.append(
                "                <div class=\"card\">\n"
                f'{title_markup}'
                + "\n".join(contents)
                + "\n                </div>"
            )

        sections.append(
            section(
                section_config["id"],
                section_config["title"],
                "\n\n".join(card_markup),
                section_config.get("tag"),
                badge_for_status(section_config.get("status"))
                or section_config.get("badge"),
            )
        )

    all_paths = {item.path for item in items}
    unconfigured = sorted(all_paths - matched_paths)
    if unconfigured:
        paths = ", ".join(str(path.relative_to(ROOT)) for path in unconfigured)
        raise ValueError(f"PDF senza associazione editoriale: {paths}")
    return "\n\n".join(sections)


def generate() -> None:
    source = INDEX.read_text(encoding="utf-8")
    start = source.index(START_MARKER)
    end = source.index(END_MARKER) + len(END_MARKER)
    replacement = START_MARKER + "\n" + generated_sections(documents()) + "\n" + END_MARKER
    INDEX.write_text(source[:start] + replacement + source[end:], encoding="utf-8")


if __name__ == "__main__":
    generate()
