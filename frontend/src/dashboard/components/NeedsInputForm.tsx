import { useState } from "react";
import type { MissingField } from "../../api/types";
import type { DomainAdapter, JsonInput } from "../model/adapter";

interface Props {
  message: string;
  fields: MissingField[];
  input: JsonInput;
  domain: DomainAdapter;
  onContinue: (input: JsonInput) => void;
  busy?: boolean;
}

export function NeedsInputForm({ message, fields, input, domain, onContinue, busy = false }: Props) {
  const [values, setValues] = useState<Record<string, string>>({});
  const complete = fields.every((f) => (values[f.field] ?? "").trim().length > 0);

  const submit = () => {
    const merged = fields.reduce((acc, f) => domain.applyMissingField(acc, f.field, values[f.field].trim()), input);
    onContinue(merged);
  };

  return (
    <div className="card card-attention" role="region" aria-label="Missing information">
      <div className="card-h"><span className="chip chip-attention">? Needs information</span><strong>The agent stopped to ask</strong></div>
      <p className="card-p">{message}</p>
      <div className="fields">
        {fields.map((f) => (
          <label key={f.field} className="field">
            <span className="field-l mono">{f.field}</span>
            <input value={values[f.field] ?? ""} onChange={(e) => setValues((v) => ({ ...v, [f.field]: e.target.value }))} placeholder={f.reason} aria-label={f.field} />
            <span className="field-h">{f.reason}</span>
          </label>
        ))}
      </div>
      <div className="card-actions">
        <button className="btn btn-primary" disabled={!complete || busy} onClick={submit}>{busy ? "Starting…" : "Continue"}</button>
      </div>
    </div>
  );
}
