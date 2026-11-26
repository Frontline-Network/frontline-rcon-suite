export function memoryDisplay(metric, t, locale) {
  const source = metric?.source;
  let label = t("dashboard.resources.metrics.ram");
  if (source === "cgroup_v1" || source === "cgroup_v2") {
    label = t("dashboard.resources.containerRam");
  } else if (source === "host") {
    label = t("dashboard.resources.hostRam");
  }

  const bytes = (field) => {
    const exact = metric?.[`${field}_bytes`];
    if (Number.isFinite(exact) && exact >= 0) return exact;
    const value = metric?.[field];
    return metric?.unit === "GiB" && Number.isFinite(value) && value >= 0
      ? value * 1024 ** 3
      : null;
  };
  const used = bytes("used");
  const total = bytes("total");
  if (metric?.available === false || !Number.isFinite(metric?.percent) ||
      used == null || total == null || total <= 0) {
    return { label, capacity: null };
  }
  const formatSize = (value) => {
    const gib = value >= 1024 ** 3;
    const number = new Intl.NumberFormat(locale, {
      maximumFractionDigits: gib ? 2 : 1,
    }).format(value / (gib ? 1024 ** 3 : 1024 ** 2));
    return `${number} ${gib ? "GiB" : "MiB"}`;
  };
  return {
    label,
    capacity: t("dashboard.resources.memoryCapacity", {
      used: formatSize(used), total: formatSize(total),
    }),
  };
}
