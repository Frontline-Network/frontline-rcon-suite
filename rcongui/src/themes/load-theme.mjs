export async function loadThemeWithRetry(load, isActive = () => true) {
  try {
    return await load();
  } catch (error) {
    if (!isActive()) throw error;
    await new Promise((resolve) => setTimeout(resolve, 500));
    if (!isActive()) throw error;
    return load(); // One retry; never reload the page automatically.
  }
}
