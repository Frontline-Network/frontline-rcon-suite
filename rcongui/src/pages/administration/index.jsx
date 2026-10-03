import { useEffect, useRef, useState } from "react";
import { Box, Button, LinearProgress, Stack, Tab, Tabs, Typography } from "@mui/material";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { useAppStore } from "@/stores/app-state";

const adminPath = (path) => /^\/admin(?:\/|$)/.test(path);
const workspacePath = (path) => path.replace(/^\/admin(?=\/|$)/, "/administration");
const frameSource = (path, language) => {
  const url = new URL(path.replace(/^\/administration\/?/, "/admin/"), window.location.origin);
  url.searchParams.set("embedded", "1");
  url.searchParams.set("ui_language", language);
  return url.href;
};

export default function Administration() {
  const location = useLocation();
  const navigate = useNavigate();
  const { i18n } = useTranslation();
  const german = i18n.resolvedLanguage?.startsWith("de");
  const language = german ? "de" : "en";
  const frameLanguage = useRef(language);
  const frame = useRef(null);
  const [height, setHeight] = useState(700);
  const [links, setLinks] = useState([]);
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);
  const framePath = useRef("");
  const pendingNavigation = useRef(true);
  const appearance = useAppStore((state) => state.appearancePreview || state.appearance);
  const initialSource = useRef(frameSource(location.pathname + location.search, language));

  const sendAppearance = () => frame.current?.contentWindow?.postMessage({
    type: "crcon-admin-appearance", preset: appearance.preset, mode: appearance.mode, wardogsStyle: appearance.wardogsStyle,
  }, window.location.origin);

  useEffect(() => {
    const receive = (event) => {
      if (event.origin !== window.location.origin || event.source !== frame.current?.contentWindow) return;
      if (pendingNavigation.current) return;
      const data = event.data;
      if (data?.type === "crcon-admin-page" && typeof data.path === "string" && adminPath(data.path)) {
        setReady(true); setFailed(false);
        if (Number.isFinite(data.height)) setHeight(Math.max(300, Math.min(100000, data.height)));
        if (Array.isArray(data.links)) setLinks(data.links.filter((item) => typeof item.url === "string" && adminPath(item.url) && typeof item.title === "string"));
        const nextPath = workspacePath(data.path);
        if (framePath.current && framePath.current !== nextPath) document.getElementById("main-content")?.scrollTo({ top: 0 });
        framePath.current = nextPath;
        if (framePath.current !== location.pathname + location.search) navigate(framePath.current, { replace: true });
        sendAppearance();
      } else if (data?.type === "crcon-admin-exit" && typeof data.path === "string" && /^\/(?!\/)/.test(data.path)) {
        navigate(data.path);
      }
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, [location.pathname, location.search, navigate, appearance]);

  useEffect(() => {
    const path = location.pathname + location.search;
    if ((framePath.current && framePath.current !== path) || frameLanguage.current !== language) {
      setReady(false); setFailed(false);
      pendingNavigation.current = true;
      frameLanguage.current = language;
      frame.current.src = frameSource(path, language);
    }
  }, [location.pathname, location.search, language]);

  useEffect(() => { sendAppearance(); }, [appearance]);
  useEffect(() => {
    if (ready) return undefined;
    const timeout = window.setTimeout(() => setFailed(true), 15000);
    return () => window.clearTimeout(timeout);
  }, [ready]);

  const items = [{url: "/admin/", title: german ? "Übersicht" : "Overview"}, ...links];
  const active = [...items].reverse().find((item) => location.pathname.startsWith(workspacePath(item.url)))?.url || false;
  return <Box sx={{ minWidth: 0 }}>
    <PageHeader title="Administration" subtitle={german ? "Benutzer, Berechtigungen und Zugänge verwalten." : "Manage users, permissions and access."}
      actions={<Button component={Link} to="/documentation?topic=roles">{german ? "Hilfe zu Rollen und Rechten" : "Roles and permissions help"}</Button>} />
    <Tabs value={active} variant="scrollable" scrollButtons="auto" aria-label={german ? "Verwaltungsbereiche" : "Administration areas"} sx={{ mb: 2, borderBottom: 1, borderColor: "divider" }}>
      {items.map((item) => <Tab component={Link} key={item.url} to={workspacePath(item.url)} value={item.url} label={item.title} />)}
    </Tabs>
    {!ready && !failed && <LinearProgress aria-label={german ? "Verwaltung wird geladen" : "Loading administration"} />}
    {failed && <Stack role="alert" gap={1.5} sx={{ p: 3, border: 1, borderColor: "divider", borderRadius: 2 }}>
      <Typography>{german ? "Die Verwaltung konnte nicht geladen werden." : "Administration could not be loaded."}</Typography>
      <Button component="a" href="/admin/?standalone=1" target="_blank" rel="noopener">{german ? "Verwaltung separat öffnen" : "Open administration separately"}</Button>
    </Stack>}
    <Box component="iframe" ref={frame} src={initialSource.current} title={german ? "Benutzer- und Rechteverwaltung" : "User and permission administration"}
      onLoad={() => {
        pendingNavigation.current = false;
        frame.current?.contentWindow?.postMessage({ type: "crcon-admin-request-page" }, window.location.origin);
      }}
      sx={{ display: failed ? "none" : "block", width: "100%", height, border: 0, colorScheme: appearance.mode === "light" ? "light" : "dark" }} />
  </Box>;
}
