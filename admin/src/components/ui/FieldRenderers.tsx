import { useState } from "react";

// ------- TextField -------

type TextFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  readOnly?: boolean;
  mono?: boolean;
};

export function TextField({
  label,
  value,
  onChange,
  placeholder,
  readOnly,
  mono,
}: TextFieldProps) {
  return (
    <label>
      {label}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        readOnly={readOnly}
        style={mono ? { fontFamily: "var(--mono)" } : undefined}
      />
    </label>
  );
}

// ------- SelectField -------

type SelectOption = { value: string; label: string };

type SelectFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
};

export function SelectField({
  label,
  value,
  onChange,
  options,
}: SelectFieldProps) {
  return (
    <label>
      {label}
      <select value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

// ------- TextAreaField -------

type TextAreaFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  mono?: boolean;
  rows?: number;
};

export function TextAreaField({
  label,
  value,
  onChange,
  placeholder,
  mono,
  rows,
}: TextAreaFieldProps) {
  return (
    <label>
      {label}
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        style={mono ? { fontFamily: "var(--mono)" } : undefined}
        rows={rows}
      />
    </label>
  );
}

// ------- CheckboxGroup -------

type CheckboxGroupProps = {
  label: string;
  options: string[];
  selected: string[];
  onChange: (selected: string[]) => void;
};

export function CheckboxGroup({
  label,
  options,
  selected,
  onChange,
}: CheckboxGroupProps) {
  const toggle = (opt: string) => {
    onChange(
      selected.includes(opt)
        ? selected.filter((s) => s !== opt)
        : [...selected, opt],
    );
  };

  return (
    <div className="field-group">
      <span className="field-label">{label}</span>
      <div className="checkbox-row">
        {options.map((opt) => (
          <label key={opt} className="checkbox-label">
            <input
              type="checkbox"
              checked={selected.includes(opt)}
              onChange={() => toggle(opt)}
            />
            {opt}
          </label>
        ))}
      </div>
    </div>
  );
}

// ------- TagField -------

type TagFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
};

export function TagField({
  label,
  value,
  onChange,
  placeholder,
}: TagFieldProps) {
  const tags = value
    .split(",")
    .map((t) => t.trim())
    .filter(Boolean);

  return (
    <div className="field-group">
      <label>
        {label}
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder ?? "comma-separated"}
        />
      </label>
      {tags.length > 0 && (
        <div className="tag-pills">
          {tags.map((tag) => (
            <span key={tag} className="tag-pill">
              {tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

// ------- JsonField -------

type JsonFieldProps = {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
};

export function JsonField({
  label,
  value,
  onChange,
  rows = 8,
}: JsonFieldProps) {
  const [valid, setValid] = useState(true);

  const handleChange = (next: string) => {
    onChange(next);
    try {
      JSON.parse(next);
      setValid(true);
    } catch {
      setValid(false);
    }
  };

  return (
    <div className="field-group">
      <label>
        <span className="field-label-row">
          {label}
          {!valid && <span className="json-error-badge">invalid JSON</span>}
        </span>
        <textarea
          value={value}
          onChange={(e) => handleChange(e.target.value)}
          rows={rows}
          className={valid ? "json-field" : "json-field json-field-invalid"}
        />
      </label>
    </div>
  );
}

// ------- ReadOnlyField -------

type ReadOnlyFieldProps = {
  label: string;
  value: string | null | undefined;
};

export function ReadOnlyField({ label, value }: ReadOnlyFieldProps) {
  return (
    <div className="readonly-field">
      <span className="readonly-label">{label}</span>
      <span className="readonly-value">{value ?? "—"}</span>
    </div>
  );
}
