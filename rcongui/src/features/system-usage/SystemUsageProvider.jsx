import { createContext, useContext } from "react";
import { useQuery } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import { getDemoSystemUsage, isFakeMode } from "@/mirage/demo-data";

export const SYSTEM_USAGE_QUERY_KEY = [{ queryIdentified: "get_system_usage" }];

const SystemUsageContext = createContext(null);

export const SystemUsageProvider = ({ children }) => {
  const query = useQuery({
    queryKey: SYSTEM_USAGE_QUERY_KEY,
    queryFn: isFakeMode() ? () => Promise.resolve(getDemoSystemUsage()) : cmd.GET_SYSTEM_USAGE,
    staleTime: 10 * 1000,
    refetchInterval: (currentQuery) => Math.max(10, Number(currentQuery.state.data?.poll_after_seconds) || 15) * 1000,
    refetchIntervalInBackground: false,
  });

  return <SystemUsageContext.Provider value={query}>{children}</SystemUsageContext.Provider>;
};

export const useSystemUsage = () => {
  const context = useContext(SystemUsageContext);
  if (!context) {
    throw new Error("useSystemUsage must be used inside SystemUsageProvider");
  }
  return context;
};
