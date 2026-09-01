import { isFakeMode } from "@/mirage/demo-data";
import { cmd } from "@/utils/fetchUtils";

export const loader = async () => {
  if (isFakeMode()) {
    return {
      serverName: "[GER] Frontline Network | #2",
      serverNameConfig: { ip: "127.0.0.1", port: 10011 },
    };
  }

  const serverName = await cmd.GET_SERVER_NAME();
  const serverNameConfig = await cmd.GET_SERVER_NAME_CHANGE_CONFIG();
  return { serverName, serverNameConfig };
};
