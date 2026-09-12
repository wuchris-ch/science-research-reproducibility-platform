import { useEffect, useRef, useState } from "react";
import { Upload, FileText, Download } from "lucide-react";
import { api, uploadSource, download, type Workspace } from "./api";
export function LibraryImports({
  workspace,
  act,
}: {
  workspace: Workspace;
  act: (fn: () => Promise<void>) => void;
}) {
  const [items, setItems] = useState<
    {
      id: string;
      created: number;
      body: { name: string; bytes: number; sha256: string; status: string };
    }[]
  >([]);
  const input = useRef<HTMLInputElement>(null);
  const activeWorkspace = useRef(workspace.id);
  activeWorkspace.current = workspace.id;
  async function refresh() {
    const result = await api<typeof items>(
      "/workspaces/" + workspace.id + "/sources",
    );
    if (activeWorkspace.current === workspace.id) setItems(result);
  }
  useEffect(() => {
    setItems([]);
    act(refresh);
  }, [workspace.id]);
  return (
    <section className="card imported-sources">
      <div className="card-heading">
        <div>
          <div className="eyebrow">YOUR ADDITIONAL SOURCES</div>
          <h2>Imported papers</h2>
        </div>
        {["owner", "editor"].includes(workspace.role) && (
          <>
            <input
              hidden
              ref={input}
              type="file"
              accept="application/pdf,.pdf"
              aria-label="Import a PDF"
              onChange={(event) => {
                const file = event.target.files?.[0];
                if (file)
                  act(async () => {
                    await uploadSource(workspace.id, file);
                    await refresh();
                    if (input.current) input.current.value = "";
                  });
              }}
            />
            <button onClick={() => input.current?.click()}>
              <Upload size={15} />
              Import PDF
            </button>
          </>
        )}
      </div>
      <div className="card-content">
        <p className="muted">
          Imported PDFs are saved for manual review. Runnable analyses currently
          use the two curated sources above.
        </p>
        {items.map((item) => (
          <div className="imported-source" key={item.id}>
            <FileText size={20} />
            <div>
              <strong>{item.body.name}</strong>
              <p>
                {(item.body.bytes / 1024).toFixed(1)} KB · Unreviewed ·{" "}
                {new Date(item.created * 1000).toLocaleDateString()}
              </p>
              <code>{item.body.sha256.slice(0, 20)}</code>
            </div>
            <button
              className="icon"
              aria-label={"Download " + item.body.name}
              onClick={() =>
                act(() =>
                  download(
                    "/workspaces/" +
                      workspace.id +
                      "/sources/" +
                      item.id +
                      "/download",
                    item.body.name,
                  ),
                )
              }
            >
              <Download size={17} />
            </button>
          </div>
        ))}
        {!items.length && (
          <p className="import-empty">No additional papers imported yet.</p>
        )}
      </div>
    </section>
  );
}
