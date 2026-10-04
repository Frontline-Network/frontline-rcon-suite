import { getPlayerIdentity } from "./player-identity.mjs";

// A non-Steam/EOS ID does not identify an Xbox account. Without platform
// metadata the legacy callers can only safely link a valid SteamID64.
const makePlayerProfileUrl = (playerId, name = "", player = {}) =>
  getPlayerIdentity({ ...player, player_id: playerId, name }).profileUrl || undefined;

export default makePlayerProfileUrl;
