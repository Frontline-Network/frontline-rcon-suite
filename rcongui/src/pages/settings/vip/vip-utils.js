import dayjs from "dayjs";

export const INDEFINITE_EXPIRATION = "3000-01-01T00:00:00+00:00";

export const isVipIndefinite = (expiration) =>
  expiration === null || expiration === INDEFINITE_EXPIRATION;

export const isVipExpired = (expiration) =>
  !isVipIndefinite(expiration) && !dayjs(expiration).isAfter(dayjs());

export const isVipExpiringSoon = (expiration, days = 7) => {
  if (isVipIndefinite(expiration) || isVipExpired(expiration)) return false;
  return !dayjs(expiration).isAfter(dayjs().add(days, "day"));
};

export const getVipCategory = (expiration) => {
  if (isVipIndefinite(expiration)) return "indefinite";
  if (isVipExpired(expiration)) return "expired";
  if (isVipExpiringSoon(expiration)) return "expiring";
  return "active";
};

export const getVipRemainingLabel = (expiration, t) => {
  if (isVipIndefinite(expiration)) return t("records.vips.indefinite");
  return dayjs(expiration).fromNow();
};

export const getVipStatusLabel = (expiration, t) => {
  const category = getVipCategory(expiration);
  if (category === "expired") return t("records.vips.expired");
  if (category === "expiring") return t("records.vips.expiringSoon");
  return t("records.vips.active");
};
