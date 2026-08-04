import { cmd, execute } from "@/utils/fetchUtils";
  import {  toast } from "react-toastify";
  import { defer } from "react-router-dom";
import i18n from "@/i18n";
import { demoPlayerRecords, isFakeMode } from "@/mirage/demo-data";
import { normalizePlayerProfile } from "@/utils/lib";
import PlayerProfilePage from './index';
import PlayerDetailView from './[detail]';

const fetchResource = async (request, errorMessage) => {
    try {
      const data = await request();
      if (!data) throw new Response(errorMessage, { status: 404 });
      return data;
    } catch (error) {
      console.warn("Failed to fetch player data:", error);
      return null; // Return null if any request fails
    }
  };
  
  export const loader = async ({ params, request }) => {
    const { playerId } = params;
    const url = new URL(request.url);
    const numSessions = url.searchParams.get('num_sessions') || 10;
  
    // Use the fetchResource function for each API call
  const fetchPlayer = isFakeMode()
    ? Promise.resolve(normalizePlayerProfile(
        demoPlayerRecords.find((player) => player.player_id === playerId)
      ))
    : fetchResource(
        () => cmd.GET_PLAYER({
          params: { player_id: playerId, num_sessions: numSessions },
        }),
        "Player not found"
      ).then((profile) => profile ? normalizePlayerProfile(profile) : null);
  
  const fetchMessages = isFakeMode() ? Promise.resolve([]) : fetchResource(
      () => cmd.GET_PLAYER_MESSAGES({ params: { player_id: playerId } }),
      "Messages not found"
    );
  
    // Run all promises concurrently
    const [profile, messages] = await Promise.all([
      fetchPlayer,
      fetchMessages,
    ]);
  
    // If player is not found, throw an error
    if (!profile) {
      throw new Response("Player not found", { status: 404 });
    }
  
    // Return a deferred object to allow data to load in parallel
    return defer({
      profile,
      messages,
      numSessions,
    });
  };
  
  export const action = async ({ request }) => {
    let formData = await request.formData();
    const url = new URL(request.url);
    const currentPath = url.pathname.split('/').pop();
  
    try {
      const res = await execute(
        'post_player_comment',
        {
          player_id: formData.get("player_id"),
          comment: formData.get("comment"),
        }
      );
      if (!res.ok) throw res;
      
      // Return success and maintain current path
      return { ok: true, currentPath };
    } catch (error) {
      toast.error(i18n.t("errors.commentSaveFailed"))
      return { ok: false, error }
    }
  };

export const route = {
  element: <PlayerProfilePage />,
  loader,
  action,
  children: [
    {
      index: true,
      path: '',
      element: <PlayerDetailView />,
    },
    {
      path: 'sessions',
      element: <PlayerDetailView />,
    },
    {
      path: 'actions',
      element: <PlayerDetailView />,
    },
    {
      path: 'names',
      element: <PlayerDetailView />,
    },
    {
      path: 'comments',
      element: <PlayerDetailView />,
    },
    {
      path: 'logs',
      element: <PlayerDetailView />,
    },
  ],
};
