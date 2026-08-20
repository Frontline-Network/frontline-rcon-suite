import { useQuery } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";

export const useTemplates = (key) => {
  const { data: templates } = useQuery({
    queryKey: ["crcon", "templates", key], // Query key
    queryFn: async () =>
      cmd.GET_MESSAGE_TEMPLATES({ params: { category: key.toUpperCase() } }),
    initialData: [],
  });

  if (!Array.isArray(templates)) return [];

  // React Query owns the cached array. Sort a copy so opening an action form
  // cannot mutate shared template data or crash when an older/malformed API
  // response is returned.
  return [...templates].sort((a, b) =>
    String(a?.title ?? "").localeCompare(String(b?.title ?? ""))
  );
};
