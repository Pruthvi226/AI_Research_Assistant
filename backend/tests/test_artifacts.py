import json
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

from agents.code_agent import CodeGenerationAgent
from utils.artifacts import write_scaffold_bundle


class ScaffoldBundleTest(unittest.TestCase):
    def test_bundle_contains_syntax_checked_scaffold_and_no_reproduction_claim(self):
        test_root = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as folder:
            path = write_scaffold_bundle(
                Path(folder),
                "model-bundle.zip",
                CodeGenerationAgent._fallback_code("test request"),
                source_title="paper.pdf",
            )
            with ZipFile(path) as archive:
                self.assertEqual(
                    {
                        "README.md",
                        "model.py",
                        "train.py",
                        "evaluate.py",
                        "config.json",
                        "source_map.json",
                        "requirements.txt",
                        "manifest.json",
                    },
                    set(archive.namelist()),
                )
                manifest = json.loads(archive.read("manifest.json"))
                self.assertFalse(manifest["reproduction_verified"])
                self.assertEqual("syntax_checked_only", manifest["verification_status"])
                self.assertIn("paper.pdf", archive.read("README.md").decode())
                self.assertIn("evaluate_model", archive.read("model.py").decode())
                self.assertIn("validation_loss", archive.read("train.py").decode())
                for name in ("model.py", "train.py", "evaluate.py"):
                    compile(archive.read(name), name, "exec")

    def test_invalid_generated_python_is_not_bundled(self):
        test_root = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as folder:
            with self.assertRaises(SyntaxError):
                write_scaffold_bundle(Path(folder), "bad.zip", "def broken(\n")
            self.assertEqual([], list(Path(folder).iterdir()))

    def test_scaffold_contract_rejects_syntax_valid_but_incomplete_code(self):
        test_root = Path(__file__).resolve().parents[2] / ".codex-test" / "backend-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as folder:
            with self.assertRaisesRegex(ValueError, "ResearchDataset"):
                write_scaffold_bundle(Path(folder), "incomplete.zip", "def train():\n    pass\n")
            self.assertEqual([], list(Path(folder).iterdir()))


if __name__ == "__main__":
    unittest.main()
