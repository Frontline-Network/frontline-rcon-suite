import { operatorMessageEntries } from "./locales/operator-messages.js";

const exactMessages = new Map();
const templates = [];
exactMessages.set("Proposal is no longer eligible for approval", "approvalNoLongerEligible");
exactMessages.set("Incident is no longer active", "incidentInactive");
const escapeRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
for (const [key, source] of operatorMessageEntries) {
  const fields = [...source.matchAll(/\{\{(\w+)\}\}/g)];
  if (!fields.length) {
    exactMessages.set(source, key);
    continue;
  }
  // The volunteer prefix is composed with a separately translated reason.
  if (key === "volunteerReason") continue;
  let pattern = "^";
  let end = 0;
  for (const field of fields) {
    pattern += escapeRegex(source.slice(end, field.index)) + "([\\s\\S]+)";
    end = field.index + field[0].length;
  }
  pattern += escapeRegex(source.slice(end)) + "$";
  templates.push({ key, expression: new RegExp(pattern), fields: fields.map((field) => field[1]) });
}

/** Translate only recognized system messages at presentation boundaries.
 * Do not apply this to chat, admin comments, configured templates or names.
 * Comparisons and API submissions must keep the original, unmodified value.
 */
export function translateOperatorMessage(message, t) {
  if (typeof message !== "string" || typeof t !== "function") return message;
  const translate = (value, allowComposite = true) => {
    const key = exactMessages.get(value);
    if (key) return t(`operatorMessages.${key}`);
    if (value.startsWith("freiwillig; ")) {
      const reason = translate(value.slice("freiwillig; ".length), false);
      if (reason !== null) return t("operatorMessages.volunteerReason", { reason });
    }
    for (const { key: templateKey, expression, fields } of templates) {
      const match = expression.exec(value);
      if (match) {
        const values = Object.fromEntries(fields.map((field, index) => [field, match[index + 1]]));
        // This field is a system classification, unlike player and squad names.
        if (templateKey === "roleMisclassified" && values.actual === "unbekannt") {
          values.actual = t("operatorMessages.unknownRole");
        }
        return t(`operatorMessages.${templateKey}`, values);
      }
    }
    if (allowComposite && value.includes("; ")) {
      const parts = value.split("; ").map((part) => translate(part, false));
      if (parts.every((part) => part !== null)) return parts.join("; ");
    }
    return null;
  };
  return translate(message) ?? message;
}
