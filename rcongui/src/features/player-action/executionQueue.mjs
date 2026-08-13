const wait = (milliseconds) =>
  new Promise((resolve) => setTimeout(resolve, milliseconds));

const isRetryableStatus = (status) => status === 429 || status >= 500;

const executeWithRetry = async (
  execute,
  payload,
  { maxAttempts, retryDelayMs }
) => {
  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await execute(payload);
      if (
        response?.ok ||
        !isRetryableStatus(response?.status) ||
        attempt === maxAttempts
      ) {
        return { status: "fulfilled", value: response };
      }
    } catch (reason) {
      const status = reason?.status;
      const canRetry =
        attempt < maxAttempts &&
        (status == null || isRetryableStatus(status));
      if (!canRetry) {
        return { status: "rejected", reason };
      }
    }

    await wait(retryDelayMs * attempt);
  }
};

export const executeQueued = async (
  payloads,
  execute,
  { concurrency = payloads.length || 1, maxAttempts = 1, retryDelayMs = 0 } = {}
) => {
  const results = new Array(payloads.length);
  let nextIndex = 0;

  const worker = async () => {
    while (nextIndex < payloads.length) {
      const index = nextIndex;
      nextIndex += 1;
      results[index] = await executeWithRetry(execute, payloads[index], {
        maxAttempts,
        retryDelayMs,
      });
    }
  };

  const workerCount = Math.min(Math.max(1, concurrency), payloads.length);
  await Promise.all(Array.from({ length: workerCount }, worker));
  return results;
};

