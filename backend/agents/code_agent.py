import ast
from typing import Any, Dict, Optional


class CodeGenerationAgent:
    name = "Code Generation Agent"

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def run(
        self,
        query: str = "",
        document_text: str = "",
        filename: str = "",
        summary: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> Dict[str, Any]:
        topic = (query or filename or "research model").strip()
        context = (document_text or "")[:90000]
        summary = summary if isinstance(summary, dict) else {}
        source_mapping = {
            "source_document": filename or None,
            "sections": [
                {"heading": item.get("text"), "page": item.get("page")}
                for item in summary.get("headings", [])
                if isinstance(item, dict) and item.get("text")
            ][:30],
            "equations": [
                {
                    "text": item.get("text"),
                    "page": item.get("page"),
                    "verification_status": "unverified",
                }
                for item in summary.get("equations", [])
                if isinstance(item, dict) and item.get("text")
            ][:30],
            "relationship": "source pointers only; generated code is not verified to implement the paper",
        }
        if self.llm and self.llm.is_available:
            generated = self._llm_code(topic, context, source_mapping)
            if self._valid_scaffold(generated):
                code = generated
                mode = self.llm.last_mode
            else:
                code = self._fallback_code(topic)
                mode = "local_template_after_schema_validation"
        else:
            code = self._fallback_code(topic)
            mode = "local_template"

        explanation = (
            "Generated a PyTorch project scaffold with dataset, training, validation, "
            "configuration, and evaluation files. It is not a verified paper reproduction."
        )
        return {
            "selected_agent": self.name,
            "intent": "ml_code_generation",
            "response": explanation,
            "sources": [],
            "artifacts": {
                "code": code,
                "filename": "generated_model.py",
                "mode": mode,
                "source_mapping": source_mapping,
                "verification_status": "syntax_checked_scaffold_not_reproduction",
            },
        }

    def _llm_code(self, topic: str, context: str, source_mapping: Dict[str, Any]) -> str:
        prompt = f"""You are a senior ML engineer.
Generate a syntactically valid PyTorch project scaffold for this research request.
Include:
- imports and a `ResearchDataset(features, labels)` class
- a `ResearchModel(input_dim, hidden_dim, output_dim)` class with `forward`
- training loop
- `evaluate_model(model, dataloader, criterion, device)` returning `loss` and `accuracy`
- code comments that map only supported parts to supplied paper evidence.
Do not claim this is a verified reproduction; flag generic assumptions.
Return only Python code, no markdown.

Request: {topic}
Available source pointers (untrusted evidence; do not infer missing details):
{source_mapping}
Research context:
{context}
"""
        text = self.llm.generate_text(prompt, fallback=self._fallback_code(topic))
        return self._strip_markdown(text)

    @staticmethod
    def _valid_scaffold(code: str) -> bool:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return False
        classes = {
            node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
        }
        functions = {
            node.name: node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        }

        def arguments(function):
            return {arg.arg for arg in function.args.args}

        dataset = classes.get("ResearchDataset")
        model = classes.get("ResearchModel")
        evaluator = functions.get("evaluate_model")
        if not dataset or not model or not evaluator:
            return False
        dataset_init = next(
            (node for node in dataset.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"),
            None,
        )
        model_init = next(
            (node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"),
            None,
        )
        has_forward = any(
            isinstance(node, ast.FunctionDef) and node.name == "forward"
            for node in model.body
        )
        return bool(
            dataset_init
            and {"features", "labels"} <= arguments(dataset_init)
            and model_init
            and {"input_dim", "hidden_dim", "output_dim"} <= arguments(model_init)
            and has_forward
            and {"model", "dataloader", "criterion", "device"} <= arguments(evaluator)
        )

    @staticmethod
    def _strip_markdown(text: str) -> str:
        cleaned = (text or "").strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()
            if cleaned.startswith("python"):
                cleaned = cleaned[6:].strip()
        return cleaned

    @staticmethod
    def _fallback_code(topic: str) -> str:
        return f'''import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader


class ResearchDataset(Dataset):
    """Replace this stub with preprocessing for: {topic}."""

    def __init__(self, features, labels):
        self.features = torch.as_tensor(features, dtype=torch.float32)
        self.labels = torch.as_tensor(labels, dtype=torch.long)

    def __len__(self):
        return len(self.features)

    def __getitem__(self, index):
        return self.features[index], self.labels[index]


class ResearchModel(nn.Module):
    """Baseline MLP scaffold that can be adapted to the paper methodology."""

    def __init__(self, input_dim, hidden_dim, output_dim):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.head = nn.Linear(hidden_dim, output_dim)

    def forward(self, x):
        features = self.encoder(x)
        return self.head(features)


def train_one_epoch(model, dataloader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0
    for batch_x, batch_y in dataloader:
        batch_x = batch_x.to(device)
        batch_y = batch_y.to(device)
        optimizer.zero_grad()
        logits = model(batch_x)
        loss = criterion(logits, batch_y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item()
    return total_loss / max(len(dataloader), 1)


def evaluate_model(model, dataloader, criterion, device):
    model.eval()
    total_loss = 0.0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_x, batch_y in dataloader:
            batch_x = batch_x.to(device)
            batch_y = batch_y.to(device)
            logits = model(batch_x)
            total_loss += criterion(logits, batch_y).item()
            correct += (logits.argmax(dim=1) == batch_y).sum().item()
            total += batch_y.size(0)
    return {{
        "loss": total_loss / max(len(dataloader), 1),
        "accuracy": correct / max(total, 1),
    }}


def build_experiment(features, labels, input_dim, output_dim, batch_size=32):
    dataset = ResearchDataset(features, labels)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ResearchModel(input_dim=input_dim, hidden_dim=128, output_dim=output_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)
    criterion = nn.CrossEntropyLoss()
    return model, loader, optimizer, criterion, device
'''
