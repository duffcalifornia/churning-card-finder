interface CountProps {
  value: number;
  onChange: (n: number) => void;
  label: string;
}

/** A small whole-number input. Zero shows as empty so a long table of cards stays readable. */
export function Count({ value, onChange, label }: CountProps) {
  return (
    <input
      className="count"
      type="number"
      inputMode="numeric"
      min={0}
      step={1}
      placeholder="0"
      aria-label={label}
      value={value === 0 ? "" : value}
      onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))}
    />
  );
}
