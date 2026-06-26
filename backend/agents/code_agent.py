from typing import Any, Dict, Optional


class CodeGenerationAgent:
    name = "Code Generation Agent"

    def __init__(self, llm_service=None):
        self.llm = llm_service

    def run(self, query: str = "", document_text: str = "", filename: str = "", **_: Any) -> Dict[str, Any]:
        topic = (query or filename or "research model").strip()
        context = (document_text or "")[:90000]
        if self.llm and self.llm.is_available:
            code = self._llm_code(topic, context)
            mode = "gemini"
        else:
            code = self._fallback_code(topic)
            mode = "local_template"

        explanation = (
            "Generated a PyTorch scaffold with model, dataset, and training loop sections. "
            "Review layer dimensions and task-specific loss functions before running experiments."
        )
        return {
            "selected_agent": self.name,
            "intent": "ml_code_generation",
            "response": explanation,
            "sources": [],
            "artifacts": {"code": code, "filename": "generated_model.py", "mode": mode},
        }

    def _llm_code(self, topic: str, context: str) -> str:
        prompt = f"""You are a senior ML engineer.
Generate a syntactically valid PyTorch scaffold for this research request.
Include:
- imports
- Dataset class
- model class
- training loop
- validation hook
- comments mapping the code to the method.
Return only Python code, no markdown.

Request: {topic}
Research context:
{context}
"""
        text = self.llm.generate_text(prompt, fallback=self._fallback_code(topic))
        return self._strip_markdown(text)

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


def build_experiment(features, labels, input_dim, output_dim, batch_size=32):
    dataset = ResearchDataset(features, labels)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ResearchModel(input_dim=input_dim, hidden_dim=128, output_dim=output_dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)
    criterion = nn.CrossEntropyLoss()
    return model, loader, optimizer, criterion, device
'''
