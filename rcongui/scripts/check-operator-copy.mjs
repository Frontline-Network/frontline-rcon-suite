import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { parse } = require("@babel/parser");

const ROOT = path.resolve(import.meta.dirname, "..");
const OPERATOR_SURFACES = [
  "src/pages/settings/[configs]/detail.jsx",
  "src/pages/settings/autosettings/index.jsx",
  "src/pages/apps/discord-report-bot/index.jsx",
  "src/pages/settings/general-group/crcon-app/DiscordReportBotCard.jsx",
  "src/features/player-action/ActionDialog.jsx",
  "src/features/player-action/ActionForm.jsx",
  "src/features/player-action/DisbandSquad.jsx",
  "src/components/dashboard/BattleOverview.jsx",
  "src/pages/dashboard.jsx",
];

const VISIBLE_ATTRIBUTES = new Set([
  "aria-label",
  "description",
  "helperText",
  "label",
  "placeholder",
  "title",
]);

const normalize = (value) => value.replace(/\s+/g, " ").trim();

const looksLikeOperatorCopy = (value) => {
  const text = normalize(value);
  if (!text || !/\p{L}/u.test(text)) return false;
  if (/^sk-[•…*.-]+$/u.test(text)) return false;
  if (/^(https?:|\/|#|[a-z0-9_.-]+\/[a-z0-9_./-]+$)/i.test(text)) {
    return false;
  }
  return true;
};

const location = (node) => ({
  line: node.loc?.start.line ?? 0,
  column: node.loc?.start.column ?? 0,
});

const translatedCall = (node) =>
  node?.type === "CallExpression" &&
  node.callee?.type === "Identifier" &&
  node.callee.name === "t";

function collectExpressionCopy(node, findings) {
  if (!node || translatedCall(node)) return;

  if (node.type === "StringLiteral") {
    if (looksLikeOperatorCopy(node.value)) {
      findings.push({ text: normalize(node.value), ...location(node) });
    }
    return;
  }
  if (node.type === "TemplateLiteral") {
    for (const quasi of node.quasis) {
      if (looksLikeOperatorCopy(quasi.value.cooked || "")) {
        findings.push({
          text: normalize(quasi.value.cooked || ""),
          ...location(quasi),
        });
      }
    }
    return;
  }
  if (node.type === "ConditionalExpression") {
    collectExpressionCopy(node.consequent, findings);
    collectExpressionCopy(node.alternate, findings);
    return;
  }
  if (node.type === "LogicalExpression") {
    collectExpressionCopy(node.right, findings);
    return;
  }
  if (node.type === "BinaryExpression" && node.operator === "+") {
    collectExpressionCopy(node.left, findings);
    collectExpressionCopy(node.right, findings);
    return;
  }
  if (node.type === "ArrayExpression") {
    node.elements.forEach((element) => collectExpressionCopy(element, findings));
  }
}

function walk(node, visitor, parent = null) {
  if (!node || typeof node !== "object") return;
  visitor(node, parent);
  for (const [key, value] of Object.entries(node)) {
    if (key === "loc" || key === "start" || key === "end") continue;
    if (Array.isArray(value)) {
      value.forEach((child) => walk(child, visitor, node));
    } else if (value && typeof value === "object" && value.type) {
      walk(value, visitor, node);
    }
  }
}

export function findHardcodedOperatorCopy(source, filename = "source.jsx") {
  const ast = parse(source, {
    sourceType: "module",
    sourceFilename: filename,
    plugins: ["jsx"],
  });
  const findings = [];

  walk(ast, (node, parent) => {
    if (node.type === "JSXText" && looksLikeOperatorCopy(node.value)) {
      findings.push({ text: normalize(node.value), ...location(node) });
      return;
    }
    if (node.type !== "JSXAttribute") return;

    const name = node.name?.name;
    if (!VISIBLE_ATTRIBUTES.has(name)) return;
    if (node.value?.type === "StringLiteral") {
      if (looksLikeOperatorCopy(node.value.value)) {
        findings.push({
          text: normalize(node.value.value),
          ...location(node.value),
        });
      }
      return;
    }
    if (node.value?.type === "JSXExpressionContainer") {
      collectExpressionCopy(node.value.expression, findings);
    }
  });

  walk(ast, (node, parent) => {
    if (
      node.type === "JSXExpressionContainer" &&
      parent?.type === "JSXElement"
    ) {
      collectExpressionCopy(node.expression, findings);
    }
  });

  return findings;
}

function assertDetectorContract() {
  const translated = findHardcodedOperatorCopy(
    '<Button aria-label={t("common.save")}>{t("common.save")}</Button>'
  );
  const hardcoded = findHardcodedOperatorCopy(
    '<Button title="Server speichern">Einstellungen speichern</Button>'
  );
  const conditional = findHardcodedOperatorCopy(
    '<Button>{ready ? "Jetzt ausführen" : t("common.processing")}</Button>'
  );
  const technicalState = findHardcodedOperatorCopy(
    '<>{step === "review" && t("actions.review")}</>'
  );
  const maskedSecret = findHardcodedOperatorCopy(
    '<TextField placeholder={stored ? "sk-••••" : "sk-…"} />'
  );
  if (
    translated.length !== 0 ||
    hardcoded.length !== 2 ||
    conditional.length !== 1 ||
    technicalState.length !== 0 ||
    maskedSecret.length !== 0
  ) {
    throw new Error("operator-copy detector self-test failed");
  }
}

assertDetectorContract();

const violations = [];
for (const relativePath of OPERATOR_SURFACES) {
  const absolutePath = path.join(ROOT, relativePath);
  const source = fs.readFileSync(absolutePath, "utf8");
  const findings = findHardcodedOperatorCopy(source, relativePath);
  findings.forEach((finding) =>
    violations.push({ file: relativePath, ...finding })
  );
}

if (violations.length) {
  console.error("Hard-coded operator-facing copy found:");
  for (const violation of violations) {
    console.error(
      `- ${violation.file}:${violation.line}:${violation.column + 1} ${JSON.stringify(
        violation.text
      )}`
    );
  }
  console.error("Move the text to both i18n locale files and render it with t().");
  process.exit(1);
}

console.log(
  `Operator-copy contract passed for ${OPERATOR_SURFACES.length} critical surfaces.`
);
