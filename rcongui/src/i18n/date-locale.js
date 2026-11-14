// Accept regional locale variants while keeping the existing German default.
export function dateLocale(language) {
  const base = (language || "de").toLowerCase().split(/[-_]/)[0];
  return ["de", "en", "fr"].includes(base) ? base : "de";
}
