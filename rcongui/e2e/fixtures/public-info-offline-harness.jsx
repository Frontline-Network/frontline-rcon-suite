import React from "react";
import { createRoot } from "react-dom/client";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import RouteError from "../../src/components/shared/RouteError";
import { cmd } from "../../src/utils/fetchUtils";
import { selectAppLanguage } from "../../src/i18n";

export async function showOverview(language) {
  await selectAppLanguage(language);
  const root = document.createElement("div");
  root.id = "offline-test-root";
  document.body.appendChild(root);
  const router = createMemoryRouter([{
    path: "/",
    loader: () => cmd.GET_PUBLIC_GAME_STATE(),
    element: <div data-testid="overview-loaded">Overview loaded</div>,
    errorElement: <RouteError />,
  }], { initialEntries: ["/"] });
  createRoot(root).render(<RouterProvider router={router} />);
}
