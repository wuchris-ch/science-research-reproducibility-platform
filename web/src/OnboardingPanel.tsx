import { useEffect, useState } from "react";
import { api, asset, uploadFile, type Plan, type Workspace } from "./api";
type Evidence = {
  id: string;
  text: string;
  kind: string;
  document_id: string;
  page?: number;
  bbox?: number[];
  xml_id?: string;
  row?: number;
};
type Field = {
  key: string;
  value: string | number | null;
  status: string;
  origin: string;
  reason: string;
  evidence_ids: string[];
  candidates: { value: string | number; evidence_id: string; origin: string }[];
};
type Onboard = {
  id: string;
  history?: {
    revision: number;
    issues: string[];
    validated: boolean;
    accepted_fields: number;
  }[];
  revision: number;
  state: string;
  body: {
    title: string;
    documents: { id: string; name: string; kind: string; sha256: string }[];
    inputs: Record<string, { name: string; sha256: string }>;
    segments: Evidence[];
    fields: Record<string, Field>;
    validation: {
      input_genes: number;
      samples: number;
      donors: number;
      alignment: {
        sample: string;
        metadata_row: number;
        count_column: number;
      }[];
    } | null;
    issues: string[];
    input_hash?: string;
  };
};
const titles: Record<string, string> = {
  organism: "Organism",
  count_scale: "Count scale",
  design: "Model design",
  contrast: "Treatment contrast",
  sample_units: "Experimental units",
  min_total_count: "Minimum total count",
};
export function OnboardingPanel({
  workspace,
  act,
  onPlan,
}: {
  workspace: Workspace;
  act: (f: () => Promise<void>) => void;
  onPlan: (p: Plan) => Promise<void>;
}) {
  const [items, setItems] = useState<
      { id: string; title: string; state: string }[]
    >([]),
    [current, setCurrent] = useState<Onboard>(),
    [title, setTitle] = useState(""),
    [role, setRole] = useState("paper"),
    [search, setSearch] = useState(""),
    [selected, setSelected] = useState<Evidence>(),
    [image, setImage] = useState("");
  const canEdit = ["owner", "editor"].includes(workspace.role),
    editable = canEdit && current?.state === "draft";
  async function refresh() {
    setItems(await api(`/workspaces/${workspace.id}/onboardings`));
  }
  useEffect(() => {
    act(refresh);
  }, [workspace.id]);
  useEffect(() => {
    let live = true;
    let url = "";
    setImage("");
    if (current && selected?.page)
      asset(
        `/onboardings/${current.id}/documents/${selected.document_id}?page=${selected.page}`,
      )
        .then((value) => {
          url = value;
          if (live) setImage(value);
          else URL.revokeObjectURL(value);
        })
        .catch((error) =>
          act(async () => {
            throw error;
          }),
        );
    return () => {
      live = false;
      if (url) URL.revokeObjectURL(url);
    };
  }, [current?.id, selected?.id]);
  useEffect(() => {
    if (!current || current.history) return;
    let live = true;
    api<Onboard>(`/onboardings/${current.id}`)
      .then((latest) => {
        if (live)
          setCurrent((row) =>
            row?.id === latest.id && row?.revision === latest.revision
              ? { ...row, history: latest.history }
              : row,
          );
      })
      .catch((error) =>
        act(async () => {
          throw error;
        }),
      );
    return () => {
      live = false;
    };
  }, [current?.id, current?.revision]);
  const segments =
    current?.body.segments
      .filter(
        (s) => !search || s.text.toLowerCase().includes(search.toLowerCase()),
      )
      .slice(0, 60) || [];
  return (
    <div className="onboarding">
      <div className="page-title">
        <div className="eyebrow">PAPER, SUPPLEMENTS, DATA</div>
        <h1>Onboard a study</h1>
        <p className="subtitle">
          Align samples, resolve methods, and retain the evidence behind each
          decision.
        </p>
      </div>
      <div className="study-picker">
        <select
          aria-label="Select onboarding"
          value={current?.id || ""}
          onChange={(e) =>
            act(async () => {
              setCurrent(await api(`/onboardings/${e.target.value}`));
              setSelected(undefined);
            })
          }
        >
          <option value="" disabled>
            Select a study
          </option>
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title} · {item.state}
            </option>
          ))}
        </select>
        {canEdit && (
          <form
            onSubmit={(e) => {
              e.preventDefault();
              act(async () => {
                setCurrent(
                  await api("/onboardings", {
                    workspace_id: workspace.id,
                    title,
                  }),
                );
                setSelected(undefined);
                setTitle("");
                await refresh();
              });
            }}
          >
            <input
              aria-label="New study title"
              placeholder="New study title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              maxLength={160}
            />
            <button>Create study</button>
          </form>
        )}
      </div>
      {current?.history && (
        <details className="card">
          <summary>Review history and validation corrections</summary>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Revision</th>
                  <th>Input validation</th>
                  <th>Reviewed fields</th>
                  <th>Issues</th>
                </tr>
              </thead>
              <tbody>
                {current.history.map((h) => (
                  <tr key={h.revision}>
                    <td>{h.revision}</td>
                    <td>{h.validated ? "Passed" : "Pending or rejected"}</td>
                    <td>{h.accepted_fields} / 6</td>
                    <td>{h.issues.join("; ") || "None recorded"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
      {current ? (
        <>
          <div className="status-strip">
            <strong>{current.body.title}</strong>
            <span className={"badge " + current.state}>{current.state}</span>
            <span>Revision {current.revision}</span>
            <span className="strip-spacer" />
            {current.state === "sealed" && (
              <button
                onClick={() =>
                  act(async () => {
                    const p = await api<Plan>(
                      `/onboardings/${current.id}/plan`,
                      {
                        expected_revision: current.revision,
                        title: current.body.title,
                      },
                    );
                    await onPlan(p);
                  })
                }
              >
                Create analysis plan
              </button>
            )}
          </div>
          <div className="onboarding-grid">
            <section>
              <div className="card">
                <div className="card-heading">
                  <h2>1. Source and dataset files</h2>
                </div>
                <div className="card-content">
                  <p>
                    Use PDF or JATS XML for the paper, PDF/XML/TSV for
                    supplements, and TSV for counts and sample metadata.
                  </p>
                  <div className="upload-row">
                    <select
                      aria-label="File role"
                      value={role}
                      disabled={!editable}
                      onChange={(e) => setRole(e.target.value)}
                    >
                      {["paper", "supplement", "counts", "samples"].map((r) => (
                        <option key={r}>{r}</option>
                      ))}
                    </select>
                    <input
                      type="file"
                      aria-label="Upload study file"
                      disabled={!editable}
                      accept=".pdf,.xml,.tsv"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (!file) return;
                        const kind =
                          file.name.split(".").pop()?.toLowerCase() || "";
                        act(async () => {
                          setCurrent(
                            await uploadFile(
                              `/onboardings/${current.id}/files`,
                              file,
                              {
                                role,
                                kind,
                                expected_revision: String(current.revision),
                              },
                            ),
                          );
                          await refresh();
                        });
                        e.currentTarget.value = "";
                      }}
                    />
                  </div>
                  <ul className="file-list">
                    {current.body.documents.map((d) => (
                      <li key={d.id}>
                        <strong>{d.name}</strong>
                        <span>{d.kind.toUpperCase()}</span>
                        <code>{d.sha256.slice(0, 12)}</code>
                      </li>
                    ))}
                    {Object.entries(current.body.inputs).map(([key, item]) => (
                      <li key={key}>
                        <strong>{key}</strong>
                        <span>{item.name}</span>
                        <code>{item.sha256.slice(0, 12)}</code>
                      </li>
                    ))}
                  </ul>
                  {editable && (
                    <button
                      onClick={() =>
                        act(async () =>
                          setCurrent(
                            await api(`/onboardings/${current.id}/validate`, {
                              expected_revision: current.revision,
                            }),
                          ),
                        )
                      }
                    >
                      Validate counts and sample alignment
                    </button>
                  )}
                  {current.body.issues.map((issue) => (
                    <p className="error" role="alert" key={issue}>
                      {issue}
                    </p>
                  ))}
                  {current.body.validation && (
                    <>
                      <p className="validation-success">
                        Validated{" "}
                        {current.body.validation.input_genes.toLocaleString()}{" "}
                        genes, {current.body.validation.samples} samples,{" "}
                        {current.body.validation.donors} donor pairs.
                      </p>
                      <details>
                        <summary>Inspect sample alignment</summary>
                        <table>
                          <thead>
                            <tr>
                              <th>Sample</th>
                              <th>Count column</th>
                              <th>Metadata row</th>
                            </tr>
                          </thead>
                          <tbody>
                            {current.body.validation.alignment.map((r) => (
                              <tr key={r.sample}>
                                <td>{r.sample}</td>
                                <td>{r.count_column}</td>
                                <td>{r.metadata_row}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </details>
                    </>
                  )}
                </div>
              </div>
              <div className="card">
                <div className="card-heading">
                  <h2>2. Review the method</h2>
                  <span>6 required fields</span>
                </div>
                <div className="card-content">
                  <p>
                    Each decision links to a source region. Conflicting
                    proposals remain in the record after you resolve them.
                  </p>
                  {Object.entries(current.body.fields).map(([key, field]) => (
                    <MethodReview
                      key={key + current.revision}
                      field={field}
                      editable={Boolean(editable)}
                      segments={current.body.segments}
                      selected={selected}
                      inspect={setSelected}
                      save={async (body) => {
                        setCurrent(
                          await api(`/onboardings/${current.id}/review`, {
                            expected_revision: current.revision,
                            ...(body as Record<string, unknown>),
                          }),
                        );
                      }}
                      act={act}
                    />
                  ))}
                  {editable && (
                    <button
                      className="primary"
                      disabled={
                        !current.body.validation ||
                        Object.values(current.body.fields).some(
                          (f) => f.status !== "accepted",
                        )
                      }
                      onClick={() =>
                        act(async () => {
                          const p = await api<Plan>(
                            `/onboardings/${current.id}/plan`,
                            {
                              expected_revision: current.revision,
                              title: current.body.title,
                            },
                          );
                          await refresh();
                          await onPlan(p);
                        })
                      }
                    >
                      Seal evidence and create plan
                    </button>
                  )}
                </div>
              </div>
            </section>
            <aside className="evidence-pane">
              <div className="card">
                <div className="card-heading">
                  <div>
                    <div className="eyebrow">SOURCE EVIDENCE</div>
                    <h2>Inspect a region</h2>
                  </div>
                  <span>{current.body.segments.length} regions</span>
                </div>
                <div className="card-content">
                  <input
                    aria-label="Search evidence"
                    placeholder="Search a method or figure"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                  />
                  {selected && (
                    <div className="selected-evidence">
                      <strong>
                        {selected.page
                          ? `PDF page ${selected.page}`
                          : selected.row
                            ? `Table row ${selected.row}`
                            : `JATS ${selected.xml_id || selected.kind}`}
                      </strong>
                      <p>{selected.text}</p>
                      <code>{selected.id}</code>
                      {image && (
                        <div className="evidence-page">
                          <img
                            src={image}
                            alt={`Source page ${selected.page}`}
                          />
                          {selected.bbox && (
                            <span
                              style={{
                                left: selected.bbox[0] * 100 + "%",
                                top: selected.bbox[1] * 100 + "%",
                                width:
                                  (selected.bbox[2] - selected.bbox[0]) * 100 +
                                  "%",
                                height:
                                  (selected.bbox[3] - selected.bbox[1]) * 100 +
                                  "%",
                              }}
                            />
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="evidence-scroll">
                    {segments.map((s) => (
                      <button
                        className={
                          selected?.id === s.id
                            ? "evidence-item active"
                            : "evidence-item"
                        }
                        key={s.id}
                        onClick={() => setSelected(s)}
                      >
                        <span>
                          {s.page
                            ? `Page ${s.page}`
                            : s.row
                              ? `Row ${s.row}`
                              : s.kind}
                        </span>
                        <p>{s.text.slice(0, 420)}</p>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <div className="note-card">
                <h3>Evidence to execution</h3>
                <ol>
                  <li>Immutable source regions</li>
                  <li>Reviewed method decisions</li>
                  <li>Validated sample and count alignment</li>
                  <li>Locked adapter and input identities</li>
                  <li>Traceable gene-level outputs</li>
                </ol>
              </div>
            </aside>
          </div>
        </>
      ) : (
        <div className="empty">
          <h2>Select or create a study</h2>
          <p>
            The paired DESeq2 adapter supports human bulk RNA-seq with one
            control and one treated sample per donor.
          </p>
        </div>
      )}
    </div>
  );
}
function MethodReview({
  field,
  editable,
  segments,
  selected,
  inspect,
  save,
  act,
}: {
  field: Field;
  editable: boolean;
  segments: Evidence[];
  selected?: Evidence;
  inspect: (e: Evidence) => void;
  save: (b: unknown) => Promise<void>;
  act: (f: () => Promise<void>) => void;
}) {
  const [value, setValue] = useState(
      String(field.value ?? field.candidates[0]?.value ?? ""),
    ),
    [reason, setReason] = useState(field.reason),
    [evidence, setEvidence] = useState<string[]>(field.evidence_ids),
    [origin, setOrigin] = useState(
      field.origin === "missing" ? "inferred" : field.origin,
    );
  return (
    <div className="method-review">
      <div className="method-review-heading">
        <h3>{titles[field.key]}</h3>
        <span className={"badge " + field.status}>{field.status}</span>
      </div>
      {field.candidates.length > 0 && (
        <div className="candidate-list">
          {field.candidates.slice(0, 6).map((c, i) => (
            <button
              key={i}
              disabled={!editable}
              onClick={() => {
                setValue(String(c.value));
                setEvidence([c.evidence_id]);
                setOrigin(c.origin);
                const s = segments.find((s) => s.id === c.evidence_id);
                if (s) inspect(s);
              }}
            >
              {String(c.value)}
              <small>Inspect supporting region</small>
            </button>
          ))}
        </div>
      )}
      {editable ? (
        <>
          <label>
            Reviewed value
            <input
              type={field.key === "min_total_count" ? "number" : "text"}
              value={value}
              onChange={(e) => setValue(e.target.value)}
            />
          </label>
          <label>
            Decision basis
            <select value={origin} onChange={(e) => setOrigin(e.target.value)}>
              <option value="reported">Reported in source</option>
              <option value="inferred">Mapped from source methods</option>
              <option value="manual">Manual correction</option>
            </select>
          </label>
          <label>
            Reason
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explain how the evidence supports this value or resolves the conflict."
            />
          </label>
          <div className="actions">
            <button
              disabled={!selected}
              onClick={() =>
                selected &&
                setEvidence([...new Set([...evidence, selected.id])])
              }
            >
              Cite selected region
            </button>
            <button
              disabled={
                evidence.length === 0 || reason.trim().length < 10 || !value
              }
              onClick={() =>
                act(() =>
                  save({
                    key: field.key,
                    value:
                      field.key === "min_total_count" ? Number(value) : value,
                    origin,
                    evidence_ids: evidence,
                    reason,
                  }),
                )
              }
            >
              Accept reviewed field
            </button>
          </div>
        </>
      ) : (
        <>
          <p>{String(field.value ?? "Unresolved")}</p>
          <p className="muted">{field.reason}</p>
        </>
      )}
      <div className="evidence-links">
        {evidence.map((id) => (
          <button
            key={id}
            className="text-button"
            onClick={() => {
              const s = segments.find((s) => s.id === id);
              if (s) inspect(s);
            }}
          >
            {id}
          </button>
        ))}
      </div>
    </div>
  );
}
