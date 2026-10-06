import { expect, it } from "vitest";
import {
  codePointOffset,
  utf16Offset,
  highlightChunks,
} from "@/features/notebook/selection";
it("round-trips code point ranges through emoji and combining sequences", () => {
  const text = "A😀e\u0301 café 🇮🇳";
  for (let point = 0; point <= Array.from(text).length; point++)
    expect(codePointOffset(text, utf16Offset(text, point))).toBe(point);
  expect(Array.from(text).slice(1, 4).join("")).toBe("😀e\u0301");
  const chunks = highlightChunks(text, [
    { start_offset: 1, end_offset: 4, color: "amber" },
  ]);
  expect(chunks.map((c) => c.text).join("")).toBe(text);
  expect(chunks[1]).toEqual({ text: "😀e\u0301", color: "amber" });
});
