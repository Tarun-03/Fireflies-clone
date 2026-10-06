# Interface references

References accessed October 6, 2026:

- [Notebook guide](https://guide.fireflies.ai/articles/4827382971-learn-about-fireflies-notebook)
- [Notepad guide](https://guide.fireflies.ai/articles/6653885315-learn-about-the-fireflies-notepad)
- [Search guide](https://guide.fireflies.ai/articles/4577578901-how-to-search-and-find-your-meetings)

The public guides describe a left navigation, local and global search, filters, and meeting rows. The notebook guide specifies notes on the left and transcript on the right. The notebook two-panel image was inspected in its browser image preview after the initial navigation timeout. It shows a narrow tools rail, two white text panels with slim borders, speaker-colored transcript labels, a compact title, and playback controls along the bottom. The search guide’s first image preview was also inspected: a dark narrow navigation rail, compact horizontal meeting rows, top search, and a secondary utility area. This implementation uses that hierarchy with its own spacing, dialogs, responsive behavior, and a lighter navigation surface.

The original interface uses a 232px sidebar, a 4px spacing grid, thin borders, compact metadata, and a restrained purple accent. The notebook follows the documented two-panel hierarchy, with a persistent player. Tags replace commercial collaboration channels. Sample playback and extractive intelligence are labelled explicitly. Inter is bundled locally under the SIL Open Font License via @fontsource-variable/inter; no remote font or avatar requests are necessary.

Semantic light and dark tokens live in frontend/styles/globals.css. Keyboard focus uses a contrasting outline. Mobile layouts prioritize transcript readability and preserve player state.

## Verified interface

The library was reviewed at 390, 768, 1024, and 1440 pixels in light and dark themes. Playwright verified no horizontal overflow, filter restoration after refresh, notification read persistence, and theme persistence. Axe found no serious or critical findings across these eight library views after correcting the mobile create-button label. Two representative screenshots are stored in `docs/screenshots/` for the README. Browser runs write the full breakpoint/theme set to ignored `frontend/test-results/` artifacts.


The completed notebook has a narrow annotation/assistant rail, split notes/transcript panels, and a shared player. On mobile the tools become a horizontal row and tabs switch panels without losing playback. Light and dark notebook screenshots cover 390, 768, 1024, and 1440 pixels. Browser checks cover contrast/focus semantics with axe, keyboard search, source seeking, dialog workflows, and page-overflow bounds. Automated accessibility checks are a useful screen, not a complete accessibility certification.
