import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = join(root, "src");

function sourceFiles(path) {
  return readdirSync(path).flatMap((name) => {
    const entry = join(path, name);
    if (statSync(entry).isDirectory()) return sourceFiles(entry);
    return /\.(js|jsx|ts|tsx)$/.test(name) ? [entry] : [];
  });
}

// Raw fetch is deliberately limited to audited, read-only external requests
// plus the implementation of fetchWithCsrf itself. All CRCON API calls must go
// through fetchWithCsrf so future features cannot silently omit the token.
const allowedRawFetchFiles = new Set([
  "src/utils/fetchUtils.js",
  "src/serviceWorker.js",
  "src/components/Header/footer.js",
  "src/hooks/useGithubReleases.js",
  "src/pages/login/footer.jsx",
]);

const violations = [];
for (const file of sourceFiles(sourceRoot)) {
  const source = readFileSync(file, "utf8");
  if (!/(^|[^A-Za-z])fetch\s*\(/m.test(source)) continue;
  const name = relative(root, file).replaceAll("\\", "/");
  if (!allowedRawFetchFiles.has(name)) violations.push(name);
}

const fetchUtils = readFileSync(
  join(sourceRoot, "utils/fetchUtils.js"),
  "utf8"
);
const rawFetchCount = (fetchUtils.match(/(^|[^A-Za-z])fetch\s*\(/gm) || [])
  .length;
if (rawFetchCount !== 1) {
  violations.push(
    `src/utils/fetchUtils.js contains ${rawFetchCount} raw fetch calls; expected only fetchWithCsrf`
  );
}

const requiredTransports = [
  [
    "generic request factory",
    /fetchWithCsrf\(url\.toString\(\),\s*requestOptions\)/,
  ],
  ["legacy GET transport", /fetchWithCsrf\(`\$\{CRCON_API\}\$\{path\}`\s*,/],
  ["legacy POST transport", /fetchWithCsrf\(url\s*,\s*\{\s*method:\s*"POST"/],
  ["mobile integration transport", /mobileRequest[\s\S]*fetchWithCsrf\(url,/],
  ["Discord integration transport", /discordRequest[\s\S]*fetchWithCsrf\(url,/],
];

const requiredRecoveryContracts = [
  ["recovery marker", /X-CRCON-CSRF-Recovery/],
  ["server-derived recovery token", /X-CRCON-CSRF-Token/],
  [
    "server-confirmed token reuse",
    /serverConfirmedCsrfToken[\s\S]*requestHeadersWithCsrf[\s\S]*serverConfirmedCsrfToken/,
  ],
  [
    "recovery token handoff",
    /response\.headers\.get\(CSRF_TOKEN_HEADER\)[\s\S]*send\(recoveryToken\)/,
  ],
];

for (const [name, pattern] of requiredTransports) {
  if (!pattern.test(fetchUtils)) {
    violations.push(`${name} is not CSRF guarded`);
  }
}

for (const [name, pattern] of requiredRecoveryContracts) {
  if (!pattern.test(fetchUtils)) {
    violations.push(`${name} is missing from the CSRF recovery path`);
  }
}

if (violations.length) {
  console.error("CSRF request contract violations:\n" + violations.join("\n"));
  process.exit(1);
}

console.log("CSRF request contract OK");
