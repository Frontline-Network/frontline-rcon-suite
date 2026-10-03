import { createBrowserRouter, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

import Root, { action as rootAction, loader as rootLoader } from "./pages/root";

import { AuthProvider } from "@/hooks/useAuth";
import { GlobalState } from "./stores/global-state";
import RouteError from "@/components/shared/RouteError";

const ViewsCrumb = () => {
  const { t } = useTranslation();
  return <span>{t("navigation.groups.views")}</span>;
};

const DocumentationCrumb = () => {
  const { t } = useTranslation();
  return <span>{t("documentation.title")}</span>;
};

const CampaignsCrumb = () => {
  const { t } = useTranslation();
  return <span>{t("navigation.links.broadcastMessage")}</span>;
};

const LiveGameCrumb = () => {
  const { t } = useTranslation();
  return <Link to={"/stats/live-game"}>{t("navigation.links.liveGame")}</Link>;
};

const lazyPage =
  (
    componentImport,
    {
      loaderImport,
      actionImport,
      errorImport,
      mapComponent,
      mapLoader,
      mapAction,
    } = {}
  ) =>
  async () => {
    const [componentModule, loaderModule, actionModule, errorModule] =
      await Promise.all([
        componentImport(),
        loaderImport?.(),
        actionImport?.(),
        errorImport?.(),
      ]);
    const loaderSource = loaderModule ?? componentModule;
    const actionSource = actionModule ?? componentModule;
    const Component = mapComponent
      ? mapComponent(componentModule)
      : componentModule.default;
    const loader = mapLoader ? mapLoader(loaderSource) : loaderSource?.loader;
    const action = mapAction ? mapAction(actionSource) : actionSource?.action;

    return {
      Component,
      ...(loader ? { loader } : {}),
      ...(action ? { action } : {}),
      ...(errorModule?.default ? { ErrorBoundary: errorModule.default } : {}),
    };
  };

const autobalancerLoader = (module) => (args) =>
  module.loader({
    ...args,
    params: {
      ...args.params,
      category: "others",
      type: "autobalancer",
    },
  });

const router = createBrowserRouter([
  {
    path: "/",
    element: (
      <AuthProvider>
        <GlobalState />
        <Root />
      </AuthProvider>
    ),
    errorElement: <RouteError />,
    action: rootAction,
    loader: rootLoader,
    children: [
      {
        path: "documentation",
        handle: { crumb: () => <DocumentationCrumb /> },
        lazy: lazyPage(() => import("./pages/documentation")),
        errorElement: <RouteError />,
      },
      {
        path: "administration/*",
        handle: { crumb: () => <span>Administration</span> },
        lazy: lazyPage(() => import("./pages/administration")),
        errorElement: <RouteError />,
      },
      {
        path: "",
        index: true,
        lazy: lazyPage(() => import("./pages/dashboard")),
        errorElement: <RouteError />,
      },
      {
        path: "apps",
        handle: { crumb: () => <span>Frontline App</span> },
        lazy: lazyPage(() => import("./pages/apps")),
        errorElement: <RouteError />,
      },
      {
        path: "apps/discord-report-bot",
        handle: { crumb: () => <span>Discord Report Bot</span> },
        lazy: lazyPage(() => import("./pages/apps/discord-report-bot")),
        errorElement: <RouteError />,
      },
      {
        path: "incidents",
        handle: { crumb: () => <span>Meldungen</span> },
        lazy: lazyPage(() => import("./pages/incidents")),
        errorElement: <RouteError />,
      },
      {
        path: "mobile/operations",
        handle: { crumb: () => <span>Betrieb</span> },
        lazy: lazyPage(() => import("./pages/mobile/operations")),
        errorElement: <RouteError />,
      },
      {
        path: "views",
        errorElement: <RouteError />,
        handle: { crumb: () => <ViewsCrumb /> },
        children: [
          {
            path: "live",
            handle: { crumb: () => <Link to={"/views/live"}>Live</Link> },
            lazy: lazyPage(() => import("./pages/views/live")),
            errorElement: <RouteError />,
          },
          {
            path: "live-map",
            handle: { crumb: () => <Link to="/views/live-map">Live-Karte</Link> },
            lazy: lazyPage(() => import("./pages/views/live-map")),
            errorElement: <RouteError />,
          },
          {
            path: "team",
            handle: { crumb: () => <Link to={"/views/team"}>Team</Link> },
            lazy: lazyPage(() => import("./pages/views/team")),
            errorElement: <RouteError />,
          },
          {
            path: "autobalancer",
            handle: {
              crumb: () => <Link to={"/views/autobalancer"}>Autobalancer</Link>,
            },
            lazy: lazyPage(() => import("./pages/settings/[configs]/detail"), {
              mapLoader: autobalancerLoader,
            }),
            errorElement: <RouteError />,
          },
        ],
      },
      {
        path: "records",
        errorElement: <RouteError />,
        handle: { crumb: () => <span>Records</span> },
        children: [
          {
            path: "players",
            handle: {
              crumb: () => <Link to={"/records/players"}>Players</Link>,
            },
            lazy: lazyPage(() => import("./pages/records/players")),
            errorElement: <RouteError />,
          },
          {
            path: "players/:playerId",
            lazy: lazyPage(() => import("./pages/records/players/[playerId]"), {
              loaderImport: () =>
                import("./pages/records/players/[playerId]/router"),
              actionImport: () =>
                import("./pages/records/players/[playerId]/router"),
            }),
            handle: {
              crumb: (data) => [
                <Link to={"/records/players"}>Players</Link>,
                <Link to={"/records/players/" + data?.profile?.player_id}>
                  {data?.profile?.names[0]?.name ?? ""}
                </Link>,
              ],
            },
            errorElement: <RouteError />,
            children: [
              {
                path: "",
                lazy: lazyPage(() =>
                  import("./pages/records/players/[playerId]/[detail]")
                ),
                errorElement: <RouteError />,
              },
              {
                path: ":detail",
                lazy: lazyPage(() =>
                  import("./pages/records/players/[playerId]/[detail]")
                ),
                errorElement: <RouteError />,
              },
              {
                path: "logs",
                lazy: lazyPage(() =>
                  import("./pages/records/players/[playerId]/[detail]/logs")
                ),
                errorElement: <RouteError />,
              },
            ],
          },
          {
            path: "vips",
            handle: { crumb: () => <Link to={"/records/vips"}>Vips</Link> },
            lazy: lazyPage(() => import("./pages/settings/vip")),
            errorElement: <RouteError />,
          },
          {
            path: "blacklists",
            handle: {
              crumb: () => <Link to={"/records/blacklists"}>Blacklists</Link>,
            },
            lazy: lazyPage(() => import("./pages/records/blacklists")),
            errorElement: <RouteError />,
          },
          {
            path: "blacklists/manage",
            handle: {
              crumb: () => [
                <Link to={"/records/blacklists"}>Blacklists</Link>,
                <span>Manage</span>,
              ],
            },
            lazy: lazyPage(() => import("./pages/records/blacklists/manage")),
            errorElement: <RouteError />,
          },
          {
            path: "game-logs",
            handle: {
              crumb: () => <Link to={"/records/game-log"}>Game Logs</Link>,
            },
            lazy: lazyPage(() => import("./pages/records/game-logs")),
            errorElement: <RouteError />,
          },
          {
            path: "audit-logs",
            handle: {
              crumb: () => <Link to={"/records/audit-log"}>Audit Logs</Link>,
            },
            lazy: lazyPage(() => import("./pages/records/audit-logs")),
            errorElement: <RouteError />,
          },
        ],
      },
      {
        path: "settings",
        errorElement: <RouteError />,
        lazy: lazyPage(() => import("./pages/settings/general-group")),
        handle: { crumb: () => <span>Settings</span> },
        children: [
          {
            path: "general",
            handle: { crumb: () => <span>General</span> },
            lazy: lazyPage(
              () => import("./pages/settings/general-group/general"),
              {
                loaderImport: () =>
                  import("./pages/settings/general-group/general/loader"),
              }
            ),
            errorElement: <RouteError />,
          },
          {
            path: "admin-cam-notifications",
            handle: { crumb: () => <span>Admin Cam Notifications</span> },
            lazy: lazyPage(
              () =>
                import(
                  "./pages/settings/general-group/admin-cam-notifications"
                ),
              {
                loaderImport: () =>
                  import(
                    "./pages/settings/general-group/admin-cam-notifications/loader"
                  ),
              }
            ),
            errorElement: <RouteError />,
          },
          {
            path: "server-name",
            handle: { crumb: () => <span>Server Name</span> },
            lazy: lazyPage(
              () => import("./pages/settings/general-group/server-name"),
              {
                loaderImport: () =>
                  import("./pages/settings/general-group/server-name/loader"),
              }
            ),
            errorElement: <RouteError />,
          },
          {
            path: "game",
            handle: { crumb: () => <span>Game</span> },
            lazy: lazyPage(
              () => import("./pages/settings/general-group/game"),
              {
                loaderImport: () =>
                  import("./pages/settings/general-group/game/loader"),
              }
            ),
            errorElement: <RouteError />,
          },
          {
            path: "crcon",
            handle: { crumb: () => <span>CRCON APP</span> },
            lazy: lazyPage(
              () => import("./pages/settings/general-group/crcon-app"),
              {
                mapComponent: (module) =>
                  function CrconSettingsRoute() {
                    const Component = module.default;
                    return <Component showFrontline={false} />;
                  },
              }
            ),
            errorElement: <RouteError />,
          },
        ],
      },
      {
        path: "settings/services",
        handle: { crumb: () => <span>Services</span> },
        lazy: lazyPage(() => import("./pages/settings/services")),
        errorElement: <RouteError />,
      },
      {
        path: "settings/console-admins",
        handle: {
          crumb: () => (
            <Link to={"/settings/console-admins"}>Console Admins</Link>
          ),
        },
        lazy: lazyPage(() => import("./pages/settings/console-admins")),
        errorElement: <RouteError />,
      },
      {
        path: "settings/profanity-filter",
        handle: { crumb: () => <span>Profanity Filter</span> },
        lazy: lazyPage(() => import("./pages/settings/profanity-filter")),
        errorElement: <RouteError />,
      },
      {
        path: "settings/welcome-message",
        handle: { crumb: () => <span>Welcome Message</span> },
        lazy: lazyPage(() => import("./pages/settings/welcome-message")),
        errorElement: <RouteError />,
      },
      {
        path: "settings/broadcast-message",
        handle: { crumb: () => <CampaignsCrumb /> },
        lazy: lazyPage(() => import("./pages/settings/broadcast-message")),
        errorElement: <RouteError />,
      },
      {
        path: "settings/autosettings",
        handle: { crumb: () => <span>Autosettings</span> },
        lazy: lazyPage(() => import("./pages/settings/autosettings")),
        errorElement: <RouteError />,
      },
      {
        path: "settings/maps",
        lazy: lazyPage(() => import("./pages/settings/maps"), {
          loaderImport: () => import("./pages/settings/maps/loader"),
        }),
        errorElement: <RouteError />,
        id: "maps",
        children: [
          {
            path: "change",
            lazy: lazyPage(() => import("./pages/settings/maps/list")),
            errorElement: <RouteError />,
          },
          {
            path: "rotation",
            lazy: lazyPage(() => import("./pages/settings/maps/rotation")),
            errorElement: <RouteError />,
            children: [
              {
                path: "",
                index: true,
                lazy: lazyPage(
                  () => import("./pages/settings/maps/rotation/builder"),
                  {
                    loaderImport: () =>
                      import("./pages/settings/maps/rotation/builder/loader"),
                  }
                ),
              },
              {
                path: "sequence",
                lazy: lazyPage(
                  () => import("./pages/settings/maps/rotation/sequence"),
                  {
                    loaderImport: () =>
                      import("./pages/settings/maps/rotation/sequence/loader"),
                  }
                ),
              },
              {
                path: "settings",
                lazy: lazyPage(
                  () => import("./pages/settings/maps/rotation/settings"),
                  {
                    loaderImport: () =>
                      import("./pages/settings/maps/rotation/settings/loader"),
                  }
                ),
              },
            ],
          },
          {
            path: "votemap",
            lazy: lazyPage(() => import("./pages/settings/maps/votemap")),
            errorElement: <RouteError />,
            children: [
              {
                path: "",
                index: true,
                lazy: lazyPage(
                  () => import("./pages/settings/maps/votemap/status"),
                  {
                    loaderImport: () =>
                      import("./pages/settings/maps/votemap/status/loader"),
                  }
                ),
              },
              {
                path: "whitelist",
                lazy: lazyPage(
                  () => import("./pages/settings/maps/votemap/builder"),
                  {
                    loaderImport: () =>
                      import("./pages/settings/maps/votemap/builder/loader"),
                  }
                ),
              },
              {
                path: "settings",
                lazy: lazyPage(
                  () => import("./pages/settings/maps/votemap/settings"),
                  {
                    loaderImport: () =>
                      import("./pages/settings/maps/votemap/settings/loader"),
                  }
                ),
              },
            ],
          },
          {
            path: "objectives",
            lazy: lazyPage(() => import("./pages/settings/maps/objectives"), {
              loaderImport: () =>
                import("./pages/settings/maps/objectives/loader"),
              errorImport: () =>
                import("./pages/settings/maps/objectives/error"),
            }),
          },
        ],
      },
      {
        path: "settings/templates",
        handle: { crumb: () => <span>Templates</span> },
        lazy: lazyPage(() => import("./pages/settings/templates")),
        children: [
          {
            path: ":category",
            handle: { crumb: () => <span>Detail</span> },
            lazy: lazyPage(() => import("./pages/settings/templates/detail")),
            errorElement: <RouteError />,
          },
        ],
      },
      {
        path: "/settings/integrations",
        handle: { crumb: () => <span>Discord &amp; Kommunikation</span> },
        lazy: lazyPage(() => import("./pages/settings/integrations")),
        errorElement: <RouteError />,
      },
      {
        path: "/settings/integrations/:section",
        handle: { crumb: () => <span>Discord &amp; Kommunikation</span> },
        lazy: lazyPage(() => import("./pages/settings/[configs]/detail")),
        errorElement: <RouteError />,
      },
      {
        path: "/settings/:category/:type",
        lazy: lazyPage(() => import("./pages/settings/[configs]/detail")),
        errorElement: <RouteError />,
      },
      {
        path: "stats",
        errorElement: <RouteError />,
        handle: { crumb: () => <span>Stats</span> },
        children: [
          {
            path: "live-game",
            handle: {
              crumb: () => <LiveGameCrumb />,
            },
            lazy: lazyPage(() => import("./pages/stats/live-game")),
            errorElement: <RouteError />,
          },
          {
            path: "live-sessions",
            handle: {
              crumb: () => (
                <Link to={"/stats/live-sessions"}>Live Sessions</Link>
              ),
            },
            lazy: lazyPage(() => import("./pages/stats/live-sessions")),
            errorElement: <RouteError />,
          },
          {
            path: "games",
            handle: { crumb: () => <Link to={"/stats/games"}>Games</Link> },
            lazy: lazyPage(() => import("./pages/stats/games/layout")),
            children: [
              {
                path: "",
                index: true,
                lazy: lazyPage(() => import("./pages/stats/games")),
                errorElement: <RouteError />,
              },
              {
                path: ":gameId",
                handle: { crumb: (data) => <span>{data?.gameId}</span> },
                lazy: lazyPage(() => import("./pages/stats/games/[gameId]")),
                errorElement: <RouteError />,
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: "/login",
    lazy: lazyPage(() => import("./pages/login")),
    errorElement: <RouteError />,
  },
]);

export default router;
