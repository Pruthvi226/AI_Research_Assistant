import React, {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import {
  ArrowDownToLine,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  Bookmark,
  ChevronLeft,
  ChevronRight,
  HelpCircle,
  FileText,
  FlaskConical,
  History,
  Layers,
  Menu,
  MessageSquare,
  Moon,
  Plus,
  Search,
  Send,
  Settings,
  Sparkles,
  Sun,
  Upload,
  X,
} from "lucide-react";
import api, {
  API_BASE,
  backendConfigured,
  errorMessage,
  getHistory,
  healthCheck,
  uploadPaper,
} from "./api";
import { citation, discover, download, readLocal, safeUrl } from "./research";
import PaperCard from "./components/PaperCard";
const Markdown = lazy(() => import("./components/Markdown"));

const suggestions = [
  "Retrieval-augmented generation",
  "AI for drug discovery",
  "Efficient language models",
  "Climate change adaptation",
];
const navigation = [
  { id: "discover", label: "Discover", icon: Search },
  { id: "chat", label: "Research assistant", icon: MessageSquare },
  { id: "library", label: "My library", icon: Bookmark },
  { id: "documents", label: "Paper workspace", icon: FileText },
  { id: "review", label: "Literature review", icon: Layers },
  { id: "history", label: "Research history", icon: History },
];
function initialTab() {
  return navigation.some((n) => n.id === window.location.hash.slice(1)) ||
    window.location.hash === "#settings"
    ? window.location.hash.slice(1)
    : "discover";
}
function useLocal(key, fallback) {
  const [value, setValue] = useState(() => readLocal(key, fallback));
  useEffect(() => {
    try {
      localStorage.setItem(key, JSON.stringify(value));
    } catch {
      /* Storage may be disabled or full. Current session remains usable. */
    }
  }, [key, value]);
  return [value, setValue];
}
function Empty({ icon: Icon = BookOpen, title, children }) {
  return (
    <div className="empty-state">
      <span className="empty-icon">
        <Icon size={26} />
      </span>
      <h2>{title}</h2>
      <p>{children}</p>
    </div>
  );
}
function TextOutput({ value }) {
  return (
    <div className="text-output">
      <Suspense fallback={typeof value === "string" ? value : "Loading…"}>
        <Markdown
          value={
            typeof value === "string" ? value : JSON.stringify(value, null, 2)
          }
        />
      </Suspense>
    </div>
  );
}

export default function App() {
  const [tab, setTab] = useState(initialTab);
  const [collapsed, setCollapsed] = useLocal("scientia.sidebar", false);
  const [mobileNav, setMobileNav] = useState(false);
  const [theme, setTheme] = useLocal("scientia.theme", "light");
  const [bookmarks, setBookmarks] = useLocal("scientia.bookmarks", []);
  const [notes, setNotes] = useLocal("scientia.notes", {});
  const [history, setHistory] = useLocal("scientia.history", []);
  const [messages, setMessages] = useLocal("scientia.conversation", []);
  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState("");
  const [results, setResults] = useState([]);
  const [total, setTotal] = useState(0);
  const [year, setYear] = useState("");
  const [field, setField] = useState("all");
  const [sort, setSort] = useState("relevance");
  const [page, setPage] = useState(1);
  const [searching, setSearching] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [status, setStatus] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [active, setActive] = useState(null);
  const [docMessages, setDocMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [selected, setSelected] = useState([]);
  const [review, setReview] = useState(null);
  const [progress, setProgress] = useState(null);
  const [tool, setTool] = useState("rag");
  const [toolOutput, setToolOutput] = useState(null);
  const [docSelected, setDocSelected] = useState([]);
  const [docComparison, setDocComparison] = useState(null);
  const [localFilter, setLocalFilter] = useState("");
  const searchController = useRef(null);
  const uploadController = useRef(null);
  const fileInput = useRef(null);
  const messageEnd = useRef(null);
  const requestVersion = useRef(0);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
  }, [theme]);
  useEffect(() => {
    const handler = () => setTab(initialTab());
    window.addEventListener("hashchange", handler);
    return () => window.removeEventListener("hashchange", handler);
  }, []);
  useEffect(() => {
    if (tab === "chat")
      messageEnd.current?.scrollIntoView({
        behavior: "smooth",
        block: "nearest",
      });
  }, [messages, docMessages, tab]);
  const connect = useCallback(async () => {
    if (!backendConfigured) return;
    try {
      setStatus(await healthCheck());
      const listed = (await api.get("/api/documents")).data.documents;
      if (!Array.isArray(listed))
        throw new Error("Invalid document list response.");
      setDocuments(
        listed.map((doc) => ({ ...doc, session_id: doc.session_id || doc.id })),
      );
    } catch {
      setStatus({ offline: true });
    }
  }, []);
  useEffect(() => {
    connect();
    return () => {
      searchController.current?.abort();
      uploadController.current?.abort();
    };
  }, [connect]);
  function navigate(next) {
    window.location.hash = next;
    setTab(next);
    setMobileNav(false);
    setError("");
  }
  async function run(action) {
    setBusy(true);
    setError("");
    try {
      await action();
      return true;
    } catch (e) {
      setError(errorMessage(e));
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function search(text = query, nextPage = 1, filters = {}) {
    const trimmed = text.trim();
    if (trimmed.length < 2) {
      setError("Enter at least two characters to search.");
      return;
    }
    searchController.current?.abort();
    const controller = new AbortController();
    searchController.current = controller;
    const timeout = setTimeout(() => controller.abort("timeout"), 25000);
    navigate("discover");
    setQuery(trimmed);
    setSearched(trimmed);
    setPage(nextPage);
    setSearching(true);
    setError("");
    try {
      const data = await discover(trimmed, {
        year,
        sort,
        field,
        page: nextPage,
        ...filters,
        signal: controller.signal,
      });
      if (searchController.current !== controller || controller.signal.aborted)
        return;
      setResults(data.papers);
      setTotal(data.total);
      setHistory((prev) =>
        [
          { query: trimmed, date: new Date().toISOString() },
          ...prev.filter((h) => h.query !== trimmed),
        ].slice(0, 40),
      );
    } catch (e) {
      if (
        !controller.signal.aborted ||
        controller.signal.reason === "timeout"
      ) {
        setResults([]);
        setTotal(0);
        setError(
          controller.signal.aborted
            ? "Search timed out. Please retry."
            : errorMessage(e),
        );
      }
    } finally {
      clearTimeout(timeout);
      if (searchController.current === controller) setSearching(false);
    }
  }
  function toggleSave(paper) {
    setBookmarks((prev) =>
      prev.some((p) => p.id === paper.id)
        ? prev.filter((p) => p.id !== paper.id)
        : [paper, ...prev],
    );
  }
  function toggleSelect(id) {
    setSelected((prev) =>
      prev.includes(id)
        ? prev.filter((x) => x !== id)
        : prev.length < 8
          ? [...prev, id]
          : prev,
    );
    setReview(null);
  }
  async function openDocument(doc) {
    const version = ++requestVersion.current;
    setActive(doc);
    setDocMessages([]);
    setToolOutput(null);
    navigate("documents");
    await run(async () => {
      const [detail, past] = await Promise.all([
        api.get(`/api/documents/${encodeURIComponent(doc.session_id)}`),
        getHistory(doc.session_id),
      ]);
      if (version !== requestVersion.current) return;
      setActive(detail.data);
      setDocMessages(
        past.history.map((m) => ({
          role: m.role,
          content: m.content,
          sources: m.sections,
        })),
      );
    });
  }
  function upload(file) {
    if (!file) return;
    navigate("documents");
    run(async () => {
      uploadController.current = new AbortController();
      setProgress({ progress: 0, message: "Uploading PDF…" });
      try {
        const doc = await uploadPaper(
          file,
          setProgress,
          uploadController.current.signal,
        );
        setActive(doc);
        setDocMessages([]);
        await connect();
      } finally {
        setProgress(null);
      }
    });
  }
  async function send(event) {
    event.preventDefault();
    if (!question.trim() || busy) return;
    const text = question.trim();
    setQuestion("");
    const setter = active ? setDocMessages : setMessages;
    const past = active ? docMessages : messages;
    const succeeded = await run(async () => {
      let data;
      if (active)
        data = (
          await api.post("/api/chat", {
            question: text,
            session_id: active.session_id,
            agent: tool,
            generate_audio: false,
          })
        ).data;
      else
        data = (
          await api.post("/api/research/answer", {
            question: text,
            history: past.slice(-10),
            papers: results.slice(0, 8),
          })
        ).data;
      setter((prev) =>
        [
          ...prev,
          { role: "user", content: text },
          {
            role: "assistant",
            content: data.response || data.answer,
            sources: data.sources || [],
            mode: data.mode || data.artifacts?.mode,
            artifacts: data.artifacts,
          },
        ].slice(-80),
      );
    });
    if (!succeeded) setQuestion(text);
  }
  const selectedPapers = bookmarks.filter((p) => selected.includes(p.id));
  async function generateReview() {
    await run(async () => {
      setReview(
        (
          await api.post(
            "/api/research/review",
            {
              paper_ids: selectedPapers.map((p) => p.doi),
            },
            { timeout: 120000 },
          )
        ).data,
      );
    });
  }
  const citationExport = (style) =>
    download(
      `scientia-library.${style === "BibTeX" ? "bib" : "txt"}`,
      bookmarks.map((p, i) => citation(p, style, i + 1)).join("\n\n"),
      "text/plain;charset=utf-8",
    );
  function report() {
    const paperText = selectedPapers
      .map(
        (p) =>
          `## ${p.title}\n${citation(p)}\n\n${p.abstract || "Abstract unavailable."}\n\nNotes: ${notes[p.id] || "None"}`,
      )
      .join("\n\n");
    download(
      "scientia-literature-review.md",
      `# Literature review\n\n${review?.response || "Metadata collection. No AI analysis has been generated."}\n\n${paperText}`,
    );
  }
  const connected = status && !status.offline;
  const aiEnabled = connected && status.mode?.includes("Gemini");
  const card = (paper, library = false) => (
    <PaperCard
      key={paper.id}
      paper={paper}
      saved={bookmarks.some((p) => p.id === paper.id)}
      onSave={toggleSave}
      selected={selected.includes(paper.id)}
      onSelect={library ? () => toggleSelect(paper.id) : undefined}
      note={notes[paper.id]}
      onNote={
        library
          ? (value) => setNotes((prev) => ({ ...prev, [paper.id]: value }))
          : undefined
      }
    />
  );
  const chatMessages = active ? docMessages : messages;

  return (
    <div className={`app-shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <a
        href="#main-content"
        className="skip-link"
        onClick={(e) => {
          e.preventDefault();
          document.getElementById("main-content").focus();
        }}
      >
        Skip to content
      </a>
      {mobileNav && (
        <button
          className="nav-scrim"
          aria-label="Close navigation"
          onClick={() => setMobileNav(false)}
        />
      )}
      <aside className={`sidebar ${mobileNav ? "mobile-open" : ""}`}>
        <a
          className="brand"
          href="#discover"
          onClick={() => navigate("discover")}
        >
          <span className="brand-icon">
            <FlaskConical size={21} />
          </span>
          <span className="brand-name">
            scientia<span className="brand-period">.</span>
            <small>THE RESEARCH WORKSPACE</small>
          </span>
        </a>
        <button
          className="new-research"
          onClick={() => {
            setQuery("");
            setSearched("");
            setResults([]);
            navigate("discover");
          }}
        >
          <Plus size={17} />
          <span>New research</span>
          <span className="key-hint">↗</span>
        </button>
        <span className="nav-caption">WORKSPACE</span>
        <nav aria-label="Main navigation">
          {navigation.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${tab === id ? "active" : ""}`}
              onClick={() => navigate(id)}
              aria-label={label}
              title={collapsed ? label : undefined}
              aria-current={tab === id ? "page" : undefined}
            >
              <Icon size={18} />
              <span>{label}</span>
              {id === "library" && (
                <span className="nav-count">{bookmarks.length}</span>
              )}
            </button>
          ))}
        </nav>
        {!collapsed && (
          <div className="sidebar-recent">
            <span className="nav-caption">RECENT EXPLORATIONS</span>
            {history.slice(0, 3).map((item) => (
              <button key={item.query} onClick={() => search(item.query)}>
                <span className="recent-dot" />
                {item.query}
              </button>
            ))}
            {!history.length && <p>Your next discovery starts here.</p>}
          </div>
        )}
        <div className="sidebar-bottom">
          <div className="workspace-note">
            <span className="tiny-spark">✦</span>
            <strong>
              A little curiosity.
              <br />A lot of possibility.
            </strong>
            <p>Your next breakthrough is one question away.</p>
          </div>
          <button
            className={`nav-item ${tab === "settings" ? "active" : ""}`}
            onClick={() => navigate("settings")}
            title="Settings"
          >
            <Settings size={18} />
            <span>Settings & connection</span>
          </button>
          <div className="profile">
            <span className="avatar">R</span>
            <div>
              <strong>Research workspace</strong>
              <small>Personal · stored on this device</small>
            </div>
            <button
              className="icon-button collapse-toggle"
              aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
              onClick={() => setCollapsed(!collapsed)}
            >
              {collapsed ? (
                <ChevronRight size={16} />
              ) : (
                <ChevronLeft size={16} />
              )}
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMobileNav(true)}
            >
              <Menu size={20} />
            </button>
            <BookOpen size={15} />
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>
              {navigation.find((n) => n.id === tab)?.label || "Settings"}
            </strong>
          </div>
          <div className="topbar-actions">
            <span
              className={`connection-badge ${connected ? "connected" : ""}`}
            >
              <i />
              {connected
                ? aiEnabled
                  ? "AI configured"
                  : "Local analysis"
                : backendConfigured
                  ? status === null
                    ? "Connecting…"
                    : "API offline"
                  : "Discovery mode"}
            </span>
            <button
              className="icon-button"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
              aria-label={`Switch to ${theme === "light" ? "dark" : "light"} theme`}
            >
              {theme === "light" ? <Moon size={18} /> : <Sun size={18} />}
            </button>
            <button
              className="icon-button"
              aria-label="Help and connection settings"
              onClick={() => navigate("settings")}
            >
              <HelpCircle size={18} />
            </button>
            <span className="avatar small">R</span>
          </div>
        </header>
        <main id="main-content" tabIndex={-1}>
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button
                className="icon-button"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {tab === "discover" && (
            <div className={`discover-page ${searched ? "has-results" : ""}`}>
              <div className="hero">
                <span className="eyebrow">
                  <span /> BUILT FOR CURIOUS MINDS
                </span>
                <h1>
                  From a question
                  <br />
                  to your next <em>discovery.</em>
                </h1>
                <p>
                  Explore the literature. Connect the ideas.
                  <br className="mobile-break" /> Make room for your next
                  breakthrough.
                </p>
                <form
                  className="search-box"
                  onSubmit={(e) => {
                    e.preventDefault();
                    search();
                  }}
                >
                  <div className="search-input-row">
                    <Search size={22} />
                    <input
                      aria-label="Research query"
                      placeholder="What would you like to explore?"
                      value={query}
                      onChange={(e) => setQuery(e.target.value)}
                      maxLength={300}
                      required
                      minLength={2}
                    />
                    <button
                      className="search-submit"
                      aria-label="Search academic papers"
                      disabled={searching}
                    >
                      <ArrowRight size={21} />
                    </button>
                  </div>
                  <div className="search-bottom">
                    <span>
                      <span className="source-dot" /> Academic literature search
                    </span>
                    <span>
                      Powered by Crossref <ArrowUpRight size={12} />
                    </span>
                  </div>
                </form>
                {!searched && (
                  <div className="suggestions">
                    <span>A starting point</span>
                    {suggestions.map((text) => (
                      <button key={text} onClick={() => search(text)}>
                        {text}
                        <ArrowUpRight size={12} />
                      </button>
                    ))}
                  </div>
                )}
              </div>
              {searched ? (
                <section className="search-results" aria-busy={searching}>
                  <div className="section-heading">
                    <div>
                      <span className="eyebrow">THE LITERATURE</span>
                      <h2>
                        Research, in focus
                        <span className="result-count">
                          {searching
                            ? "Searching…"
                            : `${total.toLocaleString()} results`}
                        </span>
                      </h2>
                    </div>
                    <button
                      className="text-button"
                      onClick={() => {
                        navigate("chat");
                        setQuestion(
                          `What does the literature say about ${searched}?`,
                        );
                      }}
                    >
                      <Sparkles size={15} /> Explore with AI
                    </button>
                  </div>
                  <div className="filter-bar">
                    <label>
                      Search in
                      <select
                        aria-label="Search in"
                        value={field}
                        onChange={(e) => {
                          setField(e.target.value);
                          search(searched, 1, { field: e.target.value });
                        }}
                      >
                        <option value="all">All metadata</option>
                        <option value="title">Paper title</option>
                        <option value="author">Author</option>
                      </select>
                    </label>
                    <label>
                      Published
                      <select
                        aria-label="Published"
                        value={year}
                        onChange={(e) => {
                          setYear(e.target.value);
                          search(searched, 1, { year: e.target.value });
                        }}
                      >
                        <option value="">Any time</option>
                        {[2026, 2025, 2024, 2020, 2015].map((y) => (
                          <option key={y} value={y}>
                            Since {y}
                          </option>
                        ))}
                      </select>
                    </label>
                    <label>
                      Sort by
                      <select
                        aria-label="Sort by"
                        value={sort}
                        onChange={(e) => {
                          setSort(e.target.value);
                          search(searched, 1, { sort: e.target.value });
                        }}
                      >
                        <option value="relevance">Most relevant</option>
                        <option value="newest">Newest first</option>
                        <option value="citations">Most cited</option>
                      </select>
                    </label>
                  </div>
                  {searching ? (
                    <div className="paper-grid">
                      {[0, 1, 2, 3].map((n) => (
                        <div className="skeleton paper-card" key={n}>
                          <i />
                          <i />
                          <i />
                          <i />
                        </div>
                      ))}
                    </div>
                  ) : results.length ? (
                    <div className="paper-grid">
                      {results.map((p) => card(p))}
                    </div>
                  ) : (
                    <Empty title="No papers found">
                      Try a broader topic, a different author, or a wider
                      publication date range.
                    </Empty>
                  )}
                  {!searching && results.length > 0 && (
                    <div className="pagination">
                      <button
                        className="secondary-button"
                        disabled={page === 1}
                        onClick={() => search(searched, page - 1)}
                      >
                        <ChevronLeft size={15} /> Previous
                      </button>
                      <span>Page {page}</span>
                      <button
                        className="secondary-button"
                        disabled={page * 12 >= total || page >= 100}
                        onClick={() => search(searched, page + 1)}
                      >
                        Next <ChevronRight size={15} />
                      </button>
                    </div>
                  )}
                </section>
              ) : (
                <>
                  <section className="pathways">
                    <div className="section-heading">
                      <h2>A clearer path to understanding</h2>
                      <span>YOUR IDEAS. A LITTLE SUPERCHARGED.</span>
                    </div>
                    <div className="pathway-grid">
                      {[
                        {
                          icon: Search,
                          label: "Discover the literature",
                          text: "Find the papers that matter. Follow the evidence, beyond the noise.",
                          action: "Start exploring",
                          tab: "discover",
                          color: "green",
                        },
                        {
                          icon: FileText,
                          label: "Go deeper into a paper",
                          text: "Turn dense research into clear insights. Ask questions. Find your answers.",
                          action: "Upload a paper",
                          tab: "documents",
                          color: "peach",
                        },
                        {
                          icon: Layers,
                          label: "See the bigger picture",
                          text: "Bring papers together. Compare approaches. Uncover what comes next.",
                          action: "Build a literature review",
                          tab: "review",
                          color: "purple",
                        },
                      ].map(
                        ({
                          icon: Icon,
                          label,
                          text,
                          action,
                          tab: next,
                          color,
                        }) => (
                          <button
                            className="pathway-card"
                            key={label}
                            onClick={() => {
                              navigate(next);
                              if (next === "discover")
                                document
                                  .querySelector(
                                    '[aria-label="Research query"]',
                                  )
                                  ?.focus();
                            }}
                          >
                            <span className={`feature-icon ${color}`}>
                              <Icon size={21} />
                            </span>
                            <h3>{label}</h3>
                            <p>{text}</p>
                            <span className="pathway-action">
                              {action}
                              <ArrowRight size={14} />
                            </span>
                          </button>
                        ),
                      )}
                    </div>
                  </section>
                  <section className="research-principle">
                    <span className="principle-mark">✳</span>
                    <div>
                      <h3>Good research starts with good sources.</h3>
                      <p>
                        Real publications. Traceable citations. A workspace that
                        keeps evidence in view.
                      </p>
                    </div>
                    <span className="principle-label">
                      <span className="source-dot" /> EVIDENCE, ALWAYS
                    </span>
                  </section>
                </>
              )}
              <footer>
                <span>Made for the pursuit of knowledge.</span>
                <span>
                  Scientia <span className="footer-star">✦</span> Stay curious.
                </span>
              </footer>
            </div>
          )}

          {tab === "library" && (
            <div className="content-page">
              <PageHeading
                eyebrow="YOUR RESEARCH, COLLECTED"
                title="My library"
                description="Keep the ideas worth returning to. Add notes, export citations, and select up to eight papers for a review."
              />
              <div className="toolbar">
                <input
                  aria-label="Filter saved papers"
                  placeholder="Filter your library…"
                  value={localFilter}
                  onChange={(e) => setLocalFilter(e.target.value)}
                />
                <button
                  className="secondary-button"
                  disabled={!bookmarks.length}
                  onClick={() => citationExport("BibTeX")}
                >
                  <ArrowDownToLine size={16} /> BibTeX
                </button>
                <button
                  className="secondary-button"
                  disabled={!bookmarks.length}
                  onClick={() => citationExport("APA")}
                >
                  Export citations
                </button>
                <button
                  className="primary-button"
                  onClick={() => navigate("review")}
                  disabled={!selectedPapers.length}
                >
                  Review {selectedPapers.length || ""} papers{" "}
                  <ArrowRight size={15} />
                </button>
              </div>
              {bookmarks.length ? (
                <div className="paper-grid">
                  {bookmarks
                    .filter((p) =>
                      `${p.title} ${p.authors.join(" ")}`
                        .toLowerCase()
                        .includes(localFilter.toLowerCase()),
                    )
                    .map((p) => card(p, true))}
                </div>
              ) : (
                <Empty icon={Bookmark} title="A home for your next big idea">
                  Save a paper from Discover and it will appear here. Bookmarks
                  and notes stay in this browser.
                </Empty>
              )}
            </div>
          )}

          {tab === "history" && (
            <div className="content-page">
              <PageHeading
                eyebrow="FOLLOW YOUR CURIOSITY"
                title="Research history"
                description="Pick up where you left off. Your recent searches are stored on this device."
              />
              <div className="toolbar">
                <button
                  className="secondary-button"
                  disabled={!history.length}
                  onClick={() => setHistory([])}
                >
                  Clear search history
                </button>
              </div>
              {history.length ? (
                <div className="history-list">
                  {history.map((h) => (
                    <button key={h.query} onClick={() => search(h.query)}>
                      <History size={19} />
                      <div>
                        <strong>{h.query}</strong>
                        <small>{new Date(h.date).toLocaleString()}</small>
                      </div>
                      <ArrowUpRight size={18} />
                    </button>
                  ))}
                </div>
              ) : (
                <Empty icon={History} title="Your research journey starts here">
                  Explore a topic to start building your history.
                </Empty>
              )}
            </div>
          )}

          {tab === "review" && (
            <div className="content-page">
              <PageHeading
                eyebrow="CONNECT THE IDEAS"
                title="The bigger picture"
                description="A structured view across your sources, with uncertainty and missing evidence made explicit."
              />
              <div className="info-banner">
                <Layers size={18} />
                <span>
                  Select papers in My library to compare them. Metadata can be
                  exported anytime; AI analysis needs the backend and uses
                  retrieved abstracts, not full texts.
                </span>
              </div>
              <div className="toolbar">
                <button
                  className="secondary-button"
                  onClick={() => navigate("library")}
                >
                  Choose papers ({selectedPapers.length}/8)
                </button>
                <button
                  className="secondary-button"
                  disabled={!selectedPapers.length}
                  onClick={report}
                >
                  <ArrowDownToLine size={16} /> Export report
                </button>
                <button
                  className="primary-button"
                  disabled={busy || selectedPapers.length < 2 || !aiEnabled}
                  onClick={generateReview}
                >
                  <Sparkles size={16} />
                  {busy ? "Reviewing sources…" : "Generate review"}
                </button>
              </div>
              {!aiEnabled && (
                <p className="metadata-note">
                  Connect a backend with Gemini enabled in Settings to generate
                  AI reviews.
                </p>
              )}
              {selectedPapers.length ? (
                <>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Paper</th>
                          <th>Authors / year</th>
                          <th>Evidence available</th>
                          <th>Citations</th>
                        </tr>
                      </thead>
                      <tbody>
                        {selectedPapers.map((p) => (
                          <tr key={p.id}>
                            <td>
                              <a
                                href={safeUrl(p.url)}
                                target="_blank"
                                rel="noreferrer"
                              >
                                {p.title}
                              </a>
                            </td>
                            <td>
                              {p.authors.slice(0, 2).join(", ")} · {p.year}
                            </td>
                            <td>
                              {p.abstract
                                ? "Publisher abstract"
                                : "Metadata only"}
                            </td>
                            <td>{p.citations}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  {review && (
                    <article className="output-card">
                      <span className="eyebrow">
                        AI ANALYSIS · VERIFY AGAINST ORIGINAL PAPERS
                      </span>
                      <TextOutput value={review.response} />
                    </article>
                  )}
                </>
              ) : (
                <Empty icon={Layers} title="Many papers. One perspective.">
                  Save and select at least two papers in your library to begin
                  comparing research.
                </Empty>
              )}
            </div>
          )}

          {tab === "documents" && (
            <div className="content-page">
              <PageHeading
                eyebrow="READ WITH A RESEARCH PARTNER"
                title="Paper workspace"
                description="Upload a PDF, uncover its key ideas, and ask questions grounded in the text."
              />
              {status?.storage_mode === "ephemeral" && (
                <div className="info-banner" role="status">
                  This free demo stores PDFs temporarily. Uploaded papers and
                  document chats reset when the server sleeps, restarts, or
                  redeploys. Download your reports before leaving.
                </div>
              )}
              <div className="upload-zone">
                <span className="feature-icon green">
                  <Upload size={23} />
                </span>
                <div>
                  <h3>Bring your paper into focus</h3>
                  <p>
                    PDF documents · up to 20 MB · processed by your connected
                    backend
                  </p>
                </div>
                <button
                  className="primary-button"
                  disabled={busy || !connected}
                  onClick={() => fileInput.current.click()}
                >
                  <Plus size={16} /> Upload PDF
                </button>
                <input
                  ref={fileInput}
                  type="file"
                  accept="application/pdf,.pdf"
                  hidden
                  onChange={(e) => {
                    upload(e.target.files[0]);
                    e.target.value = "";
                  }}
                />
              </div>
              {!connected && (
                <div className="info-banner">
                  Connect the research API in Settings to upload and analyze
                  documents.
                </div>
              )}
              {progress && (
                <div className="upload-progress" role="status">
                  <progress value={progress.progress || 0} max="100" />
                  <span>{progress.message}</span>
                </div>
              )}
              <div className="toolbar">
                {documents.length >= 2 && (
                  <>
                    <button
                      className="secondary-button"
                      disabled={busy || docSelected.length < 2 || !aiEnabled}
                      onClick={() =>
                        run(async () => {
                          setDocComparison(
                            (
                              await api.post("/api/synthesis", {
                                session_ids: docSelected,
                              })
                            ).data,
                          );
                        })
                      }
                    >
                      Compare selected PDFs ({docSelected.length}/8)
                    </button>
                    <button
                      className="secondary-button"
                      disabled={busy || docSelected.length < 2}
                      onClick={() => {
                        setActive({
                          session_id: docSelected.join(","),
                          filename: `${docSelected.length} selected papers`,
                        });
                        setDocMessages([]);
                        navigate("chat");
                      }}
                    >
                      Ask across selected papers
                    </button>
                  </>
                )}
              </div>
              <div className="document-list">
                {documents.map((d) => (
                  <div className="document-item" key={d.session_id}>
                    <label className="select-paper">
                      <input
                        type="checkbox"
                        aria-label={`Select ${d.filename} for comparison`}
                        checked={docSelected.includes(d.session_id)}
                        disabled={busy}
                        onChange={() =>
                          setDocSelected((prev) =>
                            prev.includes(d.session_id)
                              ? prev.filter((id) => id !== d.session_id)
                              : prev.length < 8
                                ? [...prev, d.session_id]
                                : prev,
                          )
                        }
                      />
                      Compare
                    </label>
                    <button
                      className={`document-chip ${active?.session_id === d.session_id ? "selected" : ""}`}
                      disabled={busy}
                      key={d.session_id}
                      onClick={() => openDocument(d)}
                    >
                      <FileText size={16} />
                      {d.filename}
                    </button>
                  </div>
                ))}
              </div>
              {docComparison && (
                <article className="output-card">
                  <span className="eyebrow">
                    AI COMPARISON ? VERIFY AGAINST THE ORIGINAL PAPERS
                  </span>
                  <div className="table-wrap">
                    <table>
                      <thead>
                        <tr>
                          <th>Attribute</th>
                          {Object.entries(docComparison.headers || {}).map(
                            ([id, name]) => (
                              <th key={id}>{name}</th>
                            ),
                          )}
                        </tr>
                      </thead>
                      <tbody>
                        {(docComparison.comparisons || []).map((row) => (
                          <tr key={row.attribute}>
                            <td>{row.attribute}</td>
                            {Object.keys(docComparison.headers || {}).map(
                              (id) => (
                                <td key={id}>
                                  {row.values?.[id] || "Not reported"}
                                </td>
                              ),
                            )}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <button
                    className="secondary-button"
                    onClick={() =>
                      download(
                        "pdf-comparison.json",
                        JSON.stringify(docComparison, null, 2),
                        "application/json",
                      )
                    }
                  >
                    Export comparison
                  </button>
                </article>
              )}
              {active ? (
                <article className="output-card">
                  <div className="section-heading">
                    <h2>{active.filename}</h2>
                    <button
                      className="secondary-button"
                      onClick={() =>
                        download(
                          "paper-analysis.md",
                          `# ${active.filename}\n\n${active.summary?.abstract || ""}\n\n${JSON.stringify(active.agent_analysis || active.summary?.sections || {}, null, 2)}`,
                        )
                      }
                    >
                      <ArrowDownToLine size={16} /> Report
                    </button>
                  </div>
                  <span className="eyebrow">
                    {active.performance?.mode?.includes("gemini")
                      ? "AI ANALYSIS · VERIFY FINDINGS"
                      : "EXTRACTIVE ANALYSIS · SOURCE SENTENCES"}
                  </span>
                  <p className="document-abstract">
                    {active.summary?.abstract}
                  </p>
                  {Object.entries(
                    active.agent_analysis || active.summary?.sections || {},
                  ).map(([key, value]) => (
                    <details key={key}>
                      <summary>{key.replace(/_/g, " ")}</summary>
                      <TextOutput value={value} />
                    </details>
                  ))}
                  <div className="toolbar">
                    <button
                      className="primary-button"
                      onClick={() => navigate("chat")}
                    >
                      <MessageSquare size={16} /> Ask this paper
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() =>
                        run(async () => {
                          setToolOutput(
                            (
                              await api.post("/api/citations", {
                                session_id: active.session_id,
                              })
                            ).data,
                          );
                        })
                      }
                      disabled={busy}
                    >
                      Extract references
                    </button>
                    <button
                      className="secondary-button"
                      onClick={() =>
                        run(async () => {
                          setToolOutput(
                            (
                              await api.post("/api/podcast", {
                                session_id: active.session_id,
                                generate_audio: false,
                              })
                            ).data,
                          );
                        })
                      }
                      disabled={busy}
                    >
                      Briefing script
                    </button>
                  </div>
                  {toolOutput && (
                    <TextOutput
                      value={
                        toolOutput.script ||
                        toolOutput.response ||
                        toolOutput.artifacts ||
                        toolOutput
                      }
                    />
                  )}
                </article>
              ) : (
                <Empty icon={FileText} title="Every paper has a story">
                  Upload a research PDF or choose a previously uploaded paper to
                  read its analysis. Use public papers in a shared demo
                  workspace.
                </Empty>
              )}
            </div>
          )}

          {tab === "chat" && (
            <div className="chat-page">
              <div className="chat-heading">
                <span className="feature-icon green">
                  <Sparkles size={20} />
                </span>
                <div>
                  <h2>Think it through, together.</h2>
                  <p>
                    {active
                      ? `Source: ${active.filename}`
                      : "Source-backed exploration with your research assistant."}
                  </p>
                </div>
                {active && (
                  <button
                    className="text-button"
                    disabled={busy}
                    onClick={() => {
                      setActive(null);
                      setDocMessages([]);
                    }}
                  >
                    Detach paper
                  </button>
                )}
                <button
                  className="icon-button"
                  aria-label="Start new conversation"
                  disabled={busy}
                  onClick={() =>
                    active ? setDocMessages([]) : setMessages([])
                  }
                >
                  <Plus size={20} />
                </button>
              </div>
              <div className="chat-messages">
                {!chatMessages.length && (
                  <Empty
                    icon={Sparkles}
                    title={
                      active
                        ? "Ask the paper. Follow the evidence."
                        : "A good question changes everything."
                    }
                  >
                    {active
                      ? "Explore the methodology, results, and limitations. Local responses extract text; Gemini adds analysis when configured."
                      : "Ask about a research topic. The assistant retrieves real publications and labels its analysis. Connect an AI backend to begin."}
                  </Empty>
                )}
                {chatMessages.map((m, i) => (
                  <article className={`message ${m.role}`} key={i}>
                    <span className="message-label">
                      {m.role === "user"
                        ? "YOU"
                        : `SCIENTIA · ${modeLabel(m.mode)}`}
                    </span>
                    <TextOutput value={m.content} />
                    {m.sources?.length > 0 && (
                      <details>
                        <summary>{m.sources.length} supporting sources</summary>
                        <div className="source-list">
                          {m.sources.map((s, j) =>
                            typeof s === "string" ? (
                              <SourceEvidence
                                key={j}
                                source={s}
                                active={active}
                              />
                            ) : (
                              <a
                                key={j}
                                href={safeUrl(s.url)}
                                target="_blank"
                                rel="noreferrer"
                              >
                                [{j + 1}] {s.title}
                                <ArrowUpRight size={13} />
                              </a>
                            ),
                          )}
                        </div>
                      </details>
                    )}
                    {m.artifacts?.script && (
                      <details>
                        <summary>Briefing script</summary>
                        <TextOutput value={m.artifacts.script} />
                      </details>
                    )}
                    {m.artifacts?.repositories?.map((repo) => (
                      <a
                        className="text-button"
                        key={repo.html_url}
                        href={safeUrl(repo.html_url)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {repo.full_name}
                        <ArrowUpRight size={13} />
                      </a>
                    ))}
                    {m.artifacts?.code && (
                      <details>
                        <summary>Generated code</summary>
                        <pre>{m.artifacts.code}</pre>
                        <button
                          className="secondary-button"
                          onClick={() =>
                            download(
                              "research_scaffold.py",
                              m.artifacts.code,
                              "text/plain",
                            )
                          }
                        >
                          Download code
                        </button>
                      </details>
                    )}
                  </article>
                ))}
                {busy && (
                  <div className="thinking" role="status">
                    <span /> Finding the connections…
                  </div>
                )}
                <div ref={messageEnd} />
              </div>
              <div className="composer-area">
                {active && (
                  <label className="agent-select">
                    Research tool
                    <select
                      value={tool}
                      onChange={(e) => setTool(e.target.value)}
                    >
                      {[
                        ["rag", "Ask the document"],
                        ["research", "Paper analysis"],
                        ["math", "Equation explanation"],
                        ["code", "ML code scaffold"],
                        ["citation", "Citation analysis"],
                        ["github", "GitHub implementations"],
                        ["podcast", "Briefing script"],
                      ].map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <form className="composer" onSubmit={send}>
                  <textarea
                    aria-label="Research question"
                    placeholder="Ask a question. Explore a connection…"
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                    maxLength={4000}
                    rows={2}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        if (question.trim() && connected && !busy) send(e);
                      }
                    }}
                  />
                  <button
                    className="search-submit"
                    aria-label="Send research question"
                    disabled={busy || !question.trim() || !connected}
                  >
                    <Send size={18} />
                  </button>
                </form>
                <p className="composer-caption">
                  {!connected
                    ? "Connect the research API in Settings to start a conversation."
                    : "AI analysis may be inaccurate. Check original sources. Shift + Enter for a new line."}
                </p>
              </div>
            </div>
          )}

          {tab === "settings" && (
            <div className="content-page settings-page">
              <PageHeading
                eyebrow="MAKE IT YOUR WORKSPACE"
                title="Settings & connection"
                description="Transparent tools. Private credentials stay on the server."
              />
              <section className="output-card">
                <h2>Research API</h2>
                <p>
                  Paper discovery, bookmarks, notes, and citation exports work
                  directly on GitHub Pages. PDF processing and AI tools use a
                  separately hosted Flask API.
                </p>
                <label className="settings-label">
                  Configured endpoint
                  <code>
                    {API_BASE ||
                      (process.env.NODE_ENV === "development"
                        ? "Local development proxy → localhost:5000"
                        : "No backend configured")}
                  </code>
                </label>
                <div className="toolbar">
                  <span
                    className={`connection-badge ${connected ? "connected" : ""}`}
                  >
                    <i />
                    {connected
                      ? aiEnabled
                        ? "Gemini enabled"
                        : "Local extraction available"
                      : "Not connected"}
                  </span>
                  <button
                    className="secondary-button"
                    disabled={!backendConfigured}
                    onClick={() => run(connect)}
                  >
                    Check connection
                  </button>
                </div>
                <p>
                  Set the GitHub repository variable{" "}
                  <code>REACT_APP_API_URL</code> to the HTTPS backend origin,
                  then rerun the Pages deployment. Add the Pages origin to
                  backend <code>CORS_ORIGINS</code>. Configure{" "}
                  <code>GEMINI_API_KEY</code> only on the backend host.
                </p>
              </section>
              <section className="output-card">
                <h2>Your data</h2>
                <p>
                  Bookmarks, notes, searches, theme, and general conversations
                  are stored in this browser. Uploaded PDFs and document chats
                  live on the backend. The current backend is a shared research
                  demo, so use public documents only.
                </p>
                {status?.storage_mode === "ephemeral" && (
                  <p>
                    Free hosting uses temporary storage: uploaded PDFs and
                    document chats can disappear when the server sleeps or
                    restarts. Browser bookmarks and notes are separate and
                    remain on this device.
                  </p>
                )}
                <div className="toolbar">
                  <button
                    className="secondary-button"
                    onClick={() =>
                      download(
                        "scientia-workspace.json",
                        JSON.stringify(
                          { bookmarks, notes, history, messages },
                          null,
                          2,
                        ),
                        "application/json",
                      )
                    }
                  >
                    Export local workspace
                  </button>
                  <button
                    className="secondary-button"
                    onClick={() => {
                      if (
                        window.confirm(
                          "Clear this browser’s saved papers, notes, searches, and conversation?",
                        )
                      ) {
                        setBookmarks([]);
                        setNotes({});
                        setHistory([]);
                        setMessages([]);
                        setSelected([]);
                      }
                    }}
                  >
                    Clear local research data
                  </button>
                </div>
              </section>
              <section className="output-card">
                <h2>What the evidence can tell you</h2>
                <p>
                  Search metadata comes from Crossref. Abstracts and PDF links
                  depend on publisher availability. Citation formats are
                  editable drafts. Literature reviews use available abstracts
                  and flag missing datasets, metrics, and limitations. AI output
                  is analysis, and should be checked against the paper.
                </p>
              </section>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
function PageHeading({ eyebrow, title, description }) {
  return (
    <div className="page-heading">
      <span className="eyebrow">{eyebrow}</span>
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
  );
}

function modeLabel(mode) {
  if (mode === "gemini") return "AI ANALYSIS";
  if (mode?.includes("local")) return "LOCAL EXTRACTION / TEMPLATE";
  if (mode?.includes("metadata")) return "METADATA / RULE-BASED ANALYSIS";
  return "RESEARCH RESPONSE · VERIFY SOURCES";
}
function SourceEvidence({ source, active }) {
  const url = safeUrl(source);
  if (url)
    return (
      <a href={url} target="_blank" rel="noreferrer">
        {source}
        <ArrowUpRight size={13} />
      </a>
    );
  const page = source.match(/\| page (\d+) \|/)?.[1];
  return (
    <blockquote>
      {source}
      {page && active?.session_id && !active.session_id.includes(",") && (
        <a
          href={`${API_BASE}/api/documents/${encodeURIComponent(active.session_id)}/file#page=${page}`}
          target="_blank"
          rel="noreferrer"
        >
          Open source · page {page}
          <ArrowUpRight size={13} />
        </a>
      )}
    </blockquote>
  );
}
