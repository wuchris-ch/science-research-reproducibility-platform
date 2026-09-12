import { useEffect, useState } from "react";
import { api, download, type Plan, type Workspace } from "./api";
type Study = {
  id: string;
  state: string;
  body: {
    title: string;
    hypothesis: string;
    protocol_hash: string;
    axes: Record<string, (string | number | boolean)[]>;
    matrix: unknown[];
    input_hash: string;
    min_abs_log2fc: number;
    alpha: number;
    registered_at: number;
    multiplicity: string;
  };
  variants: {
    ordinal: number;
    plan_id: string;
    run_id: string | null;
    state: string;
    body: { parameters: Record<string, unknown> };
    run?: {
      body: {
        diagnostic?: string;
        comparison?: { metrics: Record<string, number> };
      };
    };
  }[];
};
type Estimate = {
  variant: number;
  log2fc: number | null;
  se: number | null;
  ci95: [number, number] | null;
  padj: number | null;
  family_padj: number;
  status: string;
};
type Gene = {
  gene_id: string;
  classification: string;
  min_log2fc: number | null;
  max_log2fc: number | null;
  detections: number;
  estimates: Estimate[];
};
type Results = {
  complete: boolean;
  planned_variants: number;
  completed_variants: number;
  counts: Record<string, number>;
  family_hypotheses: number;
  total: number;
  genes: Gene[];
};
const fmt = (value: number | null | undefined) =>
  value == null
    ? "Unavailable"
    : value !== 0 && Math.abs(value) < 0.0001
      ? value.toExponential(3)
      : value.toLocaleString(undefined, { maximumSignificantDigits: 4 });
export function StudyPanel({
  workspace,
  plans,
  act,
}: {
  workspace: Workspace;
  plans: Plan[];
  act: (f: () => Promise<void>) => void;
}) {
  const [items, setItems] = useState<Study[]>([]),
    [study, setStudy] = useState<Study>(),
    [creating, setCreating] = useState(false),
    [baseId, setBaseId] = useState(""),
    [query, setQuery] = useState(""),
    [classification, setClassification] = useState(""),
    [page, setPage] = useState(0),
    [result, setResult] = useState<Results>(),
    [gene, setGene] = useState<Gene>();
  const [axes, setAxes] = useState([
    "min_total_count",
    "size_factor",
    "independent_filtering",
  ]);
  const canEdit = ["owner", "editor"].includes(workspace.role);
  async function list() {
    setItems(await api(`/workspaces/${workspace.id}/studies`));
  }
  useEffect(() => {
    act(list);
  }, [workspace.id]);
  useEffect(() => {
    if (!study) return;
    let live = true;
    const timer = setInterval(
      () =>
        api<Study>(`/studies/${study.id}`)
          .then((s) => {
            if (live) setStudy(s);
          })
          .catch((error) =>
            act(async () => {
              throw error;
            }),
          ),
      4000,
    );
    return () => {
      live = false;
      clearInterval(timer);
    };
  }, [study?.id]);
  const terminal =
    study && ["complete", "incomplete", "cancelled"].includes(study.state);
  useEffect(() => {
    let live = true;
    setGene(undefined);
    if (!study || !terminal) {
      setResult(undefined);
      return;
    }
    const timer = setTimeout(
      () =>
        act(async () => {
          const r = await api<Results>(
            `/studies/${study.id}/results?q=${encodeURIComponent(query)}&classification=${encodeURIComponent(classification)}&offset=${page * 40}`,
          );
          if (live) {
            setResult(r);
            setGene(r.genes[0]);
          }
        }),
      200,
    );
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [study?.id, terminal, query, classification, page]);
  const bases = plans.filter(
    (p) =>
      p.state === "locked" && p.body.recipe === "deseq2" && !p.body.study_id,
  );
  const base = bases.find((p) => p.id === baseId) || bases[0];
  const rules = Object.entries(base?.body.adapter?.parameters || {}).filter(
    ([, rule]) => rule.sensitivity.length >= 2,
  );
  const domain = Object.fromEntries(
    rules.map(([key, rule]) => [key, rule.sensitivity]),
  );
  const selectedAxes = axes.filter((key) => domain[key]);
  const variantCount = selectedAxes.reduce(
    (n, key) => n * domain[key].length,
    1,
  );
  return (
    <div className="study-panel">
      <div className="title-row">
        <div className="page-title">
          <div className="eyebrow">ONE QUESTION, ALL PLANNED VARIANTS</div>
          <h1>Sensitivity studies</h1>
          <p className="subtitle">
            Inspect how analysis choices affect effect sizes and conclusions.
          </p>
        </div>
        {canEdit && (
          <button onClick={() => setCreating(!creating)}>
            Preregister a study
          </button>
        )}
      </div>
      <div className="study-picker">
        <select
          aria-label="Select sensitivity study"
          value={study?.id || ""}
          onChange={(e) =>
            act(async () => {
              setStudy(await api(`/studies/${e.target.value}`));
              setPage(0);
            })
          }
        >
          <option value="" disabled>
            Select a sensitivity study
          </option>
          {items.map((s) => (
            <option value={s.id} key={s.id}>
              {s.body.title} · {s.state}
            </option>
          ))}
        </select>
      </div>
      {creating && (
        <form
          className="card protocol-form"
          onSubmit={(e) => {
            e.preventDefault();
            const data = new FormData(e.currentTarget);
            act(async () => {
              setStudy(
                await api("/studies", {
                  plan_id: data.get("plan"),
                  title: data.get("title"),
                  hypothesis: data.get("hypothesis"),
                  axes: Object.fromEntries(
                    selectedAxes.map((k) => [k, domain[k]]),
                  ),
                  alpha: Number(data.get("alpha")),
                  min_abs_log2fc: Number(data.get("effect")),
                }),
              );
              await list();
              setCreating(false);
            });
          }}
        >
          <h2>Freeze the protocol</h2>
          <label>
            Reviewed base plan
            <select
              name="plan"
              required
              value={base?.id || ""}
              onChange={(e) => setBaseId(e.target.value)}
            >
              {bases.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.body.title}
                </option>
              ))}
            </select>
          </label>
          {!bases.length && (
            <p>
              Lock a reviewed paired DESeq2 plan before registering a family.
            </p>
          )}
          <label>
            Study title
            <input name="title" required maxLength={160} />
          </label>
          <label>
            Scientific hypothesis
            <textarea
              name="hypothesis"
              required
              minLength={10}
              placeholder="Which treatment response should remain stable across these analysis choices?"
            />
          </label>
          <fieldset>
            <legend>Analysis choices</legend>
            {rules.map(([key, rule]) => (
              <label className="check-label" key={key}>
                <input
                  type="checkbox"
                  checked={axes.includes(key)}
                  onChange={(e) =>
                    setAxes(
                      e.target.checked
                        ? [...axes, key]
                        : axes.filter((a) => a !== key),
                    )
                  }
                />
                {rule.label}: {rule.sensitivity.map(String).join(", ")}
              </label>
            ))}
          </fieldset>
          <div className="field-grid">
            <label>
              Family FDR threshold
              <input
                name="alpha"
                type="number"
                min={0.001}
                max={0.2}
                step={0.001}
                defaultValue={0.05}
              />
            </label>
            <label>
              Minimum absolute log2 change
              <input
                name="effect"
                type="number"
                min={0}
                max={5}
                step={0.1}
                defaultValue={1}
              />
            </label>
          </div>
          <p>
            {variantCount} planned variants share exact inputs and runtime.
            Every result remains in the family. Benjamini-Yekutieli correction
            includes every input gene and variant.
          </p>
          <button
            className="primary"
            disabled={!bases.length || !selectedAxes.length || variantCount > 8}
          >
            Preregister {variantCount} variants
          </button>
        </form>
      )}
      {study && (
        <>
          <section className="card protocol-card">
            <div className="card-heading">
              <div>
                <span className="eyebrow">FROZEN PROTOCOL</span>
                <h2>{study.body.title}</h2>
              </div>
              <span className={"badge " + study.state}>
                {study.state.replaceAll("_", " ")}
              </span>
            </div>
            <div className="card-content">
              <p>{study.body.hypothesis}</p>
              <div className="protocol-facts">
                <span>{study.body.matrix.length} variants</span>
                <span>Family FDR {study.body.alpha}</span>
                <span>|log2 change| ≥ {study.body.min_abs_log2fc}</span>
                <span>
                  Registered{" "}
                  {new Date(study.body.registered_at * 1000).toLocaleString()}
                </span>
              </div>
              <details>
                <summary>Shared provenance and multiplicity</summary>
                <p>{study.body.multiplicity}</p>
                <p>
                  Protocol <code>{study.body.protocol_hash}</code>
                </p>
                <p>
                  Inputs <code>{study.body.input_hash}</code>
                </p>
              </details>
              <div className="actions">
                {canEdit && study.state === "registered" && (
                  <button
                    className="primary"
                    onClick={() =>
                      act(async () =>
                        setStudy(await api(`/studies/${study.id}/start`, {})),
                      )
                    }
                  >
                    Run all planned variants
                  </button>
                )}
                {canEdit && ["running", "registered"].includes(study.state) && (
                  <button
                    onClick={() =>
                      act(async () =>
                        setStudy(await api(`/studies/${study.id}/cancel`, {})),
                      )
                    }
                  >
                    Cancel family
                  </button>
                )}
                {terminal && (
                  <button
                    onClick={() =>
                      act(() =>
                        download(
                          `/studies/${study.id}/export`,
                          `sensitivity-${study.id.slice(0, 8)}.zip`,
                        ),
                      )
                    }
                  >
                    Export report and replay bundle
                  </button>
                )}
              </div>
            </div>
          </section>
          <section className="card">
            <div className="card-heading">
              <h2>Every planned execution</h2>
              <span>
                {study.variants.filter((v) => v.state === "succeeded").length} /{" "}
                {study.variants.length} complete
              </span>
            </div>
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>Variant</th>
                    <th>Choices</th>
                    <th>State</th>
                    <th>Retained</th>
                    <th>Significant within run</th>
                  </tr>
                </thead>
                <tbody>
                  {study.variants.map((v) => (
                    <tr key={v.ordinal}>
                      <td>V{v.ordinal}</td>
                      <td>
                        {Object.entries(v.body.parameters)
                          .map(
                            ([k, value]) =>
                              `${k.replaceAll("_", " ")}: ${value}`,
                          )
                          .join(" · ")}
                      </td>
                      <td>
                        <span className={"badge " + v.state}>
                          {v.state.replaceAll("_", " ")}
                        </span>
                        {v.run?.body.diagnostic && (
                          <p className="error">{v.run.body.diagnostic}</p>
                        )}
                      </td>
                      <td>
                        {fmt(v.run?.body.comparison?.metrics.retained_genes)}
                      </td>
                      <td>
                        {fmt(v.run?.body.comparison?.metrics.significant_genes)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          {result && (
            <>
              <div className="sensitivity-stats">
                {Object.entries(result.counts)
                  .filter(
                    ([k]) => k !== "not_estimated" && k !== "below_threshold",
                  )
                  .map(([label, n]) => (
                    <button
                      key={label}
                      onClick={() => {
                        setClassification(label);
                        setPage(0);
                      }}
                    >
                      <strong>{n.toLocaleString()}</strong>
                      <span>{label.replaceAll("_", " ")}</span>
                    </button>
                  ))}
              </div>
              <section className="card">
                <div className="card-heading">
                  <div>
                    <span className="eyebrow">GENE STABILITY</span>
                    <h2>Effects across the family</h2>
                  </div>
                  <input
                    aria-label="Search sensitivity gene"
                    placeholder="Search gene ID"
                    value={query}
                    onChange={(e) => {
                      setQuery(e.target.value);
                      setPage(0);
                    }}
                  />
                </div>
                <div className="card-content">
                  <p>
                    {result.complete
                      ? `${result.family_hypotheses.toLocaleString()} gene-by-variant hypotheses included in the family correction.`
                      : "The family is incomplete. No gene is classified as family supported."}{" "}
                    Family supported requires every planned variant to meet the
                    effect threshold, retain the same direction, and pass the
                    family correction.
                  </p>
                  <select
                    aria-label="Filter gene classification"
                    value={classification}
                    onChange={(e) => {
                      setClassification(e.target.value);
                      setPage(0);
                    }}
                  >
                    <option value="">All classifications</option>
                    {Object.keys(result.counts).map((k) => (
                      <option key={k} value={k}>
                        {k.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="gene-layout">
                  <div>
                    <div className="table-scroll">
                      <table>
                        <thead>
                          <tr>
                            <th>Gene</th>
                            <th>Classification</th>
                            <th>Effect range</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.genes.map((g) => (
                            <tr key={g.gene_id}>
                              <td>
                                <button
                                  className="text-button"
                                  onClick={() => setGene(g)}
                                >
                                  {g.gene_id}
                                </button>
                              </td>
                              <td>{g.classification.replaceAll("_", " ")}</td>
                              <td>
                                {fmt(g.min_log2fc)} to {fmt(g.max_log2fc)}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                    <div className="pagination">
                      <button
                        disabled={!page}
                        onClick={() => setPage(page - 1)}
                      >
                        Previous
                      </button>
                      <span>{result.total.toLocaleString()} genes</span>
                      <button
                        disabled={(page + 1) * 40 >= result.total}
                        onClick={() => setPage(page + 1)}
                      >
                        Next
                      </button>
                    </div>
                  </div>
                  <aside className="gene-detail">
                    {gene && (
                      <>
                        <h3>{gene.gene_id}</h3>
                        <EffectPlot estimates={gene.estimates} />
                        <p className="field-hint">
                          Points are log2 fold changes. Lines show ±1.96
                          coefficient SE and are not adjusted across variants.
                        </p>
                        <table>
                          <thead>
                            <tr>
                              <th>Variant</th>
                              <th>Family adjusted P</th>
                            </tr>
                          </thead>
                          <tbody>
                            {gene.estimates.map((e) => (
                              <tr key={e.variant}>
                                <td>V{e.variant}</td>
                                <td>{fmt(e.family_padj)}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </>
                    )}
                  </aside>
                </div>
              </section>
            </>
          )}
        </>
      )}
      {!study && !creating && (
        <div className="empty">
          <h2>Select a study or register a protocol</h2>
          <p>
            Analysis choices are frozen before the family starts. Completed,
            failed and cancelled variants remain inspectable.
          </p>
        </div>
      )}
    </div>
  );
}
export function EffectPlot({ estimates }: { estimates: Estimate[] }) {
  const values = estimates.flatMap((e) => e.ci95 || []);
  const lower = Math.min(0, ...values),
    upper = Math.max(0, ...values),
    span = Math.max(upper - lower, 1),
    min = lower - span * 0.1,
    max = upper + span * 0.1;
  const x = (v: number) => 58 + ((v - min) / (max - min)) * 260;
  const height = estimates.length * 34 + 52;
  return (
    <svg
      className="effect-plot"
      viewBox={`0 0 360 ${height}`}
      role="img"
      aria-label="Fold change and uncertainty for each sensitivity variant"
    >
      <line
        x1={x(0)}
        x2={x(0)}
        y1={10}
        y2={height - 35}
        stroke="#a7b2af"
        strokeDasharray="4"
      />
      {estimates.map((e, i) => (
        <g key={e.variant}>
          <text x={12} y={i * 34 + 26}>
            V{e.variant}
          </text>
          {e.log2fc !== null && e.ci95 ? (
            <>
              <line
                x1={x(e.ci95[0])}
                x2={x(e.ci95[1])}
                y1={i * 34 + 21}
                y2={i * 34 + 21}
                stroke="#20786b"
                strokeWidth={2}
              />
              <circle cx={x(e.log2fc)} cy={i * 34 + 21} r={4} fill="#20786b" />
            </>
          ) : (
            <text x={65} y={i * 34 + 26}>
              Not estimated
            </text>
          )}
        </g>
      ))}
      <text x={58} y={height - 10}>
        {min.toFixed(2)}
      </text>
      <text x={280} y={height - 10}>
        {max.toFixed(2)}
      </text>
      <text x={115} y={height - 10}>
        log2 fold change
      </text>
    </svg>
  );
}
