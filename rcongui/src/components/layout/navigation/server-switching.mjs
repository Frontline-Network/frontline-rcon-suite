export const getServerHref = (selectedServer, currentHref) => {
  const resolvedCurrentHref =
    currentHref ??
    (typeof window !== "undefined"
      ? window.location.href
      : "http://localhost/");
  const currentUrl = new URL(resolvedCurrentHref);
  const targetUrl = selectedServer?.link
    ? new URL(selectedServer.link, currentUrl)
    : new URL(currentUrl.href);

  if (!selectedServer?.link && selectedServer?.port != null) {
    targetUrl.port = String(selectedServer.port);
  }

  targetUrl.pathname = currentUrl.pathname;
  targetUrl.search = currentUrl.search;
  targetUrl.hash = currentUrl.hash;
  return targetUrl.href;
};

export const buildServerOptions = (currentServer, peerServers = []) => {
  const byNumber = new Map();

  [currentServer, ...peerServers].filter(Boolean).forEach((server) => {
    const key = server.server_number ?? server.link ?? server.port;
    if (key == null || byNumber.has(key)) return;
    byNumber.set(key, server);
  });

  const currentNumber = currentServer?.server_number;
  return [...byNumber.values()].sort((left, right) => {
    if (left.server_number === currentNumber) return -1;
    if (right.server_number === currentNumber) return 1;
    return (
      Number(left.server_number ?? Infinity) -
      Number(right.server_number ?? Infinity)
    );
  });
};

export const getServerShortCode = (server) =>
  server?.server_number == null ? "S–" : `S${server.server_number}`;
