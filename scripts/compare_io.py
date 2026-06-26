"""
Compare representative Scientia.ai API inputs and outputs.

Run after the Docker stack is up:
    python scripts/compare_io.py

Set SCIENTIA_BASE_URL to target another host, for example:
    $env:SCIENTIA_BASE_URL="http://localhost:5000"
"""

import json
import os
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


BASE_URL = os.environ.get("SCIENTIA_BASE_URL", "http://localhost:5000").rstrip("/")


PAPERS = {
    "retrieval-benchmark.pdf": """
Title
Fast Retrieval Benchmarking for Research Assistants

Abstract
This paper evaluates a retrieval augmented assistant that indexes research papers with lexical search.
The method uses cached PDF text, reusable chunks, and lightweight ranking to reduce latency.

Introduction
Research assistants must accept noisy academic PDF inputs and return grounded answers quickly.
This paper contributes a benchmark for comparing input documents, output summaries, and question answering latency.

Method
We propose cached extraction, chunk reuse, and extractive summaries for offline operation.
The dataset contains synthetic machine learning abstracts with methodology, experiments, and limitations.

Results
The optimized pipeline reduces repeated document selection and question answering time by avoiding redundant PDF parsing.
Accuracy is measured by whether answers cite dataset, method, result, limitation, and future work sentences.

Limitations
The benchmark is synthetic and does not replace full human evaluation.
Future work should add larger PDFs and live cloud model comparisons.

References
[1] Example Retrieval Evaluation Paper.
""",
    "robotics-safety.pdf": """
Title
Robotics Safety Control with Adaptive Planning

Abstract
This paper studies safe robot motion planning under uncertain indoor navigation conditions.
The proposed model combines adaptive control, risk scoring, and human feedback to improve safety.

Introduction
Robotics systems need fast decisions while avoiding unsafe trajectories.
This study compares control policies across obstacle density, response latency, and path efficiency.

Method
We propose an adaptive planning model with a risk-aware controller and a feedback module.
The dataset includes simulated warehouse routes and annotated safety interventions.

Results
The model improves collision avoidance and maintains efficient paths in dense scenes.
Performance is reported using success rate, collision count, and planning latency.

Limitations
The study is limited to simulation and does not validate performance on physical robots.
Future research should evaluate deployment on real robots and include more diverse environments.

References
[1] Example Robotics Safety Paper.
""",
}


def main() -> None:
    rows = []
    health = request_json("GET", "/health")
    rows.append(("GET /health", "", health["status"], summarize(health["data"])))

    missing_question = request_json("POST", "/ask", {"question": ""})
    rows.append(("POST /ask", "missing question", missing_question["status"], summarize(missing_question["data"])))

    bad_upload = upload_bytes("bad-input.txt", b"not a pdf", "text/plain")
    rows.append(("POST /upload", "txt file", bad_upload["status"], summarize(bad_upload["data"])))

    uploaded = []
    with tempfile.TemporaryDirectory(dir=temp_parent()) as temp_dir:
        for filename, text in PAPERS.items():
            pdf_path = Path(temp_dir) / filename
            write_pdf(pdf_path, text)
            result = upload_bytes(filename, pdf_path.read_bytes(), "application/pdf")
            uploaded.append(result["data"])
            rows.append((
                "POST /upload",
                filename,
                result["status"],
                summarize_upload(result["data"]),
            ))

    for data, question in zip(
        uploaded,
        ["What dataset is evaluated?", "What are the limitations?"],
    ):
        session_id = data.get("session_id", "")
        answer = request_json("POST", "/ask", {"question": question, "session_id": session_id})
        rows.append((
            "POST /ask",
            question,
            answer["status"],
            summarize_answer(answer["data"]),
        ))

    session_ids = [item.get("session_id") for item in uploaded if item.get("session_id")]
    if len(session_ids) >= 2:
        synthesis = request_json("POST", "/synthesis", {"session_ids": session_ids})
        rows.append(("POST /synthesis", "two uploaded papers", synthesis["status"], summarize(synthesis["data"])))

    print_table(rows)


def request_json(method: str, path: str, payload=None) -> dict:
    body = None
    headers = {}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    return request(method, path, body=body, headers=headers)


def upload_bytes(filename: str, content: bytes, content_type: str) -> dict:
    boundary = f"----ScientiaBoundary{int(time.time() * 1000)}"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + content + f"\r\n--{boundary}--\r\n".encode("utf-8")
    return request(
        "POST",
        "/upload",
        body=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        timeout=300,
    )


def request(method: str, path: str, body=None, headers=None, timeout: int = 120) -> dict:
    started = time.perf_counter()
    req = urllib.request.Request(f"{BASE_URL}{path}", data=body, method=method, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        status = exc.code
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"raw": raw[:200]}
    return {"status": status, "elapsed_ms": elapsed_ms, "data": data}


def write_pdf(path: Path, text: str) -> None:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    commands = ["BT", "/F1 11 Tf", "72 760 Td", "14 TL"]
    for line in lines[:48]:
        commands.append(f"({escape_pdf_text(line[:96])}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")

    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]

    content = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(content))
        content.extend(f"{index} 0 obj\n".encode("ascii"))
        content.extend(obj)
        content.extend(b"\nendobj\n")
    xref_start = len(content)
    content.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    content.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        content.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    content.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_start}\n%%EOF\n".encode("ascii")
    )
    path.write_bytes(content)


def temp_parent() -> str | None:
    configured = os.environ.get("SCIENTIA_TMP_DIR")
    if configured:
        Path(configured).mkdir(parents=True, exist_ok=True)
        return configured
    if os.name == "nt":
        fallback = Path("C:/tmp")
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback)
    return None


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def summarize(data: dict) -> str:
    if "error" in data:
        return data["error"][:120]
    return json.dumps(data, ensure_ascii=True)[:160]


def summarize_upload(data: dict) -> str:
    perf = data.get("performance", {})
    abstract = data.get("summary", {}).get("abstract", "")
    return f"session={data.get('session_id', '')} mode={perf.get('mode')} chunks={perf.get('chunks')} abstract={abstract[:90]}"


def summarize_answer(data: dict) -> str:
    perf = data.get("performance", {})
    answer = data.get("answer", "")
    return f"mode={perf.get('mode')} chunks={perf.get('retrieved_chunks')} answer={answer[:120]}"


def print_table(rows: list) -> None:
    headers = ("Input", "Variant", "HTTP", "Output")
    widths = [16, 28, 6, 120]
    print(" | ".join(header.ljust(widths[idx]) for idx, header in enumerate(headers)))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(" | ".join(str(value).replace("\n", " ")[:widths[idx]].ljust(widths[idx]) for idx, value in enumerate(row)))


if __name__ == "__main__":
    main()
