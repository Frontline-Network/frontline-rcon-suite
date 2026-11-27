export function memoryBytes(metric, field = "used") {
  const exact = metric?.[`${field}_bytes`];
  if (Number.isFinite(exact) && exact >= 0) return exact;
  const value = metric?.[field];
  return metric?.unit === "GiB" && Number.isFinite(value) && value >= 0
    ? value * 1024 ** 3
    : null;
}

export function formatMemorySize(value, locale) {
  if (!Number.isFinite(value) || value < 0) return null;
  const gib = value >= 1024 ** 3;
  const number = new Intl.NumberFormat(locale, {
    maximumFractionDigits: gib ? 2 : 1,
  }).format(value / (gib ? 1024 ** 3 : 1024 ** 2));
  return `${number} ${gib ? "GiB" : "MiB"}`;
}

export function memoryDisplay(metric, t, locale) {
  const source = metric?.source;
  let label = t("dashboard.resources.metrics.ram");
  if (source === "cgroup_v1" || source === "cgroup_v2") {
    label = t("dashboard.resources.containerRam");
  } else if (source === "host") {
    label = t("dashboard.resources.hostRam");
  }

  const used = memoryBytes(metric);
  const total = memoryBytes(metric, "total");
  if (
    metric?.available === false ||
    !Number.isFinite(metric?.percent) ||
    used == null ||
    total == null ||
    total <= 0
  ) {
    return { label, capacity: null };
  }
  return {
    label,
    capacity: t("dashboard.resources.memoryCapacity", {
      used: formatMemorySize(used, locale),
      total: formatMemorySize(total, locale),
    }),
  };
}

export function rconMemoryDisplay(metric, t, locale, { stale = false } = {}) {
  const label = t("dashboard.resources.instanceRam");
  const isStale = stale || String(metric?.reason || "").includes("stale");
  const used = memoryBytes(metric);
  const chargeAvailable =
    !isStale &&
    metric?.available === true &&
    metric?.source === "rcon_services" &&
    used != null;
  const available =
    chargeAvailable &&
    metric.service_ram_available === true &&
    [
      "service_used_bytes",
      "dedicated_service_used_bytes",
      "shared_service_used_bytes",
      "file_cache_bytes",
    ].every((field) => Number.isFinite(metric[field]) && metric[field] >= 0);
  return {
    label,
    available,
    value: available
      ? formatMemorySize(metric.dedicated_service_used_bytes, locale)
      : null,
    serviceValue: available
      ? formatMemorySize(metric.service_used_bytes, locale)
      : null,
    unavailableText: t(
      `dashboard.resources.${
        isStale ? "rconMemoryStale" : "rconMemoryUnavailable"
      }`
    ),
    dedicated: available
      ? formatMemorySize(metric?.dedicated_service_used_bytes, locale)
      : null,
    shared: available
      ? formatMemorySize(metric?.shared_service_used_bytes, locale)
      : null,
    components:
      available && Array.isArray(metric?.components)
        ? metric.components.filter(
            (item) =>
              item && Number.isFinite(item.used_bytes) && item.used_bytes >= 0
          )
        : [],
  };
}

export function memoryHistoryDisplay(history, locale) {
  const read = (value) => (Number.isFinite(value) && value >= 0 ? value : null);
  const bytes = history.map((sample) => {
    const value = sample.rcon_service_ram_used_bytes;
    return Number.isFinite(value) && value >= 0 ? value : null;
  });
  const dedicated = history.map((sample) =>
    read(sample.rcon_dedicated_ram_used_bytes)
  );
  const shared = history.map((sample) =>
    read(sample.rcon_shared_ram_used_bytes)
  );
  const values = [...bytes, ...dedicated, ...shared].filter(
    (value) => value != null
  );
  const totals = bytes.filter((value) => value != null);
  const divisor = values.some((value) => value >= 1024 ** 3)
    ? 1024 ** 3
    : 1024 ** 2;
  return {
    unit: divisor === 1024 ** 3 ? "GiB" : "MiB",
    data: bytes.map((value) => (value == null ? null : value / divisor)),
    dedicated: dedicated.map((value) =>
      value == null ? null : value / divisor
    ),
    shared: shared.map((value) => (value == null ? null : value / divisor)),
    minimum: totals.length
      ? formatMemorySize(Math.min(...totals), locale)
      : null,
    maximum: totals.length
      ? formatMemorySize(Math.max(...totals), locale)
      : null,
    available: values.length > 0,
  };
}
