import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useIsMutating } from "@tanstack/react-query";
import { useLocation, useNavigation } from "react-router-dom";
import { useUpdateChannel } from "@/hooks/useUpdateChannel";
import { useAppStore } from "@/stores/app-state";
import { useHighlightUI } from "./highlight-state";

const ReleaseHighlightsDialog = lazy(() => import("./ReleaseHighlightsDialog"));

const pageIsQuiet = () =>
  !document.hidden &&
  !document.querySelector(
    '[role="dialog"], [role="alertdialog"], [role="menu"], .MuiModal-root'
  ) &&
  !document.activeElement?.matches(
    'input, textarea, select, [contenteditable="true"]'
  );

export default function ReleaseHighlightsHost() {
  const channel = useUpdateChannel();
  const { pathname } = useLocation();
  const navigation = useNavigation();
  const mutations = useIsMutating();
  const appearanceOpen = useAppStore((state) => state.appearanceDialogOpen);
  const { requested, clearRequest } = useHighlightUI();
  const [openFor, setOpenFor] = useState(null);
  const [pendingFor, setPendingFor] = useState(null);
  const attempted = useRef(new Set());
  const release = channel.currentRelease;
  const available = Boolean(
    release?.highlights && channel.data?.highlight_state
  );
  const identity = available
    ? `${channel.data.reader_id}:${release.tag_name}`
    : null;
  const safePage =
    pathname === "/" &&
    navigation.state === "idle" &&
    !mutations &&
    !appearanceOpen;

  useEffect(() => {
    if (!requested) return;
    clearRequest();
    if (identity) {
      setOpenFor(identity);
      channel.setHighlightState("seen").catch(() => {});
    }
  }, [requested, identity, clearRequest, channel.setHighlightState]);

  useEffect(() => {
    if (
      !identity ||
      !safePage ||
      openFor === identity ||
      !channel.data?.highlight_state?.auto_show
    )
      return;
    const timer = setTimeout(async () => {
      if (!pageIsQuiet() || attempted.current.has(identity)) return;
      attempted.current.add(identity);
      try {
        // Server-side atomic claim prevents two tabs/devices announcing together.
        const state = await channel.setHighlightState("claim");
        if (state.show) setPendingFor(identity);
      } catch {
        // An unverified acknowledgement never interrupts the operator.
      }
    }, 1600);
    return () => clearTimeout(timer);
  }, [
    identity,
    safePage,
    openFor,
    channel.data?.highlight_state?.auto_show,
    channel.setHighlightState,
  ]);

  useEffect(() => {
    if (!identity || pendingFor !== identity || !safePage) return;
    const showWhenQuiet = () => {
      if (pageIsQuiet()) {
        setOpenFor(identity);
        setPendingFor(null);
      }
    };
    const timer = setTimeout(showWhenQuiet, 200);
    document.addEventListener("visibilitychange", showWhenQuiet);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", showWhenQuiet);
    };
  }, [pendingFor, identity, safePage]);

  if (!identity || openFor !== identity) return null;
  return (
    <Suspense fallback={null}>
      <ReleaseHighlightsDialog
        release={release}
        preview={channel.data?.preview}
        onClose={() => setOpenFor(null)}
        onLater={async () => {
          await channel.setHighlightState("later");
          attempted.current.delete(identity);
          setOpenFor(null);
        }}
      />
    </Suspense>
  );
}
