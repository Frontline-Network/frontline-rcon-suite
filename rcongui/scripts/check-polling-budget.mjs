import { readFileSync, readdirSync } from "node:fs";
import { extname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = resolve(fileURLToPath(new URL("..", import.meta.url)));
const sourceRoot = resolve(projectRoot, "src");

const readSource = (relativePath) =>
  readFileSync(resolve(sourceRoot, relativePath), "utf8");

const collectJavaScriptSources = (directory) =>
  readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return collectJavaScriptSources(path);
    return [".js", ".jsx"].includes(extname(entry.name)) ? [path] : [];
  });

const requireText = (source, expected, label) => {
  if (!source.includes(expected)) {
    throw new Error(`${label} must contain ${JSON.stringify(expected)}`);
  }
};

const forbidText = (source, forbidden, label) => {
  if (source.includes(forbidden)) {
    throw new Error(`${label} must not contain ${JSON.stringify(forbidden)}`);
  }
};

const queryClientSource = readSource("queryClient.js");
const allSources = collectJavaScriptSources(sourceRoot)
  .map((path) => readFileSync(path, "utf8"))
  .join("\n");

requireText(
  queryClientSource,
  "refetchIntervalInBackground: false",
  "Admin QueryClient"
);
forbidText(allSources, "refetchIntervalInBackground: true", "Admin source");

const globalStateSource = readSource("stores/global-state.js");
requireText(
  globalStateSource,
  'queryKey: [{ queryIdentifier: "get_gamestate" }]',
  "Global state"
);
requireText(globalStateSource, "getGameStatePollingInterval", "Global state");

for (const relativePath of [
  "pages/views/live/index.jsx",
  "pages/views/team/index.jsx",
]) {
  const source = readSource(relativePath);
  requireText(source, 'from "@/stores/global-state"', relativePath);
  requireText(
    source,
    "useGlobalStore((state) => state.gameState)",
    relativePath
  );
  forbidText(source, 'queryKey: ["game", "state"]', relativePath);
  forbidText(source, "GET_GAME_STATE", relativePath);
  forbidText(source, "gameQueryOptions.state()", relativePath);
}

const titleManagerSource = readSource(
  "features/title-manager/TitleManager.jsx"
);
requireText(titleManagerSource, "useGlobalStore", "Title manager");
forbidText(titleManagerSource, "useQuery(", "Title manager");
forbidText(titleManagerSource, "refetchInterval", "Title manager");

console.log(
  "Polling budget contract passed: hidden tabs stop polling and one route-aware game-state stream serves global, live and team views."
);
