import tempfile
import unittest
from pathlib import Path

import importlib.util
import sys

SPEC = importlib.util.spec_from_file_location(
    "generate_site", Path(__file__).with_name("generate-site.py")
)
generate_site = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = generate_site
SPEC.loader.exec_module(generate_site)


class GenerateSiteTests(unittest.TestCase):
    def test_milestone_status_generates_correct_badge(self):
        self.assertEqual(
            generate_site.badge_for_status("completed"),
            {"class": "badge-success", "text": "Completata"},
        )
        self.assertEqual(
            generate_site.badge_for_status("in_progress"),
            {"class": "badge-inprogress", "text": "In corso"},
        )
        self.assertIsNone(generate_site.badge_for_status(None))

    def test_card_omits_heading_when_title_is_null(self):
        markup = generate_site.card(None, [])
        self.assertNotIn("<h3>", markup)

    def test_card_renders_heading_when_title_is_present(self):
        markup = generate_site.card("Documenti gestionali", [])
        self.assertIn(
            "<h3>Documenti gestionali</h3>",
            markup,
        )

    def test_documents_are_filtered_by_milestone_period(self):
        root = generate_site.PDF_ROOT / "verbali" / "interni"
        items = [
            generate_site.Document(root / "2026-10-27-vi.pdf", None),
            generate_site.Document(root / "2026-11-05-vi.pdf", None),
        ]
        entry = {
            "path": "docs/pdf/verbali/interni",
            "filter_by_date": True,
        }

        candidatura = generate_site.configured_documents(
            items,
            entry,
            {"date_end": "2026-11-03"},
        )
        rtb = generate_site.configured_documents(
            items,
            entry,
            {"date_start": "2026-11-04"},
        )

        self.assertEqual([item.name for item in candidatura], ["2026-10-27-vi.pdf"])
        self.assertEqual([item.name for item in rtb], ["2026-11-05-vi.pdf"])

    def test_section_omits_milestone_tag_when_tag_is_null(self):
        markup = generate_site.section("test", "Test", "", tag=None)
        self.assertNotIn("milestone-tag", markup)

    def test_section_renders_milestone_tag_when_tag_is_present(self):
        markup = generate_site.section("test", "Test", "", tag="Milestone 01")
        self.assertIn(
            '<span class="milestone-tag">Milestone 01</span>',
            markup,
        )

    def test_dates_are_descending_and_undated_files_are_last(self):
        root = generate_site.PDF_ROOT / "verbali" / "interni"
        items = [
            generate_site.Document(root / "2026-10-20-vi.pdf", None),
            generate_site.Document(root / "2026-11-10-vi.pdf", None),
            generate_site.Document(root / "verbale.pdf", None),
        ]
        self.assertEqual(
            [item.name for item in generate_site.sort_documents(items)],
            ["2026-11-10-vi.pdf", "2026-10-20-vi.pdf", "verbale.pdf"],
        )

    def test_version_is_read_from_document_information_in_fixture(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "document.tex"
            path.write_text(
                r"""\textbf{Informazioni documento}
\textbf{Versione}
\hline
1.2.3 & 2026/11/15 & Approvato & Destinatari \\
\end{tabularx}
\section*{Registro delle modifiche}
\hline
0.9.0 & 2026/11/01 & Autore & Descrizione & Verificatore \\
\hline
""",
                encoding="utf-8",
            )
            old_tex_root = generate_site.TEX_ROOT
            generate_site.TEX_ROOT = root
            try:
                pdf_path = generate_site.PDF_ROOT / "document.pdf"
                self.assertEqual(generate_site.version_for(pdf_path), "1.2.3")
            finally:
                generate_site.TEX_ROOT = old_tex_root

    def test_version_is_resolved_for_signed_pdf_from_unsigned_tex(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tex_dir = root / "verbali" / "esterni"
            tex_dir.mkdir(parents=True)
            path = tex_dir / "2026-11-12-ve.tex"
            path.write_text(
                r"""\textbf{Informazioni documento}
\textbf{Versione}
\hline
1.0.0 & 2026/11/12 & Approvato & Destinatari \\
\end{tabularx}
""",
                encoding="utf-8",
            )
            old_tex_root = generate_site.TEX_ROOT
            generate_site.TEX_ROOT = root
            try:
                pdf_path = (
                    generate_site.PDF_ROOT
                    / "verbali"
                    / "esterni"
                    / "2026-11-12-ve-firmato.pdf"
                )
                self.assertEqual(generate_site.version_for(pdf_path), "1.0.0")
            finally:
                generate_site.TEX_ROOT = old_tex_root

    def test_repository_signed_external_minutes_have_versions(self):
        signed = [
            item
            for item in generate_site.documents()
            if item.name.endswith("-ve-firmato.pdf")
        ]
        self.assertTrue(signed)
        for item in signed:
            self.assertIsNotNone(item.version, f"Versione mancante per {item.name}")

    def test_repository_documents_are_published_according_to_configuration(self):
        items = generate_site.documents()
        content = generate_site.generated_sections(items)
        published_paths = set()
        configured_paths = set()

        for section_config in generate_site.configuration()["sections"]:
            for entry in section_config["entries"]:
                configured_paths.update(
                    item.path
                    for item in items
                    if generate_site.path_matches(item, entry)
                )
                configured = generate_site.configured_documents(
                    items,
                    entry,
                    section_config,
                )
                published_paths.update(item.path for item in configured)
                for item in configured:
                    self.assertIn(f"../{item.relative_path}", content)
                    self.assertIn(item.name, content)

        self.assertTrue(published_paths.issubset(configured_paths))
        for item in items:
            if item.path in configured_paths - published_paths:
                self.assertNotIn(f"../{item.relative_path}", content)

    def test_repository_pdf_titles_match_filenames(self):
        for pdf_path in generate_site.DOCS_ROOT.rglob("*.pdf"):
            title = generate_site.pdf_info_title(pdf_path)
            self.assertTrue(not title or title == pdf_path.stem)

    def test_draft_document_information_has_no_version(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / "document.tex"
            path.write_text(
                r"""\textbf{Informazioni documento}
\textbf{Versione}
\hline
- & - & Bozza & Destinatari \\
\end{tabularx}
""",
                encoding="utf-8",
            )
            old_tex_root = generate_site.TEX_ROOT
            generate_site.TEX_ROOT = root
            try:
                pdf_path = generate_site.PDF_ROOT / "document.pdf"
                self.assertIsNone(generate_site.version_for(pdf_path))
            finally:
                generate_site.TEX_ROOT = old_tex_root

    def test_documents_scan_new_pdf_directories_without_code_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            docs_root = Path(directory)
            future_directory = docs_root / "pdf" / "futura-milestone"
            future_directory.mkdir(parents=True)
            future_pdf = future_directory / "documento.pdf"
            future_pdf.write_bytes(b"%PDF-1.4\n")

            old_docs_root = generate_site.DOCS_ROOT
            generate_site.DOCS_ROOT = docs_root
            try:
                self.assertEqual(
                    [item.path for item in generate_site.documents()],
                    [future_pdf],
                )
            finally:
                generate_site.DOCS_ROOT = old_docs_root

    def test_unconfigured_document_is_rejected(self):
        document = generate_site.Document(
            generate_site.ROOT
            / "docs"
            / "pdf"
            / "futura-milestone"
            / "document.pdf",
            None,
        )
        with self.assertRaisesRegex(ValueError, "PDF senza associazione editoriale"):
            generate_site.generated_sections(generate_site.documents() + [document])

    def test_filename_pattern_is_generic_and_excludes_unmatched_documents(self):
        root = generate_site.PDF_ROOT / "verbali" / "esterni"
        items = [
            generate_site.Document(root / "2026-10-22-ve-firmato.pdf", None),
            generate_site.Document(root / "2026-10-22-ve.pdf", None),
        ]
        entry = {
            "path": "docs/pdf/verbali/esterni",
            "filename_pattern": "*-firmato.pdf",
        }
        self.assertEqual(
            [item.name for item in generate_site.configured_documents(items, entry)],
            ["2026-10-22-ve-firmato.pdf"],
        )

    def test_filename_patterns_exclude_unmatched_repository_documents(self):
        items = generate_site.documents()
        content = generate_site.generated_sections(items)
        configured_paths = set()

        for section_config in generate_site.configuration()["sections"]:
            for entry in section_config["entries"]:
                configured = generate_site.configured_documents(
                    items,
                    entry,
                    section_config,
                )
                configured_paths.update(item.path for item in configured)
                for item in configured:
                    self.assertIn(f"../{item.relative_path}", content)

        for item in items:
            if item.path not in configured_paths:
                self.assertNotIn(item.name, content)


if __name__ == "__main__":
    unittest.main()
