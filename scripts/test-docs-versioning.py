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

STRIP_SPEC = importlib.util.spec_from_file_location(
    "strip_placeholder",
    Path(__file__).resolve().parents[1]
    / ".github"
    / "actions"
    / "compile-latex"
    / "strip_placeholder.py",
)
strip_placeholder = importlib.util.module_from_spec(STRIP_SPEC)
sys.modules[STRIP_SPEC.name] = strip_placeholder
STRIP_SPEC.loader.exec_module(strip_placeholder)


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
- & - & - & Aggiornata la norma & - \\
\hline
1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\
\hline
\end{tabularx}
"""


def tex_with_description(description: str) -> str:
    return TEX.replace("Aggiornata la norma", description)


class DocsVersioningTests(unittest.TestCase):
    def test_pr_fills_author_date_and_inserts_placeholder_idempotently(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            )
            self.assertFalse(
                docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            )
            content = path.read_text(encoding="utf-8")
            self.assertEqual(content.count("% change-log-pr: 86"), 1)
            self.assertEqual(content.count("Descrizione mancante"), 1)
            self.assertIn(
                "- & - & - & Descrizione mancante & - \\\\\n\\hline\n"
                "- & 2026-11-17 & Federico Temporin & Aggiornata la norma & - \\\\ % change-log-pr: 86\n\\hline\n",
                content,
            )

    def test_synchronize_preserves_edited_description_without_duplicating_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            content = path.read_text(encoding="utf-8").replace(
                "Aggiornata la norma", "Descrizione aggiornata in secondo commit"
            )
            path.write_text(content, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_pr_row(path, "2026-11-18", "Federico Temporin", 86)
            )
            updated = path.read_text(encoding="utf-8")
            self.assertEqual(updated.count("Descrizione mancante"), 1)
            self.assertIn(
                "- & 2026-11-18 & Federico Temporin & Descrizione aggiornata in secondo commit & - \\\\ % change-log-pr: 86\n\\hline\n",
                updated,
            )

    def test_pr_raises_when_description_missing_or_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            for bad_desc in ("Descrizione mancante", "-", ""):
                path.write_text(tex_with_description(bad_desc), encoding="utf-8")
                with self.assertRaises(ValueError):
                    docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)

            no_draft = TEX.replace("- & - & - & Aggiornata la norma & - \\\\\n\\hline\n", "")
            path.write_text(no_draft, encoding="utf-8")
            with self.assertRaises(ValueError):
                docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)

    def test_update_pr_and_review_add_missing_hline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            missing_hline = TEX.replace(
                "- & - & - & Aggiornata la norma & - \\\\\n\\hline\n"
                "1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\\\",
                "- & 2026-11-17 & Federico Temporin & PR & - \\\\ % change-log-pr: 86\n"
                "1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\\\",
            )
            path.write_text(missing_hline, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            )
            self.assertFalse(
                docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "- & 2026-11-17 & Federico Temporin & PR & - \\\\ % change-log-pr: 86\n\\hline\n1.2.3 &",
                content,
            )

            path.write_text(missing_hline, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_review_row(path, 86, "2.0.0", "Daniele Nuzzaci")
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "2.0.0 & 2026-11-17 & Federico Temporin & PR & Daniele Nuzzaci \\\\ % change-log-pr: 86\n\\hline\n1.2.3 &",
                content,
            )

    def test_update_information_adds_missing_hline(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            missing_hline = TEX.replace(
                "1.2.3 & 2026-11-01 & Approvato & Team \\\\\n\\hline\n\\end{tabularx}",
                "1.2.3 & 2026-11-01 & Approvato & Team \\\\\n\\end{tabularx}",
            )
            path.write_text(missing_hline, encoding="utf-8")
            self.assertTrue(
                docs_versioning.update_information(path, "-", "-", "Bozza", "client")
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "- & - & Bozza & On-By-One \\newline Prof. Tullio Vardanega \\newline Prof. Riccardo Cardin \\\\\n\\hline\n\\end{tabularx}",
                content,
            )

    def test_next_version_increments_by_label_and_state(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            docs_versioning.update_information(path, "-", "-", "Bozza", "client")
            self.assertEqual(
                docs_versioning.next_version(path, 86, "major", "approved"), "2.0.0"
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "minor", "approved"), "1.3.0"
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "patch", "approved"), "1.2.4"
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "major", "changes_requested"),
                "1.3.0",
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "minor", "changes_requested"),
                "1.2.4",
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "patch", "changes_requested"),
                "1.2.4",
            )

    def test_draft_versions_start_at_0_1_0_and_approve_to_1_0_0(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            first_document = TEX.replace(
                "1.2.3 & 2026-11-01 & Approvato & Team \\\\",
                "- & - & Bozza & Team \\\\",
            ).replace(
                "1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\\\\n\\hline\n",
                "",
            )
            path.write_text(first_document, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            for kind in ("major", "minor", "patch"):
                self.assertEqual(
                    docs_versioning.next_version(path, 86, kind, "changes_requested"),
                    "0.1.0",
                )
                self.assertEqual(
                    docs_versioning.next_version(path, 86, kind, "approved"),
                    "1.0.0",
                )

            draft_document = TEX.replace(
                "1.2.3 & 2026-11-01 & Approvato & Team \\\\",
                "- & - & Bozza & Team \\\\",
            ).replace(
                "1.2.3 & 2026-11-01 & Sara Ballardin & Vecchia modifica & Daniele Nuzzaci \\\\",
                "0.1.4 & 2026-11-22 & Sara Ballardin & Bozza precedente & Daniele Nuzzaci \\\\",
            )
            path.write_text(draft_document, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            self.assertEqual(
                docs_versioning.next_version(path, 86, "patch", "changes_requested"),
                "0.1.5",
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "minor", "changes_requested"),
                "0.1.5",
            )
            self.assertEqual(
                docs_versioning.next_version(path, 86, "major", "changes_requested"),
                "0.2.0",
            )
            for kind in ("major", "minor", "patch"):
                self.assertEqual(
                    docs_versioning.next_version(path, 86, kind, "approved"),
                    "1.0.0",
                )

    def test_next_version_requires_valid_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            for invalid_kind in (None, "", "other"):
                with self.assertRaises(ValueError):
                    docs_versioning.next_version(path, 86, invalid_kind)

    def test_update_review_uses_label_on_approved_and_changes_requested(self):
        import argparse
        from unittest.mock import patch

        tex_client = TEX.replace(
            "Team",
            r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin",
        )
        for state, kind, expected_ver, expected_status in (
            ("approved", "patch", "1.2.4", "Approvato"),
            ("approved", "minor", "1.3.0", "Approvato"),
            ("approved", "major", "2.0.0", "Approvato"),
            ("changes_requested", "major", "1.3.0", "Bozza"),
            ("changes_requested", "minor", "1.2.4", "Bozza"),
            ("changes_requested", "patch", "1.2.4", "Bozza"),
        ):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "document.tex"
                path.write_text(tex_client, encoding="utf-8")
                docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
                args = argparse.Namespace(
                    base_sha="base",
                    head_sha="head",
                    pr_number=86,
                    reviewer_id="37457532",
                    state=state,
                    kind=kind,
                    date="2026-11-25T12:00:00Z",
                    recipient_type="",
                )
                with patch.object(docs_versioning, "changed_documents", return_value=[path]):
                    self.assertEqual(docs_versioning.update_review(args), 1)
                content = path.read_text(encoding="utf-8")
                self.assertIn(f"{expected_ver} & 2026-11-17 & Federico Temporin & Aggiornata la norma & Daniele Nuzzaci", content)
                if expected_status == "Approvato":
                    self.assertIn(f"{expected_ver} & 2026-11-25 & Approvato &", content)
                else:
                    self.assertIn("- & - & Bozza &", content)

    def test_update_review_raises_without_kind_when_doc_changed(self):
        import argparse
        from unittest.mock import patch

        tex_client = TEX.replace(
            "Team",
            r"On-By-One \newline Prof. Tullio Vardanega \newline Prof. Riccardo Cardin",
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(tex_client, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            args = argparse.Namespace(
                base_sha="base",
                head_sha="head",
                pr_number=86,
                reviewer_id="37457532",
                state="approved",
                kind=None,
                date="2026-11-25T12:00:00Z",
                recipient_type="",
            )
            with patch.object(docs_versioning, "changed_documents", return_value=[path]):
                with self.assertRaises(ValueError):
                    docs_versioning.update_review(args)

        args_no_docs = argparse.Namespace(
            base_sha="base",
            head_sha="head",
            pr_number=86,
            reviewer_id="37457532",
            state="approved",
            kind=None,
            date="2026-11-25T12:00:00Z",
            recipient_type="",
        )
        with patch.object(docs_versioning, "changed_documents", return_value=[]):
            self.assertEqual(docs_versioning.update_review(args_no_docs), 0)

    def test_versioned_documents_filters_non_changelog_tex(self):
        from unittest.mock import patch

        with tempfile.TemporaryDirectory() as directory:
            with_registry = Path(directory) / "doc.tex"
            with_registry.write_text(TEX, encoding="utf-8")
            without_registry = Path(directory) / "plain.tex"
            without_registry.write_text("\\section{Solo testo}\n", encoding="utf-8")

            with patch.object(
                docs_versioning, "changed_documents", return_value=[without_registry]
            ):
                self.assertEqual(docs_versioning.versioned_documents("b", "h"), [])

            with patch.object(
                docs_versioning,
                "changed_documents",
                return_value=[without_registry, with_registry],
            ):
                self.assertEqual(
                    docs_versioning.versioned_documents("b", "h"), [with_registry]
                )

    def test_review_fills_version_and_verifier(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-17", "Federico Temporin", 86)
            self.assertTrue(
                docs_versioning.update_review_row(
                    path, 86, "2.0.0", "Daniele Nuzzaci"
                )
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn(
                "2.0.0 & 2026-11-17 & Federico Temporin & Aggiornata la norma & Daniele Nuzzaci",
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

    def test_current_recipient_type_detects_multiline_recipients(self):
        multiline_proposer = TEX.replace(
            "Team \\\\",
            "\nOn-By-One \\newline \nProf. Tullio Vardanega \\newline \nProf. Riccardo Cardin \\newline \nVimar S.p.A. \\\\",
        )
        self.assertEqual(
            docs_versioning.current_recipient_type(multiline_proposer), "proposer"
        )
        multiline_client = TEX.replace(
            "Team \\\\",
            "\nOn-By-One \\newline \nProf. Tullio Vardanega \\newline \nProf. Riccardo Cardin \\\\",
        )
        self.assertEqual(
            docs_versioning.current_recipient_type(multiline_client), "client"
        )

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



    def test_latex_description_in_tex_survives_pr_update(self):
        """LaTeX commands written by the author in the .tex row must be preserved verbatim."""
        latex_desc = r"Aggiunti \ucrefplain{struttura} \& \ucrefplain{elenco-ambienti}"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(tex_with_description(latex_desc), encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-22", "Shuhui Chen", 109)
            content = path.read_text(encoding="utf-8")
            self.assertIn(latex_desc, content)
            self.assertNotIn("textbackslash", content)
            self.assertIn("- & - & - & Descrizione mancante & - \\\\", content)

    def test_strip_placeholder_removes_empty_row_for_compilation_only(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "document.tex"
            path.write_text(TEX, encoding="utf-8")
            docs_versioning.update_pr_row(path, "2026-11-26", "Shuhui Chen", 109)
            with_placeholder = path.read_text(encoding="utf-8")
            self.assertIn("Descrizione mancante", with_placeholder)

            stripped = strip_placeholder.strip_placeholder_rows(with_placeholder)
            self.assertNotIn("Descrizione mancante", stripped)
            self.assertIn("Aggiornata la norma", stripped)
            self.assertIn("Vecchia modifica", stripped)
            self.assertNotIn("\\hline\n\\hline", stripped)

    def test_strip_placeholder_main_backs_up_and_preserves_files(self):
        import os

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tex_dir = root / "docs" / "tex"
            tex_dir.mkdir(parents=True)
            tex_file = tex_dir / "doc.tex"
            content = "\\documentclass{article}\n" + tex_with_description("Descrizione mancante")
            tex_file.write_text(content, encoding="utf-8")
            file_list = root / "changed.txt"
            file_list.write_text("docs/tex/doc.tex\n", encoding="utf-8")
            backup_dir = root / "backup"
            backup_dir.mkdir()

            old_cwd = Path.cwd()
            try:
                os.chdir(root)
                strip_placeholder.main(str(file_list), str(backup_dir))
            finally:
                os.chdir(old_cwd)

            self.assertNotIn("Descrizione mancante", tex_file.read_text(encoding="utf-8"))
            self.assertEqual((backup_dir / "docs" / "tex" / "doc.tex").read_text(encoding="utf-8"), content)
            self.assertEqual((backup_dir / "files.txt").read_text(encoding="utf-8"), "docs/tex/doc.tex\n")


if __name__ == "__main__":
    unittest.main()
