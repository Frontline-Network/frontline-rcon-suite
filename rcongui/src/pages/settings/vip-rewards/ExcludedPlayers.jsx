import { useEffect, useState } from "react";
import { Autocomplete, Box, Chip, TextField, Typography } from "@mui/material";
import { cmd } from "@/utils/fetchUtils";

const nameOf = (p) => p.names?.[0]?.name || p.name || "Unbekannter Spieler";
async function findPlayers(params) {
  const response = await cmd.GET_PLAYERS_RECORDS({
    payload: { page: 1, page_size: 15, ignore_accent: true, ...params },
  });
  if (
    response?.failed ||
    response?.result?.failed ||
    !Array.isArray(response?.result?.players)
  )
    throw new Error("Spielersuche nicht verfügbar");
  return response.result.players;
}
export default function ExcludedPlayers({ value, onChange }) {
  const [input, setInput] = useState("");
  const [options, setOptions] = useState([]);
  const [known, setKnown] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const idsKey = JSON.stringify(value);
  useEffect(() => {
    let active = true;
    // Resolve stored IDs in small batches; missing records remain removable.
    const ids = JSON.parse(idsKey);
    (async () => {
      for (let i = 0; i < ids.length && active; i += 5) {
        await Promise.all(
          ids.slice(i, i + 5).map(async (id) => {
            try {
              const rows = await findPlayers({ player_id: id });
              const player = rows.find((p) => p.player_id === id);
              if (active && player)
                setKnown((prev) => ({ ...prev, [id]: player }));
            } catch {
              /* Keep existing exclusions even when records cannot be read. */
            }
          })
        );
      }
    })();
    return () => {
      active = false;
    };
  }, [idsKey]);
  useEffect(() => {
    let active = true;
    setOptions([]);
    setError("");
    setLoading(false);
    const query = input.trim();
    if (query.length < 2) return;
    setLoading(true);
    const timer = setTimeout(async () => {
      try {
        const rows = await findPlayers(
          /^(?:[0-9]{17}|[a-f0-9]{32})$/i.test(query)
            ? { player_id: query }
            : { player_name: query, exact_name_match: false }
        );
        if (active) {
          setOptions(rows);
          setKnown((prev) => ({
            ...prev,
            ...Object.fromEntries(rows.map((p) => [p.player_id, p])),
          }));
        }
      } catch {
        if (active)
          setError("Spielersuche fehlgeschlagen. Bitte erneut versuchen.");
      } finally {
        if (active) setLoading(false);
      }
    }, 350);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [input]);
  return (
    <Autocomplete
      multiple
      filterSelectedOptions
      options={options}
      loading={loading}
      loadingText="Spieler werden gesucht …"
      inputValue={input}
      value={value.map((id) => known[id] || { player_id: id })}
      filterOptions={(rows) => rows}
      isOptionEqualToValue={(a, b) => a.player_id === b.player_id}
      getOptionLabel={(p) => nameOf(p)}
      onInputChange={(_, text, reason) => {
        if (reason === "input" || reason === "clear") setInput(text);
      }}
      onChange={(_, players) => {
        setInput("");
        onChange([...new Set(players.map((p) => p.player_id))]);
      }}
      noOptionsText={
        input.trim().length < 2
          ? "Mindestens zwei Zeichen eingeben"
          : "Keine Spieler gefunden"
      }
      renderOption={({ key, ...props }, p) => (
        <Box component="li" key={p.player_id} {...props}>
          <Box sx={{ minWidth: 0 }}>
            <Typography>{nameOf(p)}</Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ overflowWrap: "anywhere" }}
            >
              {p.player_id}
            </Typography>
          </Box>
        </Box>
      )}
      renderTags={(players, getTagProps) =>
        players.map((p, i) => {
          const { key, ...props } = getTagProps({ index: i });
          return (
            <Chip
              key={p.player_id}
              {...props}
              title={p.player_id}
              label={known[p.player_id] ? nameOf(p) : p.player_id}
              sx={{ maxWidth: "100%" }}
            />
          );
        })
      }
      renderInput={(params) => (
        <TextField
          {...params}
          label="Ausgeschlossene Spieler"
          error={!!error}
          helperText={
            error ||
            "Nach Spielernamen oder ID suchen und auswählen. Ausgewählte Spieler erhalten keine dieser VIP-Belohnungen. Die Spielerakte bleibt unverändert."
          }
        />
      )}
      sx={{ mt: 2, minWidth: 0 }}
    />
  );
}
