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

    def test_version_is_read_from_document_information(self):
        tex_path = (
            generate_site.TEX_ROOT
            / "verbali"
            / "interni"
            / "2026-11-05-vi.tex"
        )
        pdf_path = generate_site.PDF_ROOT / tex_path.relative_to(
            generate_site.TEX_ROOT
        ).with_suffix(".pdf")
        self.assertEqual(generate_site.version_for(pdf_path), "1.0.1")

    def test_candidatura_keeps_completion_badge(self):
        content = generate_site.generated_sections(generate_site.documents())
        self.assertIn('class="badge badge-success">Completata</span>', content)

    def test_diary_links_use_repository_paths_and_names(self):
        content = generate_site.generated_sections(generate_site.documents())
        self.assertIn(
            "../docs/diari-di-bordo/pdf/2026-11-02-ddb.pdf", content
        )
        self.assertNotIn("2026-11-01-ddb.pdf", content)

    def test_diary_pdf_title_matches_filename_date(self):
        pdf_path = generate_site.DIARY_ROOT / "2026-11-02-ddb.pdf"
        self.assertEqual(generate_site.pdf_info_title(pdf_path), pdf_path.stem)

    def test_existing_norme_di_progetto_documentazione_has_a_version(self):
        pdf_path = (
            generate_site.PDF_ROOT
            / "gestionali"
            / "norme-di-progetto"
            / "norme-di-progetto-documentazione.pdf"
        )
        self.assertEqual(generate_site.version_for(pdf_path), "1.0.0")

    def test_editorial_configuration_uses_sentence_case_labels(self):
        labels = [
            entry.get("group", entry["card_title"])
            for section in generate_site.configuration()["sections"]
            for entry in section["entries"]
        ]
        self.assertIn("Documenti gestionali", labels)
        self.assertIn("Verbali interni", labels)
        self.assertNotIn("Verbali Interni", labels)

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

    def test_external_minutes_publish_only_signed_files(self):
        content = generate_site.generated_sections(generate_site.documents())
        self.assertIn("2026-10-22-ve-firmato.pdf", content)
        self.assertIn("2026-10-28-ve-firmato.pdf", content)
        self.assertNotIn("2026-10-22-ve.pdf", content)
        self.assertNotIn("2026-10-28-ve.pdf", content)


if __name__ == "__main__":
    unittest.main()
