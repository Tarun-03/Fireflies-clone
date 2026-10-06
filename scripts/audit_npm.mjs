// Permit only the documented, unpatched development glob advisory; all other findings fail.
import { spawnSync } from "node:child_process";
const result = spawnSync("npm", ["audit", "--json"], { cwd: "frontend", encoding: "utf8" });
let report;
try { report = JSON.parse(result.stdout); } catch { throw new Error("npm audit did not return a report"); }
if (report.error) throw new Error(`npm audit failed: ${report.error.code}`);
const vulnerabilities = report.vulnerabilities ?? {};
const allowed = new Set(["braces", "micromatch", "fast-glob", "@next/eslint-plugin-next", "eslint-config-next"]);
let unexpected = false;
for (const [name, value] of Object.entries(vulnerabilities)) {
  for (const source of value.via) {
    if (!allowed.has(name) || (typeof source === "string" ? !allowed.has(source) : source.url !== "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm")) {
      console.error(`Unexpected finding: ${name}`);
      unexpected = true;
    }
  }
}
const runtime = spawnSync("npm", ["audit", "--omit=dev", "--audit-level=low"], {cwd:"frontend",encoding:"utf8"});
process.stdout.write(runtime.stdout);
if (runtime.status !== 0 || unexpected) process.exit(1);
console.log(`Reviewed ${Object.keys(vulnerabilities).length} development chain findings against one documented exception.`);
