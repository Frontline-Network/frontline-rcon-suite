import { Button, FormControl, FormControlLabel, InputLabel, MenuItem, Select, Switch, TextField } from "@mui/material";
import Grid from "@mui/material/Grid2";
import {useState} from "react";
import { useTranslation } from "react-i18next";

const BlacklistRecordsSearch = ({
  blacklists,
  onSearch,
  disabled,
}) => {
  const { t } = useTranslation();
  const [playerIdQuery, setPlayerIdQuery] = useState("");
  const [reasonQuery, setReasonQuery] = useState("");
  const [blacklistQuery, setBlacklistQuery] = useState("");
  const [excludeExpired, setExcludeExpired] = useState(false);
  const [pageSize, setPageSize] = useState(50);

  return (
    (<form>
      <Grid
        container
        spacing={2}
        alignContent="center"
        alignItems="center"
        justifyContent="space-evenly"
      >
        <Grid size={{ xs: 12, md: 4 }}>
          <TextField
            fullWidth
            label={t("records.blacklists.searchPlayerId")}
            value={playerIdQuery}
            onChange={(e) => setPlayerIdQuery(e.target.value)}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <TextField
            fullWidth
            label={t("records.blacklists.searchNameReason")}
            value={reasonQuery}
            onChange={(e) => setReasonQuery(e.target.value)}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <FormControl fullWidth>
            <InputLabel>{t("records.blacklists.list")}</InputLabel>
            <Select
              value={blacklistQuery}
              onChange={(e) => setBlacklistQuery(e.target.value)}
            >
              <MenuItem key={""} value={""} style={{minHeight: 36}}>{" "}</MenuItem>
              { blacklists.map(
                (b) => <MenuItem key={b.id} value={b.id}>{b.name}</MenuItem>
              ) }
            </Select>
          </FormControl>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <FormControlLabel
            control={
              <Switch
                checked={!excludeExpired}
                onChange={(e) => setExcludeExpired(!e.target.checked)}
                color="primary"
              />
            }
            label={t("records.blacklists.showExpired")}
            labelPlacement="top"
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 2 }}>
          <FormControl fullWidth>
            <InputLabel>{t("common.pagination.pageSize")}</InputLabel>
            <Select
              value={pageSize}
              onChange={(e) => setPageSize(e.target.value)}
            >
              <MenuItem value={10}>10</MenuItem>
              <MenuItem value={20}>20</MenuItem>
              <MenuItem value={30}>30</MenuItem>
              <MenuItem value={40}>40</MenuItem>
              <MenuItem value={50}>50</MenuItem>
              <MenuItem value={100}>100</MenuItem>
              <MenuItem value={200}>200</MenuItem>
              <MenuItem value={500}>500</MenuItem>
              <MenuItem value={1000}>1000</MenuItem>
            </Select>
          </FormControl>
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <Button
            type="submit"
            disabled={disabled}
            variant="contained"
            color="primary"
            size="large"
            onClick={(e) => {
              e.preventDefault();
              onSearch({
                player_id: playerIdQuery,
                reason: reasonQuery,
                blacklist_id: blacklistQuery === "" ? null : blacklistQuery,
                exclude_expired: excludeExpired,
                page_size: pageSize,
              });
            }}
          >
            {t("common.search")}
          </Button>
        </Grid>
      </Grid>
    </form>)
  );
}

export default BlacklistRecordsSearch;
