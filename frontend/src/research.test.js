import { vi } from "vitest";
import { citation, discover, normalizeWork, safeUrl } from "./research";

const work = {
  DOI: "10.1000/research",
  title: ["Real research"],
  author: [{ given: "Ada", family: "Lovelace" }],
  published: { "date-parts": [[2025]] },
  "container-title": ["Science"],
  abstract: "<jats:p>Publisher evidence.</jats:p>",
  "is-referenced-by-count": 12,
};
test("normalizes publisher evidence and preserves missing abstract", () => {
  const paper = normalizeWork(work);
  expect(paper.abstract).toBe("Publisher evidence.");
  expect(paper.authors).toEqual(["Ada Lovelace"]);
  expect(paper.year).toBe(2025);
  expect(normalizeWork({ DOI: "10.1000/a" }).abstract).toBe("");
});
test("malformed optional publisher metadata does not break the result list", () => {
  expect(normalizeWork(null).id).toBe("");
  const paper = normalizeWork({
    DOI: "10.1000/test",
    author: {},
    link: null,
    "is-referenced-by-count": "not a number",
  });
  expect(paper.authors).toEqual([]);
  expect(paper.citations).toBe(0);
});
test("rejects unsafe source and PDF URLs", () => {
  for (const url of [
    "javascript:alert(1)",
    "data:text/html,hello",
    "/relative",
    "not a URL",
  ])
    expect(safeUrl(url)).toBe("");
  expect(safeUrl("https://doi.org/10.1000/research")).toContain(
    "https://doi.org/",
  );
});
test("exports distinct citation styles and escapes BibTeX braces", () => {
  const paper = normalizeWork(work);
  expect(citation(paper, "APA")).toContain("(2025)");
  expect(citation(paper, "IEEE", 3)).toMatch(/^\[3\]/);
  expect(citation(paper, "MLA")).toContain("“Real research.”");
  expect(
    citation({ ...paper, title: "A {title} \\ command" }, "BibTeX"),
  ).toContain("title = {A title  command}");
});
test("encodes filters, author query and pagination in upstream request", async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ message: { items: [work], "total-results": 42 } }),
  });
  const data = await discover("Ada & graphs", {
    field: "author",
    year: "2024",
    sort: "citations",
    page: 2,
  });
  const url = new URL(global.fetch.mock.calls[0][0]);
  expect(url.searchParams.get("query.author")).toBe("Ada & graphs");
  expect(url.searchParams.get("filter")).toBe("from-pub-date:2024-01-01");
  expect(url.searchParams.get("offset")).toBe("12");
  expect(data.total).toBe(42);
  expect(data.papers[0].title).toBe("Real research");
});
test("rejects malformed upstream data and propagates non-success responses", async () => {
  global.fetch = vi
    .fn()
    .mockResolvedValue({ ok: true, json: async () => ({ message: {} }) });
  await expect(discover("research")).rejects.toThrow("unexpected response");
  global.fetch.mockResolvedValue({ ok: false, status: 500 });
  await expect(discover("research")).rejects.toThrow("500");
});
