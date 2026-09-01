import { expect, test } from "@playwright/test";
import {
  buildServerOptions,
  getServerHref,
  getServerShortCode,
} from "../src/components/layout/navigation/server-switching.mjs";

test.describe("server switching helpers", () => {
  test("preserves path, query and hash for linked servers", () => {
    expect(
      getServerHref(
        { link: "https://rcon2.example.test" },
        "https://rcon1.example.test/settings/maps?tab=pool#active"
      )
    ).toBe("https://rcon2.example.test/settings/maps?tab=pool#active");
  });

  test("changes only the port for local server targets", () => {
    expect(
      getServerHref(
        { port: 3004 },
        "http://127.0.0.1:3001/views/live?team=all#players"
      )
    ).toBe("http://127.0.0.1:3004/views/live?team=all#players");
  });

  test("deduplicates servers and keeps the current server first", () => {
    const current = { server_number: 2, name: "Current" };
    const result = buildServerOptions(current, [
      { server_number: 3, name: "Third" },
      { server_number: 2, name: "Duplicate" },
      { server_number: 1, name: "First" },
    ]);

    expect(result.map((server) => server.server_number)).toEqual([2, 1, 3]);
    expect(getServerShortCode(current)).toBe("S2");
    expect(getServerShortCode(null)).toBe("S–");
  });
});
