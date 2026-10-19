"""Create a small real document for local/browser workflow verification."""
from pathlib import Path
import fitz


def main():
    target = Path(__file__).resolve().parents[1] / '.codex-test' / 'workflow-fixture.pdf'
    target.parent.mkdir(parents=True, exist_ok=True)
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_textbox(fitz.Rect(40, 40, 550, 800), '\n'.join([
        'Retrieval Study', 'Abstract',
        'We propose a lexical retrieval approach for research assistants. The method ranks document sentences by token overlap.',
        'Methodology', 'Our algorithm indexes paragraphs and retrieves relevant passages. The dataset contains 120 public papers.',
        'Results', 'The evaluation reports precision of 0.82 on the dataset. Retrieval improves evidence selection.',
        'Limitations', 'A limitation is the small evaluation dataset. Future work should evaluate multilingual papers.',
    ]), fontsize=11)
    pdf.save(target)
    pdf.close()
    print(target)


if __name__ == '__main__':
    main()
