export function Avatar({
  name,
  small = false,
}: {
  name: string;
  small?: boolean;
}) {
  const color =
    [...name].reduce((sum, char) => sum + (char.codePointAt(0) ?? 0), 0) % 6;
  return (
    <span
      className={`avatar avatar-${color} ${small ? "small" : ""}`}
      title={name}
      aria-label={name}
    >
      {name
        .split(/\s+/)
        .map((part) => part[0])
        .slice(0, 2)
        .join("")}
    </span>
  );
}
