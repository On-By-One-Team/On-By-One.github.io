import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "docs_versioning", Path(__file__).with_name("docs-versioning.py")
)
docs_versioning = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = docs_versioning
SPEC.loader.exec_module(docs_versioning)


TEX = r"""\textbf{Informazioni documento}
\textbf{Versione} & \textbf{Data} & \textbf{Stato} & \textbf{Destinatari} \\
\hline
1.2.3 & 2026-11-01 & Approvato & Team \\
\hline
\end{tabularx}
\section*{Registro delle modifiche}
\begin{tabularx}{\textwidth}{|c|c|c|X|c|}
\textbf{Verificatore} \\
\hline
1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\
\hline
\end{tabularx}
"""


class DocsVersioningTests(unittest.TestCase):
    def test_insert_is_idempotent_and_uses_placeholders(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            row = docs_versioning.ChangeRow(
                "-", "2026-11-17", "Federico Temporin", "Aggiornata la norma", "-"
            )
            self.assertTrue(docs_versioning.update_pr_row(path, row, 86))
            self.assertFalse(docs_versioning.update_pr_row(path, row, 86))
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("% change-log-pr: 86"), 1)
            self.assertIn("- & 2026-11-17 & Federico Temporin & Aggiornata la norma & -", content)

    def test_approved_version_increments_left_counter(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            row = docs_versioning.ChangeRow("-", "2026-11-17", "Federico Temporin", "PR", "-")
            docs_versioning.update_pr_row(path, row, 86)
            docs_versioning.update_information(path, "-", "-", "Bozza", "client")
            self.assertEqual(docs_versioning.approved_version(path, 86), "2.0.0")

    def test_failed_major_and_minor_versions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            row = docs_versioning.ChangeRow("-", "2026-11-17", "Federico Temporin", "PR", "-")
            docs_versioning.update_pr_row(path, row, 86)
            self.assertEqual(docs_versioning.failed_review_version(path, 86, "major"), "1.3.0")
            self.assertEqual(docs_versioning.failed_review_version(path, 86, "minor"), "1.2.4")

    def test_first_failed_review_uses_initial_major_or_minor_version(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            first_document = TEX.replace(
                "1.2.3 & 2026-11-01 & Approvato & Team \\\\",
                "- & - & Bozza & Team \\\\",
            ).replace(
                "1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\\\",
                "",
            )
            path.write_text(first_document, encoding="utf-8")
            row = docs_versioning.ChangeRow("-", "2026-11-17", "Federico Temporin", "PR", "-")
            docs_versioning.update_pr_row(path, row, 86)
            self.assertEqual(docs_versioning.failed_review_version(path, 86, "major"), "0.1.0")
            self.assertEqual(docs_versioning.failed_review_version(path, 86, "minor"), "0.0.1")

    def test_review_fills_version_and_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            row = docs_versioning.ChangeRow("-", "2026-11-17", "Federico Temporin", "PR", "-")
            docs_versioning.update_pr_row(path, row, 86)
            self.assertTrue(
                docs_versioning.update_review_row(
                    path, 86, "2.0.0", "Daniele Nuzzaci"
                )
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "2.0.0 & 2026-11-17 & Federico Temporin & PR & Daniele Nuzzaci",
                content,
            )

    def test_information_table_uses_draft_and_recipient_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_information(
                    path, "-", "-", "Bozza", "proposer"
                )
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                r"- & - & Bozza & On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin \newline Vimar S.p.A. \\",
                content,
            )

    def test_approval_updates_information_date_in_iso_format(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_information(
                    path, "2.0.0", "2026-11-17T16:13:45+01:00", "Approvato", "client"
                )
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn("2.0.0 & 2026-11-17 & Approvato &", content)

    def test_current_recipient_type_detects_client(self):
        tex_client = TEX.replace(
            "Team",
            r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin",
        )
        self.assertEqual(docs_versioning.current_recipient_type(tex_client), "client")

    def test_current_recipient_type_detects_proposer(self):
        tex_proposer = TEX.replace(
            "Team",
            r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin \newline Vimar S.p.A.",
        )
        self.assertEqual(docs_versioning.current_recipient_type(tex_proposer), "proposer")

    def test_current_recipient_type_returns_none_for_unknown(self):
        self.assertIsNone(docs_versioning.current_recipient_type(TEX))

    def test_resolve_uses_explicit_when_provided(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            self.assertEqual(
                docs_versioning.resolve_recipient_type(path, "client"), "client"
            )

    def test_resolve_detects_from_document_when_no_explicit(self):
        tex_proposer = TEX.replace(
            "Team",
            r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin \newline Vimar S.p.A.",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(tex_proposer, encoding="utf-8")
            self.assertEqual(
                docs_versioning.resolve_recipient_type(path, ""), "proposer"
            )

    def test_resolve_raises_when_undetectable_and_no_explicit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            with self.assertRaises(ValueError):
                docs_versioning.resolve_recipient_type(path, "")

    def test_changed_documents_ignores_templates_directory(self):
        from unittest.mock import patch, MagicMock

        mock_result = MagicMock()
        mock_result.stdout = (
            "docs/tex/templates/template-generico.tex\n"
            "docs/tex/templates/ve.tex\n"
            "docs/tex/gestionali/glossario.tex\n"
        )
        with patch("subprocess.run", return_value=mock_result):
            changed = docs_versioning.changed_documents("base", "head")
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0].name, "glossario.tex")



if __name__ == "__main__":
    unittest.main()
