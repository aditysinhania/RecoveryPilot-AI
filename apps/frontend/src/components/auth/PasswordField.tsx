import { Eye, EyeOff } from "lucide-react";
import { useState } from "react";

interface PasswordFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  autoComplete?: string;
  error?: string | null;
  disabled?: boolean;
  className?: string;
  required?: boolean;
}

const inputClass =
  "w-full rounded-lg border border-border bg-canvas px-3 py-2 pr-10 text-sm outline-none focus:border-ai";

/** Password input with a show/hide control that never submits the form. */
export function PasswordField({
  label,
  value,
  onChange,
  autoComplete = "current-password",
  error,
  disabled = false,
  className = "",
  required = false,
}: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);

  return (
    <label className={`block text-sm ${className}`}>
      <span className="text-muted">{label}</span>
      <span className="relative mt-1 block">
        <input
          type={visible ? "text" : "password"}
          autoComplete={autoComplete}
          value={value}
          disabled={disabled}
          required={required}
          onChange={(event) => onChange(event.target.value)}
          className={`${inputClass} ${error ? "border-blocked" : ""}`}
        />
        <button
          type="button"
          disabled={disabled}
          className="absolute inset-y-0 right-0 flex items-center px-3 text-muted hover:text-foreground disabled:opacity-50"
          aria-label={visible ? "Hide password" : "Show password"}
          onClick={() => setVisible((open) => !open)}
        >
          {visible ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
        </button>
      </span>
      {error ? <p className="mt-1 text-xs text-blocked">{error}</p> : null}
    </label>
  );
}
