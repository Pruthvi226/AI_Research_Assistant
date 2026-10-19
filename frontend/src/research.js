export function safeUrl(value) {
  try {
    const url = new URL(value);
    return ["https:", "http:"].includes(url.protocol) ? url.href : "";
  } catch {
    return "";
  }
}
export function plainText(value = "") {
  return String(value)
    .replace(/<[^>]*>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}
export function normalizeWork(work) {
  work = work && typeof work === "object" ? work : {};
  const year =
    (work.published?.["date-parts"] || work.issued?.["date-parts"])?.[0]?.[0] ||
    null;
  const authors = (Array.isArray(work.author) ? work.author : [])
    .filter((a) => a && typeof a === "object")
    .map((a) =>
      plainText([a.given, a.family].filter(Boolean).join(" ") || a.name),
    )
    .filter(Boolean);
  const doi = typeof work.DOI === "string" ? work.DOI : "";
  return {
    id: doi || safeUrl(work.URL),
    doi,
    title: plainText(work.title?.[0] || "Untitled work"),
    authors,
    year,
    venue: plainText(
      work["container-title"]?.[0] || work.publisher || "Academic publication",
    ),
    abstract: plainText(work.abstract),
    citations: Number.isFinite(Number(work["is-referenced-by-count"]))
      ? Math.max(0, Number(work["is-referenced-by-count"]))
      : 0,
    url: safeUrl(doi ? `https://doi.org/${doi}` : work.URL),
    pdf: safeUrl(
      (Array.isArray(work.link) ? work.link : []).find(
        (l) => l?.["content-type"] === "application/pdf",
      )?.URL,
    ),
    source: "Crossref",
  };
}
export async function discover(
  query,
  { year = "", sort = "relevance", page = 1, field = "all", signal } = {},
) {
  const params = new URLSearchParams({
    rows: "12",
    offset: String((page - 1) * 12),
    [field === "author"
      ? "query.author"
      : field === "title"
        ? "query.title"
        : "query.bibliographic"]: query,
    sort:
      {
        relevance: "relevance",
        newest: "published",
        citations: "is-referenced-by-count",
      }[sort] || "relevance",
    order: "desc",
  });
  if (year) params.set("filter", `from-pub-date:${year}-01-01`);
  let response;
  for (let attempt = 0; attempt < 2; attempt++) {
    response = await fetch(`https://api.crossref.org/works?${params}`, {
      signal,
    });
    if (![429, 503].includes(response.status) || attempt === 1) break;
    await new Promise((resolve) => setTimeout(resolve, 1200));
  }
  if (!response.ok)
    throw new Error(
      response.status === 429
        ? "The research index is busy. Please wait a moment and retry."
        : `Research index unavailable (${response.status}). Please retry.`,
    );
  const data = await response.json();
  if (!Array.isArray(data.message?.items))
    throw new Error("The research index returned an unexpected response.");
  return {
    papers: data.message.items.map(normalizeWork).filter((p) => p.id),
    total: data.message["total-results"] || 0,
  };
}
export function citation(paper, style = "APA", index = 1) {
  const authors = paper.authors?.join(", ") || "Unknown author";
  const year = paper.year || "n.d.";
  if (style === "BibTeX") {
    const escape = (s) =>
      String(s || "")
        .replace(/[{}\\]/g, "")
        .replace(/[\r\n]/g, " ");
    return `@article{${escape(paper.doi || paper.id).replace(/[^a-zA-Z0-9]/g, "")},\n  title = {${escape(paper.title)}},\n  author = {${(paper.authors || []).map(escape).join(" and ")}},\n  year = {${year}},\n  journal = {${escape(paper.venue)}},\n  doi = {${escape(paper.doi)}}\n}`;
  }
  if (style === "IEEE")
    return `[${index}] ${authors}, “${paper.title},” ${paper.venue || ""}, ${year}. ${paper.url || ""}`;
  if (style === "MLA")
    return `${authors}. “${paper.title}.” ${paper.venue || ""}, ${year}, ${paper.url || ""}.`;
  return `${authors} (${year}). ${paper.title}. ${paper.venue || ""}. ${paper.url || ""}`;
}
export function download(
  filename,
  content,
  type = "text/markdown;charset=utf-8",
) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function readLocal(key, fallback) {
  try {
    const value = JSON.parse(localStorage.getItem(key));
    if (
      value === null ||
      typeof value !== typeof fallback ||
      Array.isArray(value) !== Array.isArray(fallback)
    )
      return fallback;
    return value;
  } catch {
    return fallback;
  }
}
