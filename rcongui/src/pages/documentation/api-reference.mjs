// Treat the introspection response as data, including on older backends.
export function normalizeApiDocumentation(value) {
  if (!Array.isArray(value))
    throw new Error("Invalid API documentation response");
  const entries = new Map();
  for (const item of value) {
    if (!item || typeof item.endpoint !== "string" || !item.endpoint.trim())
      continue;
    const strings = (values) =>
      Array.isArray(values) ? values.filter((v) => typeof v === "string") : [];
    entries.set(item.endpoint, {
      endpoint: item.endpoint,
      methods: strings(item.allowed_http_methods).map((value) =>
        value.toUpperCase()
      ),
      permissions: strings(item.permissions_required),
      description: typeof item.doc_string === "string" ? item.doc_string : "",
      descriptionTranslations: Object.fromEntries(
        ["de", "en"]
          .filter(
            (language) =>
              typeof item.description_translations?.[language] === "string" &&
              item.description_translations[language].trim()
          )
          .map((language) => [
            language,
            item.description_translations[language].trim(),
          ])
      ),
      returnType: typeof item.return_type === "string" ? item.return_type : "",
      arguments:
        item.arguments &&
        typeof item.arguments === "object" &&
        !Array.isArray(item.arguments)
          ? Object.entries(item.arguments).map(([name, argument]) => ({
              name,
              type:
                typeof argument?.annotation === "string"
                  ? argument.annotation
                  : "",
              default:
                typeof argument?.default === "string" ? argument.default : null,
            }))
          : [],
    });
  }
  if (value.length && !entries.size)
    throw new Error("Invalid API documentation entries");
  return [...entries.values()].sort((a, b) =>
    a.endpoint.localeCompare(b.endpoint)
  );
}

export function localizeApiDocumentation(entries, language) {
  const locale = language?.split("-")[0] || "en";
  return entries.map((item) => {
    const translated =
      item.descriptionTranslations[locale] || item.descriptionTranslations.en;
    return {
      ...item,
      description: translated || item.description,
      technicalDescription:
        translated && translated !== item.description ? item.description : "",
    };
  });
}

export function apiEndpointPath(item) {
  return item.methods.includes("WEBSOCKET")
    ? "/" + item.endpoint
    : "/api/" + item.endpoint;
}

export function filterApiDocumentation(entries, search, method) {
  const words = search.trim().toLocaleLowerCase().split(/\s+/).filter(Boolean);
  return entries.filter((item) => {
    if (method && !item.methods.includes(method)) return false;
    const text = [
      item.endpoint,
      item.description,
      item.technicalDescription,
      ...item.permissions,
      ...item.arguments.map((arg) => arg.name),
    ]
      .join(" ")
      .toLocaleLowerCase();
    return words.every((word) => text.includes(word));
  });
}
