import ast
import io
import json
import mimetypes
from pathlib import Path
from typing import Dict
from zipfile import ZIP_DEFLATED, ZipFile

import fitz

from config import GENERATED_CODE_FOLDER, GENERATED_MARKDOWN_FOLDER


GENERATED_MARKDOWN_FOLDER.mkdir(parents=True, exist_ok=True)
GENERATED_CODE_FOLDER.mkdir(parents=True, exist_ok=True)


def write_text_artifact(folder: Path, filename: str, content: str) -> str:
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    path = folder / safe_name
    path.write_text(content or "", encoding="utf-8")
    return str(path)


def write_scaffold_bundle(
    folder: Path,
    filename: str,
    code: str,
    source_title: str = "",
    source_mapping: Dict | None = None,
) -> str:
    tree = ast.parse(code or "")
    classes = {node.name: node for node in tree.body if isinstance(node, ast.ClassDef)}
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
    dataset_init = next(
        (node for node in dataset.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"),
        None,
    ) if dataset else None
    model_init = next(
        (node for node in model.body if isinstance(node, ast.FunctionDef) and node.name == "__init__"),
        None,
    ) if model else None
    has_forward = bool(model) and any(
        isinstance(node, ast.FunctionDef) and node.name == "forward"
        for node in model.body
    )
    if not (
        dataset_init
        and {"features", "labels"} <= arguments(dataset_init)
        and model_init
        and {"input_dim", "hidden_dim", "output_dim"} <= arguments(model_init)
        and has_forward
        and evaluator
        and {"model", "dataloader", "criterion", "device"} <= arguments(evaluator)
    ):
        raise ValueError(
            "Scaffold must define ResearchDataset and implement the documented model, forward, and evaluation interfaces."
        )
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    if not safe_name.lower().endswith(".zip"):
        safe_name = f"{safe_name}.zip"

    requirements = "numpy>=1.26,<3\ntorch>=2.2,<3\n"
    train_script = '''"""Train a generated scaffold from an NPZ with `features` and `labels` arrays."""
import argparse
import random

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

from model import ResearchDataset, ResearchModel, evaluate_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="NPZ archive with features and labels")
    parser.add_argument("--checkpoint", default="checkpoint.pt")
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    data = np.load(args.data, allow_pickle=False)
    features = torch.as_tensor(data["features"], dtype=torch.float32)
    features = features.reshape(len(features), -1)
    labels = torch.as_tensor(data["labels"], dtype=torch.long)
    if len(features) != len(labels) or len(features) < 2:
        raise ValueError("features and labels must have equal length >= 2")
    dataset = ResearchDataset(features, labels)
    split = max(1, int(len(dataset) * 0.8))
    generator = torch.Generator().manual_seed(args.seed)
    order = torch.randperm(len(dataset), generator=generator).tolist()
    train = Subset(dataset, order[:split])
    validation = Subset(dataset, order[split:] or order[:split])
    train_loader = DataLoader(train, batch_size=args.batch_size, shuffle=True)
    validation_loader = DataLoader(validation, batch_size=args.batch_size)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ResearchModel(
        input_dim=int(features[0].numel()),
        hidden_dim=128,
        output_dim=int(labels.max().item()) + 1,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=3e-4, weight_decay=1e-2)
    criterion = nn.CrossEntropyLoss()
    for epoch in range(args.epochs):
        model.train()
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            optimizer.zero_grad()
            loss = criterion(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()
        metrics = evaluate_model(model, validation_loader, criterion, device)
        print(
            f"epoch={epoch + 1} validation_loss={metrics['loss']:.4f} "
            f"accuracy={metrics['accuracy']:.4f}"
        )
    torch.save({"state_dict": model.state_dict(), "seed": args.seed}, args.checkpoint)


if __name__ == "__main__":
    main()
'''
    evaluation_script = '''"""Evaluate an NPZ feature/label archive against a trained checkpoint."""
import argparse

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from model import ResearchDataset, ResearchModel, evaluate_model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", required=True, help="NPZ archive with features and labels")
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()
    data = np.load(args.data, allow_pickle=False)
    features = torch.as_tensor(data["features"], dtype=torch.float32)
    features = features.reshape(len(features), -1)
    labels = torch.as_tensor(data["labels"], dtype=torch.long)
    dataset = ResearchDataset(features, labels)
    loader = DataLoader(dataset, batch_size=args.batch_size)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ResearchModel(
        input_dim=int(features[0].numel()),
        hidden_dim=128,
        output_dim=int(labels.max().item()) + 1,
    ).to(device)
    checkpoint = torch.load(args.checkpoint, map_location=device, weights_only=True)
    model.load_state_dict(checkpoint["state_dict"])
    metrics = evaluate_model(model, loader, nn.CrossEntropyLoss(), device)
    print(metrics)


if __name__ == "__main__":
    main()
'''
    config = {
        "seed": 42,
        "epochs": 10,
        "batch_size": 32,
        "optimizer": "AdamW",
        "learning_rate": 0.0003,
        "weight_decay": 0.01,
        "loss": "CrossEntropyLoss",
        "input_archive": "NPZ with features and labels arrays",
    }
    source_mapping = source_mapping or {
        "source_document": source_title or None,
        "sections": [],
        "equations": [],
        "relationship": "no source pointers supplied; scaffold is generic and unverified",
    }
    manifest = {
        "artifact_type": "generated_scaffold",
        "verification_status": "syntax_checked_only",
        "reproduction_verified": False,
        "source_document": source_title or None,
        "files": [
            "README.md",
            "model.py",
            "train.py",
            "evaluate.py",
            "config.json",
            "source_map.json",
            "requirements.txt",
            "manifest.json",
        ],
    }
    readme = f"""# Generated research scaffold

Source document: {source_title or "Not attached"}

This bundle contains generated starter code, not a verified reproduction of a
paper. It has only been checked for Python syntax; inspect model dimensions and
the task-specific loss, validate dataset assumptions, pin tested dependency
versions, and run experiments independently. No generated code is executed
during bundle creation.

`source_map.json` lists extracted section/equation pointers when available.
Those pointers do not prove that the scaffold implements the paper's method.

The example runner expects an NPZ file with numeric `features` and integer
`labels` arrays. That format is a starter data contract, not a representation
of the paper's dataset or preprocessing.

```shell
python -m pip install -r requirements.txt
python train.py --data your_data.npz --epochs 10
python evaluate.py --data validation.npz --checkpoint checkpoint.pt
```
"""

    buffer = io.BytesIO()
    with ZipFile(buffer, "w", ZIP_DEFLATED) as archive:
        archive.writestr("README.md", readme)
        archive.writestr("model.py", code or "")
        archive.writestr("train.py", train_script)
        archive.writestr("evaluate.py", evaluation_script)
        archive.writestr("config.json", json.dumps(config, indent=2))
        archive.writestr("source_map.json", json.dumps(source_mapping, indent=2))
        archive.writestr("requirements.txt", requirements)
        archive.writestr("manifest.json", json.dumps(manifest, indent=2))
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_name
    path.write_bytes(buffer.getvalue())
    return str(path)


def write_briefing_pdf(folder: Path, filename: str, title: str, content: str) -> str:
    """Render a text-first briefing PDF using the existing PyMuPDF dependency."""
    safe_name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in filename)
    if not safe_name.lower().endswith(".pdf"):
        safe_name = f"{safe_name}.pdf"
    pdf = fitz.open()
    page = pdf.new_page()
    page_number = 1
    page_width = page.rect.width
    max_width = page_width - 96
    y = 52

    def add_page():
        nonlocal page, page_number, y
        page = pdf.new_page()
        page_number += 1
        y = 52

    def write_line(text: str, size: float, bold: bool = False):
        nonlocal y
        text = (text or "").encode("latin-1", "replace").decode("latin-1")
        font = "hebo" if bold else "helv"
        words = text.split()
        lines = []
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if current and fitz.get_text_length(
                candidate, fontname=font, fontsize=size
            ) > max_width:
                lines.append(current)
                current = word
            else:
                current = candidate
        if current or not lines:
            lines.append(current)
        for line in lines:
            line_height = size * 1.55
            if y + line_height > page.rect.height - 48:
                add_page()
            page.insert_text(
                (48, y),
                line,
                fontname=font,
                fontsize=size,
                color=(0.12, 0.16, 0.15),
            )
            y += line_height

    write_line(title, 18, bold=True)
    write_line("Generated research briefing · evidence and metadata may be incomplete", 9)
    y += 12
    for line in (content or "").splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            heading = stripped.lstrip("# ").strip()
            if heading:
                y += 6
                write_line(heading, 13 if stripped.startswith("## ") else 11, bold=True)
        elif stripped:
            write_line(stripped, 9)
        else:
            y += 5
    for index in range(1, page_number + 1):
        current_page = pdf[index - 1]
        current_page.insert_text(
            (page_width - 75, current_page.rect.height - 24),
            f"{index} / {page_number}",
            fontname="helv",
            fontsize=8,
            color=(0.35, 0.39, 0.38),
        )
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / safe_name
    path.write_bytes(pdf.tobytes())
    pdf.close()
    return str(path)


def artifact_response_headers(path: str) -> Dict[str, str]:
    mime, _ = mimetypes.guess_type(path)
    return {"mimetype": mime or "application/octet-stream"}
