import { readFileSync } from "node:fs";
import { gzipSync } from "node:zlib";
import path from "node:path";

const DIST_DIRECTORY = path.resolve(process.cwd(), "dist");
const ENTRY_RAW_BUDGET = 500_000;
const ENTRY_GZIP_BUDGET = 150_000;
const INITIAL_RAW_BUDGET = 1_500_000;
const INITIAL_GZIP_BUDGET = 500_000;

const formatKilobytes = (bytes) => `${(bytes / 1_000).toFixed(2)} kB`;

const html = readFileSync(path.join(DIST_DIRECTORY, "index.html"), "utf8");
const entryMatch = html.match(
  /<script[^>]+type=["']module["'][^>]+src=["']\/assets\/([^"']+\.js)["']/i
);

if (!entryMatch) {
  throw new Error("Unable to find the initial JavaScript entry in dist/index.html");
}

const initialAssets = [
  ...new Set(
    [...html.matchAll(/(?:src|href)=["']\/assets\/([^"']+\.js)["']/gi)].map(
      (match) => match[1]
    )
  ),
];

const getAssetSize = (assetName) => {
  const content = readFileSync(path.join(DIST_DIRECTORY, "assets", assetName));
  return {
    raw: content.length,
    gzip: gzipSync(content).length,
  };
};

const entrySize = getAssetSize(entryMatch[1]);
const initialSize = initialAssets.reduce(
  (total, assetName) => {
    const size = getAssetSize(assetName);
    return {
      raw: total.raw + size.raw,
      gzip: total.gzip + size.gzip,
    };
  },
  { raw: 0, gzip: 0 }
);

console.log(
  [
    `Initial entry: ${entryMatch[1]}`,
    `Entry JavaScript: ${formatKilobytes(entrySize.raw)} raw / ${formatKilobytes(entrySize.gzip)} gzip`,
    `Initial JavaScript (${initialAssets.length} files): ${formatKilobytes(initialSize.raw)} raw / ${formatKilobytes(initialSize.gzip)} gzip`,
  ].join("\n")
);

const failures = [
  ["entry raw", entrySize.raw, ENTRY_RAW_BUDGET],
  ["entry gzip", entrySize.gzip, ENTRY_GZIP_BUDGET],
  ["initial raw", initialSize.raw, INITIAL_RAW_BUDGET],
  ["initial gzip", initialSize.gzip, INITIAL_GZIP_BUDGET],
].filter(([, actual, budget]) => actual > budget);

if (failures.length > 0) {
  for (const [label, actual, budget] of failures) {
    console.error(
      `Bundle budget exceeded for ${label}: ${formatKilobytes(actual)} > ${formatKilobytes(budget)}`
    );
  }
  process.exitCode = 1;
}
