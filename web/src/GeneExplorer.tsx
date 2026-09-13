import { useEffect, useState } from "react";
import { api, type Run } from "./api";
type Gene = {
  gene_id: string;
  log2FoldChange: number | null;
  baseMean: number | null;
  padj: number | null;
  pvalue: number | null;
  lfcSE: number | null;
  status: string;
};
const number = (v: number | null) =>
  v === null
    ? "Not estimated"
    : v !== 0 && Math.abs(v) < 0.0001
      ? v.toExponential(3)
      : v.toLocaleString(undefined, { maximumSignificantDigits: 4 });
export function GeneExplorer({
  run,
  act,
}: {
  run: Run;
  act: (f: () => Promise<void>) => void;
}) {
  const [query, setQuery] = useState(""),
    [page, setPage] = useState(0),
    [data, setData] = useState<{ total: number; rows: Gene[] }>(),
    [detail, setDetail] = useState<{
      gene: Gene;
      samples: {
        sample: string;
        donor: string;
        group: string;
        normalized_count: number;
      }[];
      input_hash: string;
      effects_sha256: string;
    }>();
  useEffect(() => {
    let live = true;
    const timer = setTimeout(
      () =>
        act(async () => {
          const r = await api<typeof data>(
            `/runs/${run.id}/genes?q=${encodeURIComponent(query)}&offset=${page * 40}`,
          );
          if (live) setData(r);
        }),
      200,
    );
    return () => {
      live = false;
      clearTimeout(timer);
    };
  }, [run.id, query, page]);
  useEffect(() => {
    setDetail(undefined);
    setPage(0);
  }, [run.id]);
  return (
    <section className="card gene-explorer">
      <div className="card-heading">
        <div>
          <span className="eyebrow">GENE-LEVEL EVIDENCE</span>
          <h2>Inspect the treatment response</h2>
        </div>
        <input
          aria-label="Search gene ID"
          placeholder="Search Ensembl gene ID"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setPage(0);
          }}
        />
      </div>
      <div className="gene-layout">
        <div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Gene</th>
                  <th>log2 change</th>
                  <th>BH adjusted P</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {data?.rows.map((g) => (
                  <tr key={g.gene_id}>
                    <td>
                      <button
                        className="text-button"
                        onClick={() =>
                          act(async () =>
                            setDetail(
                              await api(
                                `/runs/${run.id}/genes/${encodeURIComponent(g.gene_id)}`,
                              ),
                            ),
                          )
                        }
                      >
                        {g.gene_id}
                      </button>
                    </td>
                    <td>{number(g.log2FoldChange)}</td>
                    <td>{number(g.padj)}</td>
                    <td>{g.status.replaceAll("_", " ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="pagination">
            <button disabled={page === 0} onClick={() => setPage(page - 1)}>
              Previous
            </button>
            <span>
              {data?.total.toLocaleString()} genes · page {page + 1}
            </span>
            <button
              disabled={!data || (page + 1) * 40 >= data.total}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
        <aside className="gene-detail">
          {detail ? (
            <>
              <div className="eyebrow">SELECTED GENE</div>
              <h3>{detail.gene.gene_id}</h3>
              <p>
                log2 fold change {number(detail.gene.log2FoldChange)} · SE{" "}
                {number(detail.gene.lfcSE)}
              </p>
              <h4>Normalized expression by sample</h4>
              <div className="expression-bars">
                {detail.samples.map((s) => (
                  <div key={s.sample}>
                    <span>
                      {s.donor} · {s.group}
                    </span>
                    <div>
                      <i
                        style={{
                          width: `${(100 * s.normalized_count) / Math.max(...detail.samples.map((v) => v.normalized_count), 1)}%`,
                          background:
                            s.group === "treated" ? "#20786b" : "#98a6ba",
                        }}
                      />
                    </div>
                    <b>{number(s.normalized_count)}</b>
                  </div>
                ))}
              </div>
              <p className="field-hint">
                Counts divided by the recorded sample size factor. Compare
                treatment and control within each donor.
              </p>
              <details>
                <summary>Input and output provenance</summary>
                <p>
                  Input <code>{detail.input_hash}</code>
                </p>
                <p>
                  Effect table <code>{detail.effects_sha256}</code>
                </p>
                <p>
                  Runtime <code>{run.body.image_id}</code>
                </p>
              </details>
            </>
          ) : (
            <p>
              Select a gene to inspect its effect, uncertainty, donor-level
              counts, and exact input and output identities.
            </p>
          )}
        </aside>
      </div>
    </section>
  );
}
