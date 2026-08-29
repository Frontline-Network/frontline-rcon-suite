const isRecord = (value) =>
  value !== null && typeof value === "object" && !Array.isArray(value);

const decodePointerToken = (token) =>
  token.replaceAll("~1", "/").replaceAll("~0", "~");

const resolveReference = (schema, rootSchema) => {
  if (!schema?.$ref?.startsWith("#/")) return schema || {};

  return (
    schema.$ref
      .slice(2)
      .split("/")
      .map(decodePointerToken)
      .reduce((current, segment) => current?.[segment], rootSchema || {}) || {}
  );
};

const resolveSchema = (schema, rootSchema) => {
  const resolved = resolveReference(schema, rootSchema);
  if (resolved.allOf?.length) {
    return resolved.allOf.reduce(
      (combined, entry) => ({
        ...combined,
        ...resolveSchema(entry, rootSchema),
        properties: {
          ...(combined.properties || {}),
          ...(resolveSchema(entry, rootSchema).properties || {}),
        },
      }),
      { ...resolved, allOf: undefined }
    );
  }

  const variants = resolved.anyOf || resolved.oneOf || [];
  const concreteVariant = variants
    .map((entry) => resolveSchema(entry, rootSchema))
    .find((entry) => entry.type !== "null");
  return concreteVariant
    ? { ...resolved, ...resolveSchema(concreteVariant, rootSchema) }
    : resolved;
};

const valueType = (value) => {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  if (Number.isInteger(value)) return "integer";
  if (typeof value === "number") return "number";
  if (isRecord(value)) return "object";
  return typeof value;
};

const schemaType = (schema) =>
  schema?.type || (schema?.properties ? "object" : undefined);

const typeMatches = (value, expectedType) => {
  if (!expectedType) return true;
  const actualType = valueType(value);
  if (expectedType === "number")
    return actualType === "number" || actualType === "integer";
  return actualType === expectedType;
};

const matchingSchema = (schema, value, rootSchema) => {
  const resolved = resolveReference(schema, rootSchema);
  const variants = resolved.anyOf || resolved.oneOf || [];
  if (!variants.length) return resolveSchema(resolved, rootSchema);

  return (
    variants
      .map((entry) => resolveSchema(entry, rootSchema))
      .find((entry) => typeMatches(value, schemaType(entry))) ||
    resolveSchema(resolved, rootSchema)
  );
};

const inspectValue = (value, schema, rootSchema, path, issues) => {
  if (value === undefined) return;

  const resolvedSchema = matchingSchema(schema, value, rootSchema);
  const expectedType = schemaType(resolvedSchema);
  const actualType = valueType(value);

  if (!typeMatches(value, expectedType)) {
    issues.push({
      path: path || "$",
      expectedType: expectedType || "unknown",
      actualType,
    });
    return;
  }

  if (actualType === "array" && resolvedSchema.items) {
    value.forEach((item, index) =>
      inspectValue(
        item,
        resolvedSchema.items,
        rootSchema,
        `${path || "$"}[${index}]`,
        issues
      )
    );
  }

  if (actualType === "object") {
    Object.entries(resolvedSchema.properties || {}).forEach(
      ([key, childSchema]) => {
        if (!Object.prototype.hasOwnProperty.call(value, key)) return;
        inspectValue(
          value[key],
          childSchema,
          rootSchema,
          path ? `${path}.${key}` : key,
          issues
        );
      }
    );
  }
};

export const inspectConfigCompatibility = (data, schema) => {
  const issues = [];
  inspectValue(data, schema, schema, "", issues);
  return issues;
};

/**
 * Applies form changes without discarding configuration values introduced by
 * an older/newer CRCON version. Declared arrays and free-form objects remain
 * fully replaceable; unknown keys inside structured objects are carried over.
 */
export const mergeConfigWithSchema = (
  currentValue,
  nextValue,
  schema,
  rootSchema = schema
) => {
  if (nextValue === undefined) return currentValue;
  if (Array.isArray(nextValue)) return nextValue;
  if (!isRecord(nextValue)) return nextValue;

  const resolvedSchema = resolveSchema(schema, rootSchema);
  const declaredProperties = resolvedSchema.properties || {};

  // Objects without declared fields are intentional key/value editors. Their
  // contents must be replaceable so users can also remove entries.
  if (!Object.keys(declaredProperties).length) return nextValue;

  const merged = isRecord(currentValue) ? { ...currentValue } : {};
  Object.entries(nextValue).forEach(([key, value]) => {
    merged[key] = Object.prototype.hasOwnProperty.call(declaredProperties, key)
      ? mergeConfigWithSchema(
          currentValue?.[key],
          value,
          declaredProperties[key],
          rootSchema
        )
      : value;
  });

  return merged;
};
