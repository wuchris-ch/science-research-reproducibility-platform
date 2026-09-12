import React, { useState, useEffect, useCallback, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  BookOpen,
  FlaskConical,
  GitBranch,
  Play,
  Check,
  ArrowUpRight,
  Download,
  Plus,
  Search,
  FileText,
  Clock,
  ShieldCheck,
  ChevronRight,
  Square,
  History,
  Settings2,
  AlertCircle,
  ExternalLink,
  RefreshCw,
  Lock,
  Layers,
  ArrowLeft,
  MessageSquare,
  X,
  Users,
  PanelLeftClose,
  Menu,
} from "lucide-react";
import {
  api,
  session,
  asset,
  download,
  setToken,
  type Plan,
  type Run,
  type Source,
  type Workspace,
  type Parameters,
  type Event,
} from "./api";
import "./style.css";
import { SourceViewer, useDialog } from "./SourceViewer";
import { LibraryImports } from "./LibraryImports";
const defaults: Parameters = {
  filter_policy: "published",
  min_count: 10,
  min_total_count: 15,
  min_samples: 3,
  contrast: "BasalvsLP",
  fdr: 0.05,
  seed: 1,
};
const reviewFields = [
  "dataset",
  "samples",
  "filter",
  "environment",
  "comparison",
];
const friendly = (s: string) => s.replaceAll("_", " ").replaceAll(".", " · ");
const fmt = (n: unknown) =>
  typeof n === "number"
    ? n.toLocaleString(undefined, { maximumFractionDigits: 3 })
    : typeof n === "object"
      ? "View artifact"
      : String(n ?? "Unavailable");
const when = (n: number) =>
  new Date(n * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
function Badge({ value }: { value: string }) {
  return (
    <span className={"badge " + value}>
      <span />
      {friendly(value)}
    </span>
  );
}
function App() {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]),
    [workspaceId, setWorkspaceId] = useState(
      localStorage.getItem("workspace") || "",
    );
  const [plans, setPlans] = useState<Plan[]>([]),
    [runs, setRuns] = useState<Run[]>([]),
    [sources, setSources] = useState<Source[]>([]);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null),
    [selectedRun, setSelectedRun] = useState<string | null>(null),
    [source, setSource] = useState<Source | null>(null);
  const [section, setSection] = useState<
      "workbench" | "library" | "activity" | "team"
    >("workbench"),
    [tab, setTab] = useState("Overview"),
    [ready, setReady] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    [authRequired, setAuthRequired] = useState(false);
  const [events, setEvents] = useState<Event[]>([]),
    [modal, setModal] = useState<"new" | "variation" | "workspace" | null>(
      null,
    ),
    [mobile, setMobile] = useState(false);
  useDialog(Boolean(modal), () => setModal(null));
  const [identityMode, setIdentityMode] = useState("local");
  const [newDataset, setNewDataset] = useState("law2018");
  const activeWorkspace = useRef(workspaceId);
  activeWorkspace.current = workspaceId;
  const plan =
    plans.find(
      (p) => p.id === selectedPlan && p.workspace_id === workspaceId,
    ) || null;
  const run =
    runs.find((r) => r.id === selectedRun && r.workspace_id === workspaceId) ||
    runs.find((r) => r.plan_id === selectedPlan) ||
    null;
  const workspace = workspaces.find((w) => w.id === workspaceId);
  const refresh = useCallback(async () => {
    if (!workspaceId) return;
    const data = await api<{ plans: Plan[]; runs: Run[] }>(
      `/workspaces/${workspaceId}`,
    );
    if (activeWorkspace.current !== workspaceId) return;
    setPlans(data.plans);
    setRuns(data.runs);
    setEvents(await api<Event[]>(`/workspaces/${workspaceId}/events`));
  }, [workspaceId]);
  async function act(fn: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    session()
      .then(async (mode) => {
        setIdentityMode(mode);
        setSources(await api("/sources"));
        const list = await api<Workspace[]>("/workspaces");
        setWorkspaces(list);
        if (!list.some((w) => w.id === workspaceId))
          setWorkspaceId(list[0]?.id || "");
        setReady(true);
      })
      .catch((e) => {
        setError(e.message);
        setAuthRequired(true);
      });
  }, []);
  useEffect(() => {
    if (!workspaceId) return;
    localStorage.setItem("workspace", workspaceId);
    setSelectedPlan(localStorage.getItem("selected-plan:" + workspaceId));
    setSelectedRun(localStorage.getItem("selected-run:" + workspaceId));
    setTab(localStorage.getItem("selected-tab:" + workspaceId) || "Overview");
    refresh().catch((e) => setError(e.message));
    const id = setInterval(() => refresh().catch(() => {}), 2500);
    return () => clearInterval(id);
  }, [refresh]);
  useEffect(() => {
    if (plans.length && plans[0].workspace_id === workspaceId && !selectedPlan)
      setSelectedPlan(plans[plans.length - 1].id);
  }, [plans, selectedPlan, workspaceId]);
  useEffect(() => {
    if (!plan) return;
    localStorage.setItem("selected-plan:" + workspaceId, plan.id);
    localStorage.setItem("selected-tab:" + workspaceId, tab);
    if (run && run.plan_id === plan.id)
      localStorage.setItem("selected-run:" + workspaceId, run.id);
  }, [plan?.id, run?.id, tab, workspaceId]);
  useEffect(() => {
    let active = true;
    setSource(null);
    if (plan)
      api<Source>("/sources/" + plan.body.dataset_id)
        .then((value) => {
          if (active) setSource(value);
        })
        .catch((e) => {
          if (active) setError(e.message);
        });
    return () => {
      active = false;
    };
  }, [plan?.body.dataset_id]);
  useEffect(() => {
    if (run)
      api<Run>("/runs/" + run.id)
        .then((r) =>
          setRuns((prev) => prev.map((x) => (x.id === r.id ? r : x))),
        )
        .catch(() => {});
  }, [run?.id, tab]);
  const choose = (p: Plan) => {
    setSelectedPlan(p.id);
    setSelectedRun(null);
    setSection("workbench");
    setTab("Overview");
    setMobile(false);
  };
  async function start() {
    if (!plan) return;
    await act(async () => {
      const r = await api<Run>("/runs", { plan_id: plan.id, use_cache: false });
      setSelectedRun(r.id);
      setTab("Overview");
      await refresh();
    });
  }
  async function newWorkspace(name: string) {
    await act(async () => {
      const w = await api<{ id: string }>("/workspaces", { name });
      setWorkspaces(await api("/workspaces"));
      setWorkspaceId(w.id);
      setModal(null);
    });
  }
  if (authRequired)
    return (
      <div className="login">
        <div className="brand">
          <FlaskConical /> Research Workbench
        </div>
        <h1>Connect to your research workspace</h1>
        <p>
          This installation requires an OIDC access token issued for its
          configured audience.
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            setToken(new FormData(e.currentTarget).get("token") as string);
            location.reload();
          }}
        >
          <label>
            Access token
            <textarea name="token" required autoComplete="off" />
          </label>
          <button className="primary">Connect</button>
        </form>
        <p className="error">{error}</p>
      </div>
    );
  return (
    <div className="app">
      <a className="skip" href="#main">
        Skip to research workspace
      </a>
      <aside className={mobile ? "sidebar open" : "sidebar"}>
        <div className="brand">
          <span className="brand-icon">
            <FlaskConical size={21} />
          </span>
          <div>
            Research<span>WORKBENCH</span>
          </div>
          <button
            className="mobile-only icon"
            aria-label="Close navigation"
            onClick={() => setMobile(false)}
          >
            <X size={18} />
          </button>
        </div>
        <div className="workspace-switch">
          <span className="workspace-avatar">{workspace?.name[0] || "R"}</span>
          <select
            aria-label="Workspace"
            value={workspaceId}
            onChange={(e) => setWorkspaceId(e.target.value)}
          >
            {workspaces.map((w) => (
              <option key={w.id} value={w.id}>
                {w.name}
              </option>
            ))}
            {!workspaces.length && <option>No workspace</option>}
          </select>
          <button
            className="icon"
            title="New workspace"
            onClick={() => setModal("workspace")}
          >
            <Plus size={15} />
          </button>
        </div>
        <div className="nav-label">RESEARCH</div>
        <nav>
          {[
            ["workbench", "Workbench", FlaskConical],
            ["library", "Paper library", BookOpen],
            ["activity", "Activity", History],
            ["team", "Team & settings", Users],
          ].map(([key, label, Icon]) => (
            <button
              key={String(key)}
              className={section === key ? "nav active" : "nav"}
              onClick={() => {
                setSection(key as typeof section);
                setMobile(false);
              }}
            >
              {React.createElement(Icon as typeof FlaskConical, { size: 18 })}
              {String(label)}
              {key === "library" && (
                <span className="count">{sources.length}</span>
              )}
            </button>
          ))}
        </nav>
        <div className="nav-label projects-label">
          ANALYSES{" "}
          <button
            className="icon"
            aria-label="New analysis"
            onClick={() => setModal("new")}
            disabled={!workspaceId}
          >
            <Plus size={15} />
          </button>
        </div>
        <div className="analysis-nav">
          {plans.map((p) => (
            <button
              key={p.id}
              className={
                selectedPlan === p.id
                  ? "analysis-link selected"
                  : "analysis-link"
              }
              onClick={() => choose(p)}
            >
              <span className={"small-dot " + p.state} />
              <span>
                {p.body.title}
                <small>
                  {p.body.parent_id ? "Variation · " : ""}
                  {p.body.dataset_id === "law2018" ? "Law 2018" : "Chen 2016"}
                </small>
              </span>
            </button>
          ))}
          {!plans.length && (
            <p className="muted empty-nav">Your analyses will appear here.</p>
          )}
        </div>
        <div className="sidebar-bottom">
          <ShieldCheck size={17} />
          <div>
            Evidence stays connected
            <small>Reviewed methods. Traceable results.</small>
          </div>
        </div>
      </aside>
      <div className="body">
        <header>
          <button
            className="mobile-only icon"
            aria-label="Open navigation"
            onClick={() => setMobile(true)}
          >
            <Menu size={20} />
          </button>
          <div className="breadcrumb">
            {workspace?.name || "Your research"}
            <ChevronRight size={13} />
            <strong>
              {section === "workbench"
                ? "Workbench"
                : section === "library"
                  ? "Paper library"
                  : section === "team"
                    ? "Team & settings"
                    : "Activity"}
            </strong>
          </div>
          <div className="header-right">
            <span className="local-indicator" />{" "}
            {identityMode === "local" ? "Local workspace" : "Team workspace"}{" "}
            <span className="profile">RW</span>
          </div>
        </header>
        <main id="main">
          {error && (
            <div className="error-banner" role="alert">
              <AlertCircle size={17} />
              {error}
              <button
                className="icon"
                aria-label="Dismiss error"
                onClick={() => setError("")}
              >
                <X size={16} />
              </button>
            </div>
          )}
          {!ready ? (
            <div className="empty">
              <span className="spinner" />
              <h2>Opening your workspace</h2>
            </div>
          ) : !workspaceId ? (
            <div className="welcome">
              <div className="eyebrow">A CLEARER PATH FROM PAPER TO RESULT</div>
              <h1>
                Make research
                <br />
                reproducible.
              </h1>
              <p>
                Connect the paper, the method, and the evidence. Start with a
                verified RNA-seq workflow and inspect every step.
              </p>
              <button className="primary" onClick={() => setModal("workspace")}>
                <Plus size={17} />
                Create your workspace
              </button>
            </div>
          ) : section === "library" ? (
            <>
              <PageTitle
                eyebrow="YOUR EVIDENCE BASE"
                title="Paper library"
                description="Versioned sources with verified public datasets and curated computational methods."
              />
              <div className="paper-grid">
                {sources.map((s) => (
                  <article className="paper-card" key={s.id}>
                    <div className="paper-top">
                      <FileText size={26} />
                      <Badge value="source_verified" />
                    </div>
                    <p className="eyebrow">
                      {s.authors} · {s.year} · VERSION {s.version}
                    </p>
                    <h2>{s.title}</h2>
                    <div className="paper-meta">
                      <span>{s.accession}</span>
                      <span>Bulk RNA-seq</span>
                      <span>CC BY</span>
                    </div>
                    <p className="muted">
                      {s.id === "law2018"
                        ? "9 samples · 27,179 genes · Density + differential expression"
                        : "12 samples · 27,179 genes · MDS exploration"}
                    </p>
                    <button
                      onClick={() => {
                        setModal("new");
                        setSource(s);
                        setNewDataset(s.id);
                      }}
                    >
                      Start an analysis
                      <ArrowUpRight size={16} />
                    </button>
                    <a
                      href={"https://doi.org/" + s.doi}
                      target="_blank"
                      rel="noreferrer"
                    >
                      View publication <ExternalLink size={13} />
                    </a>
                  </article>
                ))}
              </div>
              {workspace && <LibraryImports workspace={workspace} act={act} />}
            </>
          ) : section === "activity" ? (
            <>
              <PageTitle
                eyebrow="THE RESEARCH RECORD"
                title="Workspace activity"
                description="A durable history of methods, execution, corrections, and review."
              />
              <EventList events={events} />
            </>
          ) : section === "team" ? (
            <Team workspace={workspace!} act={act} />
          ) : !plan ? (
            <div className="welcome">
              <div className="eyebrow">PAPER → METHOD → RESULT</div>
              <h1>
                Start with a question.
                <br />
                Keep the evidence.
              </h1>
              <p>
                Create an analysis from a verified paper, review its methods,
                and run a fresh reproduction.
              </p>
              <button className="primary" onClick={() => setModal("new")}>
                <Plus size={17} />
                New analysis
              </button>
            </div>
          ) : (
            <>
              <div className="title-row">
                <div>
                  <div className="eyebrow">
                    <span className="small-dot green" /> RNA-SEQ REPRODUCTION{" "}
                    <span className="subtle">
                      / ANALYSIS {plan.id.slice(0, 6).toUpperCase()}
                    </span>
                  </div>
                  <h1>{plan.body.title}</h1>
                  <p className="subtitle">
                    {source?.authors} · {source?.year} <span>·</span>{" "}
                    {source?.accession} <span>·</span>{" "}
                    {plan.body.recipe === "density"
                      ? "Figure 1 · Expression filtering"
                      : plan.body.recipe === "mds"
                        ? "Figure 1 · Sample relationships"
                        : "Differential expression · " +
                          plan.body.parameters.contrast}
                  </p>
                </div>
                <div className="actions">
                  <button
                    disabled={plan.state !== "locked" || busy}
                    onClick={() => setModal("variation")}
                  >
                    <GitBranch size={16} />
                    Create variation
                  </button>
                  {run?.state === "running" ||
                  run?.state === "queued" ||
                  run?.state === "cancel_requested" ? (
                    <button
                      className="primary"
                      disabled={busy || run.state === "cancel_requested"}
                      onClick={() =>
                        act(async () => {
                          await api("/runs/" + run.id + "/cancel", {});
                          await refresh();
                        })
                      }
                    >
                      <Square size={14} />
                      {run.state === "cancel_requested"
                        ? "Stopping…"
                        : "Stop run"}
                    </button>
                  ) : (
                    <button
                      className="primary"
                      disabled={plan.state !== "locked" || busy}
                      onClick={start}
                    >
                      <Play size={15} />
                      {run ? "Run again" : "Run analysis"}
                    </button>
                  )}
                </div>
              </div>
              <div className="status-strip">
                <span>
                  <Lock size={14} />
                  {plan.state === "locked"
                    ? "Methods locked"
                    : "Methods need review"}{" "}
                  · revision {plan.revision}
                </span>
                {run && (
                  <>
                    <span className="strip-divider" />
                    <Badge value={run.state} />
                    <span className="mono">{run.id.slice(0, 8)}</span>
                    {run.body.duration_seconds && (
                      <span className="muted">
                        <Clock size={13} />
                        {Math.round(run.body.duration_seconds)} sec
                      </span>
                    )}
                  </>
                )}
                <span className="strip-spacer" />
                <span className="muted">
                  {run?.body.cached_from
                    ? "Saved execution reused"
                    : "Fresh execution · cache off"}
                </span>
              </div>
              <div className="tabs" role="tablist">
                {[
                  "Overview",
                  "Methods",
                  "Results",
                  "Lineage",
                  "Run history",
                ].map((t) => (
                  <button
                    role="tab"
                    aria-selected={tab === t}
                    key={t}
                    className={tab === t ? "active" : ""}
                    onClick={() => setTab(t)}
                  >
                    {t}
                    {t === "Methods" && plan.state === "draft" && (
                      <span className="tab-dot" />
                    )}
                  </button>
                ))}
              </div>
              {tab === "Overview" ? (
                <Overview
                  plan={plan}
                  run={run}
                  source={source}
                  review={() => setTab("Methods")}
                  results={() => setTab("Results")}
                  setError={setError}
                />
              ) : tab === "Methods" ? (
                <Methods
                  key={plan.id + ":" + plan.revision}
                  plan={plan}
                  source={source}
                  busy={busy}
                  act={act}
                  refresh={refresh}
                />
              ) : tab === "Results" ? (
                <Results
                  run={run}
                  setError={setError}
                  act={act}
                  refresh={refresh}
                />
              ) : tab === "Lineage" ? (
                <Lineage plan={plan} run={run} plans={plans} choose={choose} />
              ) : (
                <RunHistory
                  runs={runs.filter((r) => r.plan_id === plan.id)}
                  choose={(r) => {
                    setSelectedRun(r.id);
                    setTab("Results");
                  }}
                />
              )}
            </>
          )}
        </main>
        <footer>
          Research Workbench{" "}
          <span>Computational evidence, open to inspection.</span>
        </footer>
      </div>
      {modal && (
        <div
          className="modal-backdrop"
          onMouseDown={(e) => {
            if (e.target === e.currentTarget) setModal(null);
          }}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
            className="modal"
          >
            <button
              className="icon close"
              aria-label="Close dialog"
              onClick={() => setModal(null)}
            >
              <X size={19} />
            </button>
            {modal === "workspace" ? (
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  newWorkspace(
                    new FormData(e.currentTarget).get("name") as string,
                  );
                }}
              >
                <div className="eyebrow">A PLACE FOR YOUR RESEARCH</div>
                <h2 id="modal-title">Create a workspace</h2>
                <label>
                  Workspace name
                  <input
                    autoFocus
                    name="name"
                    required
                    maxLength={120}
                    placeholder="Mammary transcriptomics"
                  />
                </label>
                <button className="primary" disabled={busy}>
                  Create workspace
                </button>
              </form>
            ) : (
              <NewPlan
                sources={sources}
                initialDataset={newDataset}
                workspaceId={workspaceId}
                parent={modal === "variation" ? plan : null}
                busy={busy}
                onCreate={(body) =>
                  act(async () => {
                    const p = await api<Plan>("/plans", body);
                    await refresh();
                    choose(p);
                    setModal(null);
                    setTab("Methods");
                  })
                }
              />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
function PageTitle({
  eyebrow,
  title,
  description,
}: {
  eyebrow: string;
  title: string;
  description: string;
}) {
  return (
    <div className="page-title">
      <div className="eyebrow">{eyebrow}</div>
      <h1>{title}</h1>
      <p className="subtitle">{description}</p>
    </div>
  );
}
function ImageAsset({
  path,
  alt,
  className = "",
}: {
  path: string;
  alt: string;
  className?: string;
}) {
  const [url, setUrl] = useState("");
  useEffect(() => {
    let current = "";
    let active = true;
    asset(path)
      .then((u) => {
        current = u;
        if (active) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch(() => setUrl(""));
    return () => {
      active = false;
      if (current) URL.revokeObjectURL(current);
    };
  }, [path]);
  return url ? (
    <img className={className} src={url} alt={alt} />
  ) : (
    <div className="image-placeholder">
      <FileText size={25} />
      <span>Figure unavailable</span>
    </div>
  );
}
function Overview({
  plan,
  run,
  source,
  review,
  results,
  setError,
}: {
  plan: Plan;
  run: Run | null;
  source: Source | null;
  review: () => void;
  results: () => void;
  setError: (s: string) => void;
}) {
  const [showSource, setShowSource] = useState(false);
  const c = run?.body.comparison,
    m = c?.metrics;
  return (
    <div className="overview">
      <div className="stats-grid">
        <Stat
          label="INPUT GENES"
          value={m ? fmt(m.input_genes) : "27,179"}
          note="Pinned public count matrix"
          icon={<Layers size={17} />}
        />
        <Stat
          label="SAMPLES"
          value={plan.body.dataset_id === "law2018" ? "9" : "12"}
          note={
            plan.body.dataset_id === "law2018"
              ? "3 cell populations · 3 replicates"
              : "2 cell types · 3 biological states"
          }
          icon={<FlaskConical size={17} />}
        />
        <Stat
          label="RETAINED GENES"
          value={m ? fmt(m.retained_genes) : "Awaiting run"}
          note={
            m
              ? `${((Number(m.retained_genes) / Number(m.input_genes)) * 100).toFixed(1)}% of the input universe`
              : "Determined by the reviewed filter"
          }
          icon={<Settings2 size={17} />}
        />
        <Stat
          label="COMPARISON"
          value={
            c
              ? c.status === "checks_match"
                ? "Checks match"
                : "Mismatch"
              : "Not evaluated"
          }
          note={
            c
              ? `${c.checks.filter((x) => x.passed).length} of ${c.checks.length} checked observables match`
              : "Execution and comparison are separate"
          }
          icon={<ShieldCheck size={17} />}
        />
      </div>
      <div className="split">
        <section className="card source-card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">01 / SOURCE</span>
              <h2>
                {plan.body.recipe === "differential"
                  ? "Published filtering reference"
                  : "The published result"}
              </h2>
            </div>
            <span className="pill">VERSION {source?.version || "–"}</span>
          </div>
          <div className="figure-area">
            <ImageAsset
              path={"/sources/" + plan.body.dataset_id + "/asset/figure"}
              alt="Published Figure 1 from the source paper"
            />
          </div>
          <div className="source-caption">
            <h3>
              {plan.body.dataset_id === "law2018"
                ? "Figure 1. Expression before and after filtering"
                : "Figure 1. Sample relationships"}
            </h3>
            <p>
              {plan.body.dataset_id === "law2018"
                ? "Density of log-CPM values in the raw and filtered data. Dotted lines mark the expression threshold."
                : "Multidimensional scaling of expression profiles across cell types and biological states."}
            </p>
            <div className="source-citation">
              <FileText size={14} />
              {source?.authors}, {source?.year} ·{" "}
              {source?.geometry
                ? "Page " + source.geometry.page
                : "Versioned source"}
              <button
                className="text-button"
                onClick={() => setShowSource(true)}
              >
                Open paper
                <ArrowUpRight size={14} />
              </button>
            </div>
          </div>
        </section>
        <section className="card result-card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">02 / REPRODUCTION</span>
              <h2>Your computed result</h2>
            </div>
            {run && <Badge value={run.state} />}
          </div>
          {run?.state === "succeeded" ? (
            <>
              <div className="figure-area">
                <ImageAsset
                  path={"/runs/" + run.id + "/artifacts/figure.png"}
                  alt="Figure produced by the selected scientific execution"
                />
              </div>
              <div className="result-caption">
                <div className="result-message">
                  <span className="check-circle">
                    <Check size={17} />
                  </span>
                  <div>
                    <h3>
                      {c?.status === "checks_match"
                        ? "Checked observables agree"
                        : "A discrepancy needs review"}
                    </h3>
                    <p>
                      {c?.status === "checks_match"
                        ? "The declared numerical checks match their references."
                        : "Execution completed. Inspect the numerical differences below."}
                    </p>
                  </div>
                </div>
                <button className="text-button" onClick={results}>
                  Inspect results and limitations
                  <ArrowUpRight size={15} />
                </button>
              </div>
            </>
          ) : (
            <div className="run-empty">
              {run?.state === "running" || run?.state === "queued" ? (
                <>
                  <span className="spinner" />
                  <h3>
                    {run.state === "queued"
                      ? "Queued for execution"
                      : "Scientific analysis is running"}
                  </h3>
                  <p>
                    Real progress appears as the worker completes each stage.
                    You can return to this run at any time.
                  </p>
                </>
              ) : run?.state === "failed" ? (
                <>
                  <AlertCircle size={35} />
                  <h3>Execution needs attention</h3>
                  <p>{run.body.diagnostic}</p>
                  <button onClick={results}>Inspect diagnostics</button>
                </>
              ) : (
                <>
                  <div className="empty-icon">
                    <FlaskConical size={32} />
                  </div>
                  <h3>
                    {plan.state === "draft"
                      ? "Review the method to begin"
                      : "Ready for a fresh execution"}
                  </h3>
                  <p>
                    {plan.state === "draft"
                      ? "Check the source, sample mapping, and filtering choices. Lock the plan when you are ready."
                      : "The reviewed plan is locked. Run the analysis to generate a traceable result."}
                  </p>
                  {plan.state === "draft" && (
                    <button onClick={review}>
                      Review methods
                      <ChevronRight size={15} />
                    </button>
                  )}
                </>
              )}
            </div>
          )}
        </section>
      </div>
      <div className="lower-grid">
        <section className="card workflow-card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">THE METHOD</span>
              <h2>Every step, connected</h2>
            </div>
            <button className="text-button" onClick={review}>
              View method
              <ArrowUpRight size={15} />
            </button>
          </div>
          <div className="workflow">
            {[
              ["01", "Count matrix", "GEO · " + (source?.accession || "")],
              [
                "02",
                "Expression filter",
                plan.body.parameters.filter_policy === "published"
                  ? "Published policy"
                  : "CPM > 1 variation",
              ],
              [
                "03",
                plan.body.recipe === "density"
                  ? "Log-CPM density"
                  : plan.body.recipe === "mds"
                    ? "TMM + MDS"
                    : "TMM + voom",
                "Curated R recipe",
              ],
              ["04", "Compare & review", "Sealed artifacts"],
            ].map(([n, title, note], i) => (
              <React.Fragment key={n}>
                <div className="workflow-step">
                  <span>{n}</span>
                  <h3>{title}</h3>
                  <p>{note}</p>
                </div>
                {i < 3 && <ChevronRight size={16} />}
              </React.Fragment>
            ))}
          </div>
        </section>
        <section className="note-card">
          <div>
            <ShieldCheck size={19} />
            <h3>Know what this result establishes</h3>
          </div>
          <p>
            Matching counts is one piece of evidence. The paper has no numerical
            density grid for an exact curve comparison, and a successful run
            does not validate every scientific conclusion.
          </p>
          <button className="text-button" onClick={results}>
            Read the comparison limits
            <ArrowUpRight size={14} />
          </button>
        </section>
      </div>
      {showSource && source && (
        <SourceViewer source={source} close={() => setShowSource(false)} />
      )}
    </div>
  );
}
function Stat({
  label,
  value,
  note,
  icon,
}: {
  label: string;
  value: string;
  note: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="stat">
      <div>
        {label}
        {icon}
      </div>
      <strong>{value}</strong>
      <p>{note}</p>
    </div>
  );
}
function NewPlan({
  sources,
  initialDataset,
  workspaceId,
  parent,
  busy,
  onCreate,
}: {
  sources: Source[];
  initialDataset: string;
  workspaceId: string;
  parent: Plan | null;
  busy: boolean;
  onCreate: (b: unknown) => void;
}) {
  const [dataset, setDataset] = useState(parent?.body.dataset_id || "law2018");
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        const f = new FormData(e.currentTarget);
        onCreate({
          workspace_id: workspaceId,
          title: f.get("title"),
          dataset_id: dataset,
          recipe: parent?.body.recipe || f.get("recipe"),
          parameters: parent
            ? {
                ...parent.body.parameters,
                filter_policy:
                  parent.body.parameters.filter_policy === "published"
                    ? "cpm1"
                    : "published",
              }
            : { ...defaults, min_samples: dataset === "chen2016" ? 2 : 3 },
          parent_id: parent?.id || null,
          reason: f.get("reason") || "",
        });
      }}
    >
      <div className="eyebrow">
        {parent ? "A CONTROLLED CHANGE" : "CONNECT PAPER AND RESULT"}
      </div>
      <h2 id="modal-title">{parent ? "Create a variation" : "New analysis"}</h2>
      <p className="muted">
        {parent
          ? "Start a new reviewable plan with one changed filtering policy. The original plan and every run remain available."
          : "Choose a source-backed workflow. You will review its methods before execution."}
      </p>
      <label>
        Analysis title
        <input
          name="title"
          required
          autoFocus
          maxLength={160}
          defaultValue={parent ? "Stricter expression filter" : ""}
          placeholder="Figure 1: expression filtering"
        />
      </label>
      {!parent && (
        <>
          <label>
            Source paper
            <select
              value={dataset}
              onChange={(e) => setDataset(e.target.value)}
            >
              {sources.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.authors} · {s.year} · {s.accession}
                </option>
              ))}
            </select>
          </label>
          <label>
            Workflow
            <select name="recipe" key={dataset}>
              {dataset === "law2018" ? (
                <>
                  <option value="density">Figure 1: log-CPM density</option>
                  <option value="differential">
                    Differential expression: TMM + voom
                  </option>
                </>
              ) : (
                <option value="mds">Figure 1: MDS sample relationships</option>
              )}
            </select>
          </label>
        </>
      )}
      {parent && (
        <>
          <div className="change-preview">
            <span>
              {parent.body.parameters.filter_policy === "published"
                ? "Published filter"
                : "CPM > 1"}
            </span>
            <ChevronRight size={16} />
            <strong>
              {parent.body.parameters.filter_policy === "published"
                ? "CPM > 1"
                : "Published filter"}
            </strong>
          </div>
          <label>
            Reason for the change
            <textarea
              name="reason"
              required
              minLength={3}
              defaultValue="Test whether the result is sensitive to a stricter expression threshold."
            />
          </label>
        </>
      )}
      <button className="primary" disabled={busy}>
        {parent ? <GitBranch size={16} /> : <Plus size={16} />}Create{" "}
        {parent ? "variation" : "analysis"}
      </button>
    </form>
  );
}
function Methods({
  plan,
  source,
  busy,
  act,
  refresh,
}: {
  plan: Plan;
  source: Source | null;
  busy: boolean;
  act: (f: () => Promise<void>) => void;
  refresh: () => Promise<void>;
}) {
  const [parameters, setParameters] = useState<Parameters>(
      plan.body.parameters,
    ),
    [checked, setChecked] = useState<string[]>([]),
    [reason, setReason] = useState(""),
    [search, setSearch] = useState(""),
    [evidence, setEvidence] = useState<string[]>([]),
    [proposals, setProposals] = useState<{
      fields: {
        key: string;
        value: unknown;
        origin: string;
        evidence_ids: string[];
        explanation: string;
      }[];
    } | null>(null);
  const draft = plan.state === "draft",
    chen = plan.body.dataset_id === "chen2016",
    changed =
      JSON.stringify(parameters) !== JSON.stringify(plan.body.parameters);
  const passages =
    source?.segments
      .filter(
        (s) =>
          s.kind === "p" &&
          (search
            ? s.text.toLowerCase().includes(search.toLowerCase())
            : [
                chen ? "chen2016:37" : "law2018:49",
                "law2018:50",
                "law2018:9",
                "law2018:76",
              ].includes(s.id)),
      )
      .slice(0, 30) || [];
  return (
    <div className="methods-layout">
      <section className="card method-editor">
        <div className="card-heading">
          <div>
            <span className="eyebrow">REVIEWABLE, VERSIONED METHODS</span>
            <h2>
              {draft ? "Review your analysis plan" : "Locked analysis plan"}
            </h2>
          </div>
          <Badge value={plan.state} />
        </div>
        <div className="card-content">
          <div className="method-section">
            <h3>
              <span>01</span>Dataset & samples
            </h3>
            <p>
              <strong>{source?.accession}</strong> ·{" "}
              {chen
                ? "12 mouse mammary samples, six groups with two replicates"
                : "9 mouse mammary samples, three groups with three replicates"}
            </p>
            <p className="muted">
              {chen
                ? "Basal and luminal cells across virgin, pregnant and lactating states. Original gene-symbol availability filter is retained."
                : "LP, ML and Basal. Sequencing lanes L004, L006 and L008 follow the paper mapping. All sample checksums are verified."}
            </p>
            <code className="digest">
              Source SHA-256: {plan.body.source_sha256}
            </code>
          </div>
          <div className="method-section">
            <h3>
              <span>02</span>Expression filtering
            </h3>
            <label>
              Filtering policy
              <select
                disabled={!draft}
                value={parameters.filter_policy}
                onChange={(e) =>
                  setParameters({
                    ...parameters,
                    filter_policy: e.target
                      .value as Parameters["filter_policy"],
                  })
                }
              >
                <option value="published">
                  Published method{" "}
                  {chen
                    ? "(CPM > 0.5 in 2 samples)"
                    : "(approximately 10 counts)"}
                </option>
                <option value="cpm1">Controlled variation: CPM &gt; 1</option>
              </select>
            </label>
            <div className="field-grid">
              <label>
                Minimum samples
                <input
                  type="number"
                  min={2}
                  max={chen ? 2 : 9}
                  disabled={!draft || chen}
                  value={parameters.min_samples}
                  onChange={(e) =>
                    setParameters({
                      ...parameters,
                      min_samples: Number(e.target.value),
                    })
                  }
                />
              </label>
              {!chen && (
                <>
                  <label>
                    Minimum count
                    <input
                      type="number"
                      min={1}
                      max={100}
                      disabled={!draft || parameters.filter_policy === "cpm1"}
                      value={parameters.min_count}
                      onChange={(e) =>
                        setParameters({
                          ...parameters,
                          min_count: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                  <label>
                    Minimum total count
                    <input
                      type="number"
                      min={1}
                      max={1000}
                      disabled={!draft || parameters.filter_policy === "cpm1"}
                      value={parameters.min_total_count}
                      onChange={(e) =>
                        setParameters({
                          ...parameters,
                          min_total_count: Number(e.target.value),
                        })
                      }
                    />
                  </label>
                </>
              )}
            </div>
            <p className="field-hint">
              {chen
                ? "The published Chen filter is fixed at two samples. Count-based fields do not apply."
                : "Minimum count and total count apply to the published filtering policy. Library sizes are recalculated after filtering."}
            </p>
          </div>
          {plan.body.recipe === "differential" && (
            <div className="method-section">
              <h3>
                <span>03</span>Differential expression
              </h3>
              <p>
                <code>~0+group+lane</code> · TMM · voom · empirical Bayes
              </p>
              <div className="field-grid">
                <label>
                  Contrast
                  <select
                    disabled={!draft}
                    value={parameters.contrast}
                    onChange={(e) =>
                      setParameters({
                        ...parameters,
                        contrast: e.target.value as Parameters["contrast"],
                      })
                    }
                  >
                    {["BasalvsLP", "BasalvsML", "LPvsML"].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </label>
                <label>
                  FDR threshold
                  <input
                    disabled={!draft}
                    type="number"
                    min={0.001}
                    max={0.2}
                    step={0.001}
                    value={parameters.fdr}
                    onChange={(e) =>
                      setParameters({
                        ...parameters,
                        fdr: Number(e.target.value),
                      })
                    }
                  />
                </label>
              </div>
              <p className="field-hint">
                Benjamini-Hochberg across all tested genes for the selected
                contrast. This workflow uses the paper's eBayes analysis; its
                later TREAT test is a separate method.
              </p>
            </div>
          )}
          <div className="method-section">
            <h3>
              <span>{plan.body.recipe === "differential" ? "04" : "03"}</span>
              Environment & comparison
            </h3>
            <p>{plan.body.environment}</p>
            {plan.body.adaptations.map((a) => (
              <p className="field-hint" key={a}>
                {a}
              </p>
            ))}
            <p className="field-hint">
              Exact scalar checks are separated from unavailable paper-level
              curve or gene-table references. Every run records its immutable
              image identity.
            </p>
          </div>
          {draft && (
            <>
              {changed ? (
                <div className="save-change">
                  <label>
                    Reason for correction
                    <textarea
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      placeholder="Explain the method correction and the evidence supporting it."
                      minLength={3}
                    />
                  </label>
                  <p className="field-hint">
                    {evidence.length} source passages selected. Saving creates
                    revision {plan.revision + 1}.
                  </p>
                  <button
                    className="primary"
                    disabled={busy || reason.trim().length < 3}
                    onClick={() =>
                      act(async () => {
                        await api("/plans/" + plan.id + "/correct", {
                          expected_revision: plan.revision,
                          parameters,
                          reason,
                          evidence_ids: evidence,
                        });
                        await refresh();
                      })
                    }
                  >
                    Save method correction
                  </button>
                </div>
              ) : (
                <div className="review-checklist">
                  <h3>Review before locking</h3>
                  <p className="muted">
                    Confirm each part against the source and declared
                    limitations.
                  </p>
                  {reviewFields.map((k) => (
                    <label className="checkbox-label" key={k}>
                      <input
                        type="checkbox"
                        checked={checked.includes(k)}
                        onChange={(e) =>
                          setChecked(
                            e.target.checked
                              ? [...checked, k]
                              : checked.filter((x) => x !== k),
                          )
                        }
                      />
                      <span>
                        I reviewed the {k}
                        {k === "comparison" ? " limits" : ""}
                      </span>
                    </label>
                  ))}
                  <button
                    className="primary"
                    disabled={busy || checked.length !== 5}
                    onClick={() =>
                      act(async () => {
                        await api("/plans/" + plan.id + "/lock", {
                          expected_revision: plan.revision,
                          reviewed_fields: checked,
                        });
                        await refresh();
                      })
                    }
                  >
                    <Lock size={16} />
                    Lock reviewed plan
                  </button>
                </div>
              )}
            </>
          )}
          {!draft && (
            <div className="locked-note">
              <ShieldCheck size={19} />
              <div>
                <strong>This plan is immutable.</strong>
                <p>
                  Create a variation to change a method while preserving its
                  evidence trail.
                </p>
              </div>
            </div>
          )}
        </div>
      </section>
      <aside className="evidence-panel">
        <div className="card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">SOURCE EVIDENCE</span>
              <h2>Read the method in context</h2>
            </div>
            <BookOpen size={20} />
          </div>
          <div className="card-content">
            <div className="search-field">
              <Search size={16} />
              <input
                aria-label="Search source passages"
                placeholder="Search the paper…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            {passages.map((p) => (
              <article
                className={
                  evidence.includes(p.id) ? "passage chosen" : "passage"
                }
                key={p.id}
              >
                <div>
                  <span>{p.id}</span>
                  {draft && (
                    <button
                      className="text-button"
                      onClick={() =>
                        setEvidence(
                          evidence.includes(p.id)
                            ? evidence.filter((x) => x !== p.id)
                            : [...evidence, p.id],
                        )
                      }
                    >
                      {evidence.includes(p.id) ? "Selected" : "Cite passage"}
                      {evidence.includes(p.id) && <Check size={12} />}
                    </button>
                  )}
                </div>
                <p>{p.text}</p>
              </article>
            ))}
            {!passages.length && (
              <p className="muted">
                No matching passages. Try a method term such as “filter” or
                “design”.
              </p>
            )}
            <a
              className="source-link"
              href={"https://doi.org/" + source?.doi}
              target="_blank"
              rel="noreferrer"
            >
              Open the complete publication
              <ExternalLink size={14} />
            </a>
          </div>
        </div>
        <div className="card assistance">
          <h3>Optional extraction assistance</h3>
          <p className="muted">
            Suggestions stay separate from the reviewed plan. Exact source
            matches still need contextual review.
          </p>
          <div className="actions">
            <button
              disabled={busy}
              onClick={() =>
                act(async () =>
                  setProposals(
                    await api("/workspaces/" + plan.workspace_id + "/extract", {
                      dataset_id: plan.body.dataset_id,
                      mode: "lexical",
                    }),
                  ),
                )
              }
            >
              Find source matches
            </button>
            <button
              disabled={busy}
              onClick={() =>
                act(async () =>
                  setProposals(
                    await api("/workspaces/" + plan.workspace_id + "/extract", {
                      dataset_id: plan.body.dataset_id,
                      mode: "model",
                    }),
                  ),
                )
              }
            >
              Ask configured model
            </button>
          </div>
          {proposals && (
            <div className="proposals">
              {proposals.fields.map((f) => (
                <div key={f.key}>
                  <Badge value={f.origin} />
                  <strong>{friendly(f.key)}</strong>
                  <p>{fmt(f.value)}</p>
                  <small>{f.explanation}</small>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
function Results({
  run,
  setError,
  act,
  refresh,
}: {
  run: Run | null;
  setError: (s: string) => void;
  act: (f: () => Promise<void>) => void;
  refresh: () => Promise<void>;
}) {
  const [text, setText] = useState(""),
    [selected, setSelected] = useState(""),
    [review, setReview] = useState("accepted_with_limits"),
    [note, setNote] = useState("");
  async function inspect(name: string) {
    if (!run) return;
    setSelected(name);
    try {
      const u = await asset("/runs/" + run.id + "/artifacts/" + name);
      const t = await fetch(u).then((r) => r.text());
      URL.revokeObjectURL(u);
      setText(t.slice(0, 80000));
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (!run)
    return (
      <div className="empty">
        <FlaskConical size={32} />
        <h2>No execution yet</h2>
        <p>Review and lock the method, then run the analysis.</p>
      </div>
    );
  const comparison = run.body.comparison;
  return (
    <div className="results">
      <div className="results-top">
        <div>
          <h2>
            Execution <code>{run.id.slice(0, 8)}</code>
          </h2>
          <Badge value={run.state} />
          {comparison && <Badge value={comparison.status} />}
        </div>
        <button
          disabled={!["succeeded", "failed", "cancelled"].includes(run.state)}
          onClick={() =>
            download(
              "/runs/" + run.id + "/export",
              "research-" + run.id.slice(0, 8) + ".zip",
            ).catch((e) => setError(e.message))
          }
        >
          <Download size={16} />
          Export reproducibility bundle
        </button>
      </div>
      {run.body.diagnostic && (
        <div className="diagnostic">
          <AlertCircle size={19} />
          {run.body.diagnostic}
        </div>
      )}
      {comparison && (
        <>
          <div className="card">
            <div className="card-heading">
              <div>
                <span className="eyebrow">NUMERICAL EVIDENCE</span>
                <h2>Declared observable checks</h2>
              </div>
              <span className="muted">
                Execution success is a separate outcome
              </span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Observable</th>
                    <th>Reference</th>
                    <th>Computed</th>
                    <th>Result</th>
                    <th>Reference basis</th>
                  </tr>
                </thead>
                <tbody>
                  {comparison.checks.map((c) => (
                    <tr key={c.key}>
                      <td>{friendly(c.key)}</td>
                      <td>{fmt(c.expected)}</td>
                      <td>{fmt(c.actual)}</td>
                      <td>
                        <Badge value={c.passed ? "match" : "mismatch"} />
                      </td>
                      <td className="muted">{c.basis}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
          <div className="limits">
            <ShieldCheck size={20} />
            <div>
              <h3>Limits of this comparison</h3>
              {comparison.limitations.map((l) => (
                <p key={l}>{l}</p>
              ))}
            </div>
          </div>
        </>
      )}
      <div className="result-detail-grid">
        <section className="card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">INSPECTABLE OUTPUTS</span>
              <h2>Artifacts & provenance</h2>
            </div>
          </div>
          <div className="artifacts">
            {Object.entries(run.body.artifacts).map(([name, item]) => (
              <div className="artifact" key={name}>
                <FileText size={18} />
                <button
                  className="text-button"
                  onClick={() =>
                    name.endsWith(".png")
                      ? download(
                          "/runs/" + run.id + "/artifacts/" + name,
                          name,
                        ).catch((e) => setError(e.message))
                      : inspect(name)
                  }
                >
                  {name}
                </button>
                <span>{(item.bytes / 1024).toFixed(1)} KB</span>
                <code title={item.sha256}>{item.sha256.slice(0, 12)}</code>
                <button
                  className="icon"
                  title={"Download " + name}
                  onClick={() =>
                    download(
                      "/runs/" + run.id + "/artifacts/" + name,
                      name,
                    ).catch((e) => setError(e.message))
                  }
                >
                  <Download size={14} />
                </button>
              </div>
            ))}
            {!Object.keys(run.body.artifacts).length && (
              <p className="muted">
                Artifacts appear after the worker seals the completed output.
              </p>
            )}
          </div>
          <div className="runtime-detail">
            <strong>Executed environment</strong>
            <code>{run.body.image_id}</code>
            <p>
              Attempt {run.epoch} · {when(run.created)}
            </p>
          </div>
        </section>
        <section className="card">
          <div className="card-heading">
            <div>
              <span className="eyebrow">SCIENTIFIC REVIEW</span>
              <h2>Record your interpretation</h2>
            </div>
            <MessageSquare size={19} />
          </div>
          <div className="card-content">
            <p className="muted">
              A review is an attributable interpretation of this run. It does
              not overwrite the execution or comparison.
            </p>
            <label>
              Review decision
              <select
                value={review}
                onChange={(e) => setReview(e.target.value)}
              >
                <option value="accepted_with_limits">
                  Accept with stated limits
                </option>
                <option value="disputed">Dispute the result</option>
              </select>
            </label>
            <label>
              Evidence and limitations
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Describe what you checked, what agrees, and what remains uncertain."
              />
            </label>
            <button
              disabled={run.state !== "succeeded" || note.trim().length < 3}
              onClick={() =>
                act(async () => {
                  await api("/runs/" + run.id + "/reviews", {
                    status: review,
                    note,
                  });
                  setNote("");
                  await refresh();
                })
              }
            >
              Save review
            </button>
            {run.reviews?.map((r, i) => (
              <div className="review-entry" key={i}>
                <Badge value={r.body.status} />
                <p>{r.body.note}</p>
                <small>
                  {r.actor} · {when(r.created)}
                </small>
              </div>
            ))}
          </div>
        </section>
      </div>
      {selected && (
        <section className="card artifact-view">
          <div className="card-heading">
            <h2>{selected}</h2>
            <button
              className="icon"
              aria-label="Close artifact"
              onClick={() => setSelected("")}
            >
              <X size={18} />
            </button>
          </div>
          <pre>{text}</pre>
          {text.length === 80000 && (
            <p>
              Preview limited to 80,000 characters. Download the complete
              artifact above.
            </p>
          )}
        </section>
      )}
    </div>
  );
}
function Lineage({
  plan,
  run,
  plans,
  choose,
}: {
  plan: Plan;
  run: Run | null;
  plans: Plan[];
  choose: (p: Plan) => void;
}) {
  const parent = plans.find((p) => p.id === plan.body.parent_id);
  const children = plans.filter((p) => p.body.parent_id === plan.id);
  return (
    <div className="lineage">
      <div className="card">
        <div className="card-heading">
          <div>
            <span className="eyebrow">AN UNBROKEN EVIDENCE TRAIL</span>
            <h2>From source to interpretation</h2>
          </div>
          <GitBranch size={23} />
        </div>
        <div className="lineage-path">
          {[
            ["Versioned paper", plan.body.dataset_id, plan.body.source_sha256],
            [
              "Locked method",
              plan.body.title,
              plan.body.plan_hash || "Review pending",
            ],
            [
              "Scientific execution",
              run ? friendly(run.state) : "No execution",
              run?.body.image_id || "Image identity captured on submission",
            ],
            [
              "Sealed result",
              run
                ? Object.keys(run.body.artifacts).length + " artifacts"
                : "Awaiting execution",
              run?.id || "",
            ],
          ].map(([label, title, hash], i) => (
            <div key={label} className="lineage-node">
              <span>{i + 1}</span>
              <div>
                <small>{label}</small>
                <h3>{title}</h3>
                <code>{hash}</code>
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className="card variation-tree">
        <h2>Controlled variations</h2>
        {parent && (
          <>
            <p className="eyebrow">PARENT ANALYSIS</p>
            <button onClick={() => choose(parent)}>
              <ArrowLeft size={15} />
              {parent.body.title}
            </button>
            <p>{plan.body.reason}</p>
            <div className="parameter-diff">
              {Object.entries(plan.body.parameters)
                .filter(
                  ([k, v]) =>
                    parent.body.parameters[k as keyof Parameters] !== v,
                )
                .map(([k, v]) => (
                  <p key={k}>
                    <strong>{friendly(k)}</strong>
                    <code>
                      {String(parent.body.parameters[k as keyof Parameters])}
                    </code>
                    <ChevronRight size={13} />
                    <code>{String(v)}</code>
                  </p>
                ))}
            </div>
          </>
        )}
        {!parent && <p className="muted">This is a root analysis.</p>}
        {children.map((child) => (
          <button key={child.id} onClick={() => choose(child)}>
            <GitBranch size={16} />
            {child.body.title}
            <Badge value={child.state} />
          </button>
        ))}
        {!children.length && <p className="muted">No child variations yet.</p>}
      </div>
    </div>
  );
}
function RunHistory({
  runs,
  choose,
}: {
  runs: Run[];
  choose: (r: Run) => void;
}) {
  return (
    <div className="card">
      <div className="card-heading">
        <h2>Every execution is retained</h2>
        <span className="muted">{runs.length} runs</span>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Started</th>
              <th>Execution</th>
              <th>Comparison</th>
              <th>Attempt</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td>
                  <code>{r.id.slice(0, 8)}</code>
                </td>
                <td>{when(r.created)}</td>
                <td>
                  <Badge value={r.state} />
                </td>
                <td>
                  {r.body.comparison ? (
                    <Badge value={r.body.comparison.status} />
                  ) : (
                    <span className="muted">Not evaluated</span>
                  )}
                </td>
                <td>{r.epoch}</td>
                <td>
                  <button className="text-button" onClick={() => choose(r)}>
                    Inspect
                    <ArrowUpRight size={14} />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {!runs.length && (
          <div className="empty">
            <p>No executions have been submitted for this plan.</p>
          </div>
        )}
      </div>
    </div>
  );
}
function EventList({ events }: { events: Event[] }) {
  return (
    <div className="card event-list">
      {[...events].reverse().map((e) => (
        <div className="event" key={e.id}>
          <span className="event-icon">
            {e.kind.startsWith("run") ? (
              <Play size={15} />
            ) : e.kind.startsWith("plan") ? (
              <FileText size={15} />
            ) : (
              <History size={15} />
            )}
          </span>
          <div>
            <h3>{friendly(e.kind)}</h3>
            <p>
              {String(
                e.body.reason ||
                  e.body.note ||
                  e.body.name ||
                  e.body.diagnostic ||
                  e.run_id?.slice(0, 8) ||
                  "",
              )}
            </p>
            <small>
              {e.actor} · event {e.id}
            </small>
          </div>
          <time>{when(e.created)}</time>
        </div>
      ))}
      {!events.length && <p className="muted">No activity yet.</p>}
    </div>
  );
}
function Team({
  workspace,
  act,
}: {
  workspace: Workspace;
  act: (fn: () => Promise<void>) => void;
}) {
  const [members, setMembers] = useState<{ subject: string; role: string }[]>(
      [],
    ),
    [usage, setUsage] = useState<{
      budget_usd: number;
      spent_or_reserved_usd: number;
    } | null>(null);
  async function load() {
    setMembers(await api("/workspaces/" + workspace.id + "/members"));
    setUsage(await api("/workspaces/" + workspace.id + "/usage"));
  }
  useEffect(() => {
    load();
  }, [workspace.id]);
  return (
    <>
      <PageTitle
        eyebrow="WORK TOGETHER, KEEP ATTRIBUTION"
        title="Team & settings"
        description="Workspace roles control review, execution, membership, and access to evidence."
      />
      <div className="team-grid">
        <section className="card">
          <div className="card-heading">
            <h2>Workspace members</h2>
            <Badge value={workspace.role} />
          </div>
          <table>
            <thead>
              <tr>
                <th>Identity subject</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {members.map((m) => (
                <tr key={m.subject}>
                  <td>{m.subject}</td>
                  <td>
                    <Badge value={m.role} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {workspace.role === "owner" && (
            <form
              className="card-content"
              onSubmit={(e) => {
                e.preventDefault();
                const f = new FormData(e.currentTarget);
                act(async () => {
                  await api(
                    "/workspaces/" + workspace.id + "/members",
                    { subject: f.get("subject"), role: f.get("role") },
                    "PUT",
                  );
                  await load();
                });
              }}
            >
              <h3>Add or update membership</h3>
              <label>
                OIDC subject
                <input
                  name="subject"
                  required
                  placeholder="Exact subject from your identity provider"
                />
              </label>
              <label>
                Role
                <select name="role">
                  <option value="viewer">Viewer: read evidence</option>
                  <option value="reviewer">
                    Reviewer: annotate and review
                  </option>
                  <option value="editor">
                    Editor: review plans and execute
                  </option>
                  <option value="owner">Owner: manage workspace access</option>
                </select>
              </label>
              <button>Save membership</button>
            </form>
          )}
        </section>
        <section className="card card-content">
          <div className="eyebrow">OPTIONAL ASSISTANCE</div>
          <h2>Model usage budget</h2>
          <strong className="budget">
            ${usage?.spent_or_reserved_usd.toFixed(4) || "0"}
          </strong>
          <p className="muted">
            Spent or conservatively reserved from a ${usage?.budget_usd || 0}{" "}
            workspace budget.
          </p>
          <p>
            Provider credentials, model choice and token prices are configured
            on the server. Manual method review works without a model.
          </p>
          <div className="locked-note">
            <ShieldCheck size={20} />
            <p>
              Model suggestions cannot execute code or accept scientific
              results.
            </p>
          </div>
        </section>
      </div>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
