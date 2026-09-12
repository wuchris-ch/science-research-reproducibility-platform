import { useEffect, useState } from "react";
import { api, type Adapter, type Parameters } from "./api";

export function ParameterEditor({
  recipe,
  adapter: frozen,
  values,
  onChange,
  disabled,
}: {
  recipe: string;
  adapter?: Adapter;
  values: Parameters;
  onChange: (value: Parameters) => void;
  disabled: boolean;
}) {
  const [adapter, setAdapter] = useState(frozen);
  const [error, setError] = useState("");
  useEffect(() => {
    if (frozen) {
      setAdapter(frozen);
      return;
    }
    let active = true;
    setError("");
    api<Adapter[]>("/adapters")
      .then((items) => {
        if (active) setAdapter(items.find((a) => a.recipe === recipe));
      })
      .catch(() => {
        if (active)
          setError("Parameter definitions could not load. Reload this plan.");
      });
    return () => {
      active = false;
    };
  }, [recipe, frozen]);
  return (
    <div className="field-grid">
      {error && <p role="alert">{error}</p>}
      {adapter &&
        Object.entries(adapter.parameters).map(([key, rule]) => (
          <label key={key}>
            {rule.label}
            {rule.type === "boolean" ? (
              <select
                disabled={disabled}
                value={String(values[key] ?? rule.default)}
                onChange={(e) =>
                  onChange({ ...values, [key]: e.target.value === "true" })
                }
              >
                <option value="true">Enabled</option>
                <option value="false">Disabled</option>
              </select>
            ) : rule.choices.length ? (
              <select
                disabled={disabled}
                value={String(values[key] ?? rule.default)}
                onChange={(e) => onChange({ ...values, [key]: e.target.value })}
              >
                {rule.choices.map((value) => (
                  <option key={String(value)} value={String(value)}>
                    {String(value)}
                  </option>
                ))}
              </select>
            ) : (
              <input
                type={rule.type === "string" ? "text" : "number"}
                step={rule.type === "integer" ? 1 : "any"}
                min={rule.minimum}
                max={rule.maximum}
                disabled={disabled}
                value={String(values[key] ?? rule.default)}
                onChange={(e) =>
                  onChange({
                    ...values,
                    [key]:
                      rule.type === "string"
                        ? e.target.value
                        : Number(e.target.value),
                  })
                }
              />
            )}
          </label>
        ))}
    </div>
  );
}
