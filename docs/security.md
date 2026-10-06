# Security and data handling

This is an anonymous demonstration for synthetic meeting data. No security audit or penetration test is claimed. An anonymous workspace is not a verified identity. Losing its session cookie prevents normal access to its existing data.

Configuration requires a service token of at least 32 characters. Example files contain no working secrets. Local environment files and database/WAL files are excluded from Git. SQLite connections use foreign keys, WAL, full synchronous durability, and a bounded busy timeout.

## Dependency review

Checked October 6, 2026. Next.js 16.3.8 includes the September security updates. The runtime npm dependency audit returned no findings during initial installation.

The full npm audit reports five high-severity dependency-chain entries originating from one unpatched development-only advisory: [GHSA-vfj7-8cjw-p6xm](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm), braces <=3.0.3. It is reached through Next.js's lint plugin → fast-glob → micromatch. npm and the advisory list no patched braces release. The application does not accept glob patterns from users; lint operates on checked-in source with fixed patterns, and the production standalone image excludes development tooling. This is a narrowly scoped tooling exception, not a suppressed runtime finding. Recheck when upgrading tooling; arbitrary untrusted glob patterns must never be passed to this dependency.

ESLint 10 uses the official @eslint/compat adapter for the Next.js React/import/accessibility rules that still declare ESLint 9 peer ranges. No rules are disabled.
