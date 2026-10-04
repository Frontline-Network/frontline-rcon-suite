// The backend chooses the eligible spotlight and owns its original release key.
// The current changelog entry stays separate: a hotfix is not the feature release.
export function highlightReleaseForChannel(channel) {
  if (channel?.status !== "ready" || !Array.isArray(channel.releases))
    return null;
  const key = channel.highlight_state?.release_version;
  if (typeof key !== "string" || !key) return null;
  return (
    channel.releases.find(
      (release) =>
        release.highlights &&
        typeof release.tag_name === "string" &&
        release.tag_name.replace(/^v/, "") === key.replace(/^v/, "")
    ) ?? null
  );
}
