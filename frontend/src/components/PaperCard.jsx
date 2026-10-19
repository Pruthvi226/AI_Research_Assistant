import React, { useState } from "react";
import { ArrowUpRight, Bookmark, Check, Copy, FileText } from "lucide-react";
import { citation, safeUrl } from "../research";

export default function PaperCard({
  paper,
  saved,
  onSave,
  selected,
  onSelect,
  note,
  onNote,
}) {
  const [style, setStyle] = useState("APA");
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(citation(paper, style));
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      setCopyError(true);
    }
  }
  return (
    <article className="paper-card">
      <div className="card-meta">
        <span className="source-dot" /> {paper.source} <span>·</span>{" "}
        {paper.year || "Year unavailable"}{" "}
        <span className="venue">{paper.venue}</span>
        {onSelect && (
          <label className="select-paper">
            <input
              type="checkbox"
              checked={selected}
              onChange={onSelect}
              aria-label={`Select ${paper.title} for review`}
            />{" "}
            Compare
          </label>
        )}
      </div>
      <h3>
        <a href={safeUrl(paper.url)} target="_blank" rel="noreferrer">
          {paper.title}
          <ArrowUpRight size={17} />
        </a>
      </h3>
      <p className="authors">
        {paper.authors?.slice(0, 4).join(", ") || "Authors unavailable"}
        {paper.authors?.length > 4 ? " et al." : ""}
      </p>
      {paper.abstract ? (
        <details>
          <summary>Read abstract</summary>
          <p className="abstract">{paper.abstract}</p>
        </details>
      ) : (
        <p className="metadata-note">
          Abstract not provided by the publisher. Open the paper for full text.
        </p>
      )}
      <div className="card-footer">
        <span className="citation-count">
          {paper.citations.toLocaleString()} citations
        </span>
        {safeUrl(paper.pdf) && (
          <a
            className="text-button"
            href={safeUrl(paper.pdf)}
            target="_blank"
            rel="noreferrer"
          >
            <FileText size={14} /> PDF
          </a>
        )}
        <div className="card-actions">
          <select
            aria-label={`Citation style for ${paper.title}`}
            value={style}
            onChange={(e) => setStyle(e.target.value)}
          >
            {["APA", "IEEE", "MLA", "BibTeX"].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
          <button
            className="icon-button"
            onClick={copy}
            aria-label="Copy citation"
            title="Copy citation"
          >
            {copied ? <Check size={16} /> : <Copy size={16} />}
          </button>
          <button
            className={`icon-button ${saved ? "is-saved" : ""}`}
            onClick={() => onSave(paper)}
            aria-label={saved ? "Remove bookmark" : "Bookmark paper"}
            title={saved ? "Remove bookmark" : "Save paper"}
          >
            <Bookmark size={17} fill={saved ? "currentColor" : "none"} />
          </button>
        </div>
      </div>
      {copyError && (
        <textarea
          aria-label="Citation to copy manually"
          readOnly
          value={citation(paper, style)}
        />
      )}
      {onNote && (
        <textarea
          className="paper-note"
          aria-label={`Notes for ${paper.title}`}
          placeholder="Your research notes…"
          value={note || ""}
          onChange={(e) => onNote(e.target.value)}
          maxLength={10000}
        />
      )}
    </article>
  );
}
