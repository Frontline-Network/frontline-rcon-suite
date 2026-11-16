import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const sourceRoot = join(root, "src");

function sourceFiles(path) {
  return readdirSync(path).flatMap((name) => {
    const entry = join(path, name);
    if (statSync(entry).isDirectory()) return sourceFiles(entry);
    return /\.(js|jsx|mjs|ts|tsx)$/.test(name) ? [entry] : [];
  });
}

// Raw fetch is deliberately limited to audited, read-only external requests
// plus the implementation of fetchWithCsrf itself. All CRCON API calls must go
// through fetchWithCsrf so future features cannot silently omit the token.
const allowedRawFetchFiles = new Set([
  "src/utils/fetchUtils.js",
  "src/serviceWorker.js",
  // Reads only the same-origin static language chunk manifest; no API write.
  "src/i18n/index.js",
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

const languageLoader = readFileSync(join(sourceRoot, "i18n/index.js"), "utf8");
const languageFetches = languageLoader.match(/(^|[^A-Za-z])fetch\s*\(/gm) || [];
if (languageFetches.length !== 1 || !languageLoader.includes('fetch(new URL("language-chunks.json", base), { cache: "no-store" })')) {
  violations.push("src/i18n/index.js must fetch only the static language manifest");
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

// Recovery concurrency/exactly-once behavior is covered by executable transport
// tests in check:csrf. This guard checks that every UI caller reaches that code.
const requiredRecoveryContracts = [
  ["shared token coordinator", /createCsrfTransport\(\{/],
  ["coordinated transport handoff", /csrfTransport\.fetchWithCsrf\(input, options\)/],
  ["explicit CSRF error classification", /csrfFailureKind\(response\)/],
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
