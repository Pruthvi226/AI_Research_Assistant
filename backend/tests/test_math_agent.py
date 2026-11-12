import unittest

from agents.math_agent import MathEquationAgent


class MathEquationAgentTest(unittest.TestCase):
    def test_local_explanation_uses_explicit_context_definition_and_page(self):
        result = MathEquationAgent().run(
            query="z = alpha * x",
            context="The paper states alpha denotes the regularization weight.",
            page=8,
            filename="methods.pdf",
        )
        self.assertIn("alpha: the regularization weight", result["artifacts"]["explanation"])
        self.assertEqual(8, result["artifacts"]["source"]["page"])
        self.assertIn("methods.pdf", result["response"])
        self.assertIn(r"\alpha", result["artifacts"]["latex"])
        self.assertIn("unverified", result["response"])

    def test_local_explanation_does_not_invent_missing_definitions_or_derivations(self):
        result = MathEquationAgent().run(
            query="x = y + z",
            context="The method uses the following equation.",
            page=3,
        )
        self.assertIn("remain unknown", result["artifacts"]["explanation"])
        self.assertIn("no derivation is inferred", result["artifacts"]["explanation"])


if __name__ == "__main__":
    unittest.main()
