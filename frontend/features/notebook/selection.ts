export function codePointOffset(text: string, utf16Offset: number) {
  return Array.from(text.slice(0, utf16Offset)).length;
}
export function utf16Offset(text: string, codePoint: number) {
  return Array.from(text).slice(0, codePoint).join("").length;
}
export function selectedRange(
  element: HTMLElement,
): { start: number; end: number } | null {
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount) return null;
  const range = selection.getRangeAt(0);
  if (
    !element.contains(range.startContainer) ||
    !element.contains(range.endContainer)
  )
    return null;
  const prefix = range.cloneRange();
  prefix.selectNodeContents(element);
  prefix.setEnd(range.startContainer, range.startOffset);
  const start = Array.from(prefix.toString()).length;
  return { start, end: start + Array.from(range.toString()).length };
}
export function highlightChunks(
  text: string,
  marks: { start_offset: number; end_offset: number; color: string }[],
) {
  const chars = Array.from(text);
  const boundaries = [
    ...new Set([
      0,
      chars.length,
      ...marks.flatMap((m) => [m.start_offset, m.end_offset]),
    ]),
  ].sort((a, b) => a - b);
  return boundaries.slice(0, -1).map((start, i) => {
    const end = boundaries[i + 1];
    const mark = marks.findLast(
      (m) => m.start_offset <= start && m.end_offset >= end,
    );
    return { text: chars.slice(start, end).join(""), color: mark?.color };
  });
}
