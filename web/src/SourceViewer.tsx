import { useEffect, useRef, useState } from "react";
import { X, Download, FileText } from "lucide-react";
import { asset, download, type Source } from "./api";

export function useDialog(active: boolean, close: () => void) {
  const callback = useRef(close);
  callback.current = close;
  useEffect(() => {
    if (!active) return;
    const previous = document.activeElement as HTMLElement | null;
    document
      .querySelector<HTMLElement>(
        '[role="dialog"] input, [role="dialog"] button',
      )
      ?.focus();
    const handler = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        event.preventDefault();
        callback.current();
        return;
      }
      if (event.key !== "Tab") return;
      const dialog = document.querySelector('[role="dialog"]');
      const nodes = Array.from(
        dialog?.querySelectorAll<HTMLElement>(
          'button:not(:disabled),input:not(:disabled),select:not(:disabled),textarea:not(:disabled),a[href],[tabindex="0"]',
        ) || [],
      ).filter((n) => n.offsetParent !== null);
      if (!nodes.length) return;
      const first = nodes[0],
        last = nodes[nodes.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handler);
    return () => {
      document.removeEventListener("keydown", handler);
      previous?.focus();
    };
  }, [active]);
}
export function SourceViewer({
  source,
  close,
}: {
  source: Source;
  close: () => void;
}) {
  const document =
    source.documents?.find((d) => d.role === "paper" && d.kind === "pdf") ||
    source.documents?.find((d) => d.role === "paper");
  const documentPath =
    source.onboarding_id && document
      ? `/onboardings/${source.onboarding_id}/documents/${document.id}`
      : undefined;
  const [url, setUrl] = useState(""),
    [error, setError] = useState(""),
    [region, setRegion] = useState<
      "figure_bbox" | "caption_bbox" | "method_bbox"
    >("figure_bbox");
  const first = useRef<HTMLButtonElement>(null);
  useDialog(true, close);
  useEffect(() => {
    first.current?.focus();
    let live = true;
    let value = "";
    if (documentPath && document?.kind !== "pdf") return;
    asset(
      documentPath
        ? documentPath + "?page=1"
        : "/sources/" + source.id + "/asset/page",
    )
      .then((u) => {
        value = u;
        if (live) setUrl(u);
        else URL.revokeObjectURL(u);
      })
      .catch((e) => setError(e.message));
    return () => {
      live = false;
      if (value) URL.revokeObjectURL(value);
    };
  }, [source.id]);
  const g = source.geometry,
    bbox = g?.[region];
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) close();
      }}
    >
      <section
        className="source-viewer"
        role="dialog"
        aria-modal="true"
        aria-labelledby="source-viewer-title"
      >
        <div className="card-heading">
          <div>
            <div className="eyebrow">
              {document ? "REVIEWED SOURCE DOCUMENT" : "VERIFIED SOURCE REGION"}
            </div>
            <h2 id="source-viewer-title">
              {source.authors || source.title}
              {g?.page || document?.kind === "pdf"
                ? ` · page ${g?.page || 1}`
                : ""}
            </h2>
          </div>
          <button
            ref={first}
            className="icon"
            aria-label="Close source viewer"
            onClick={close}
          >
            <X size={20} />
          </button>
        </div>
        <div className="source-toolbar">
          <div className="actions">
            {(
              [
                ["figure_bbox", "Figure"],
                ["caption_bbox", "Caption"],
                ["method_bbox", "Method"],
              ] as const
            )
              .filter(([key]) => g?.[key])
              .map(([key, label]) => (
                <button
                  key={key}
                  className={region === key ? "primary" : ""}
                  onClick={() => setRegion(key)}
                >
                  {label}
                </button>
              ))}
          </div>
          <button
            onClick={() =>
              download(
                documentPath || "/sources/" + source.id + "/asset/pdf",
                "source-paper.pdf",
              ).catch((e) => setError(e.message))
            }
          >
            <Download size={14} />
            {document ? "Download source" : "Complete PDF"}
          </button>
        </div>
        {error && <p className="error-banner">{error}</p>}
        <div className="source-page-scroll">
          <div className="source-page">
            {document && document.kind !== "pdf" ? (
              <div className="source-text">
                {source.segments.slice(0, 200).map((segment) => (
                  <p key={segment.id}>{segment.text}</p>
                ))}
              </div>
            ) : url ? (
              <img
                src={url}
                alt={`Verified page ${g?.page} from ${source.authors}, including the original figure and surrounding text`}
              />
            ) : (
              <div className="empty">
                <FileText size={30} />
                Loading source page
              </div>
            )}
            {bbox && g && url && (
              <div
                className="region-overlay"
                aria-label={"Highlighted " + region.replace("_bbox", "")}
                style={{
                  left: (bbox[0] / g.page_size_points[0]) * 100 + "%",
                  top: (bbox[1] / g.page_size_points[1]) * 100 + "%",
                  width:
                    ((bbox[2] - bbox[0]) / g.page_size_points[0]) * 100 + "%",
                  height:
                    ((bbox[3] - bbox[1]) / g.page_size_points[1]) * 100 + "%",
                }}
              />
            )}
          </div>
        </div>
        <div className="source-viewer-note">
          {document ? (
            "Open the onboarding record to inspect individual cited regions and review decisions."
          ) : (
            <>
              Article version {source.version} · DOI {source.doi}. Highlight
              positions were checked against this exact PDF.
            </>
          )}
        </div>
      </section>
    </div>
  );
}
