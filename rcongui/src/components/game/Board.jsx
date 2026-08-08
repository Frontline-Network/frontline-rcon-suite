import { Typography, Divider, Stack, Box } from "@mui/material";
import { styled } from "@mui/material";
import Grid from "@mui/material/Grid2";
import { useThemedImages } from "@/hooks/useThemedImages";

const StyledStack = styled(Stack)(({ theme }) => ({
  padding: 0,
  maxWidth: theme.breakpoints.values.md,
  margin: "0 auto",
  [theme.breakpoints.up("md")]: {
    paddingRight: theme.spacing(1),
    paddingLeft: theme.spacing(1),
  },
}));

const SmallText = styled(Typography)(({ theme }) => ({
  fontSize: theme.typography.pxToRem(12),
}));

/**
 * @typedef {Object} BoardData
 * @property {string} raw_time_remaining - The raw time remaining.
 * @property {number} allied_score - The allied score.
 * @property {number} axis_score - The axis score.
 * @property {Object} current_map - The current map.
 * @property {number} num_allied_players - The number of allied players.
 * @property {number} num_axis_players - The number of axis players.
 */

/**
 * 
 * @param {BoardData} data - The data object containing the game information.
 * @param {Object} props - Additional props.
 * @returns {JSX.Element} The rendered Board component.
 */
export const Board = ({ data, ...props }) => {
  const themedImg = useThemedImages()
  const boardData = data ?? {};
  // A server can briefly return an incomplete public game state while a map
  // is loading or when the game connection is reconnecting. Keep the board
  // useful in that state instead of crashing the whole route while reading
  // faction names from an undefined map object.
  const currentMap = data?.current_map ?? {};
  const map = currentMap.map ?? {};
  const alliesName = map.allies?.name;
  const axisName = map.axis?.name;
  const mapName = currentMap.pretty_name ?? map.pretty_name ?? "Unknown Map";
  const gameMode = currentMap.game_mode?.toUpperCase() ?? "—";

  return (
    <StyledStack>
      <SmallText textAlign={"center"} fontWeight={"bold"}>
        {boardData.raw_time_remaining ?? "—"}
      </SmallText>
      <Divider variant="middle" />
      <Grid
        container
        columnSpacing={1}
        justifyContent={"center"}
        sx={{ py: 0.5 }}
        alignContent={"center"}
      >
        <Grid
          size={4}
          sx={{
            display: "flex",
            justifyContent: "start",
            alignItems: "start",
          }}
        >
          {alliesName ? (
            <Box
              width={24}
              height={24}
              component={"img"}
              alt="Allies"
              src={themedImg.getFactionIconSrc(alliesName)}
            />
          ) : null}
        </Grid>
        <Grid container sx={{ textAlign: "center" }} size={4}>
          <Grid size={5}>
            <Typography component={"span"} fontWeight={"bold"}>{boardData.allied_score ?? 0}</Typography>
          </Grid>
          <Grid size={2}>
            <Typography component={"span"}>:</Typography>
          </Grid>
          <Grid size={5}>
            <Typography component={"span"} fontWeight={"bold"}>{boardData.axis_score ?? 0}</Typography>
          </Grid>
        </Grid>
        <Grid
          size={4}
          sx={{
            display: "flex",
            justifyContent: "end",
            alignItems: "start",
          }}
        >
          {axisName ? (
            <Box
              width={24}
              height={24}
              component={"img"}
              alt="Axis"
              src={themedImg.getFactionIconSrc(axisName)}
            />
          ) : null}
        </Grid>
      </Grid>
      <Divider variant="middle" />
      <Grid container>
        <Grid size={3}>
          <SmallText textAlign={"left"} sx={{ pl: 0.75 }}>
            {`[${boardData.num_allied_players ?? 0}]`}
          </SmallText>
        </Grid>
        <Grid size={6}>
          <SmallText textAlign={"center"}>
            {mapName}
          </SmallText>
        </Grid>
        <Grid size={3}>
          <SmallText textAlign={"right"} sx={{ pr: 0.75 }}>
            {`[${boardData.num_axis_players ?? 0}]`}
          </SmallText>
        </Grid>
      </Grid>
      <Grid size={12}>
        <SmallText textAlign={"center"}>
          {gameMode}
        </SmallText>
      </Grid>
    </StyledStack>
  );
};
