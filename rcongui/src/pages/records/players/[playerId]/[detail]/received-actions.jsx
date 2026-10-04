import { useLoaderData } from "react-router-dom";
import { FilterSection, ScrollableContent, ListItem } from "../styled";
import { TextField, MenuItem, Typography } from "@mui/material";
import dayjs from "dayjs";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const formatDate = (dateString) => {
  return dayjs(dateString).format("lll");
};

const ReceivedActions = () => {
  const { t } = useTranslation();
  const { profile } = useLoaderData();
  const [filters, setFilters] = useState({
    actions: {
      search: "",
      type: "",
    },
  });

  const handleFilterChange = (key, subKey, value) => {
    setFilters((prev) => ({ ...prev, [key]: { ...prev[key], [subKey]: value } }));
  };

  const filteredActions = profile.received_actions.filter((item) => {
    const searchLower = filters.actions.search.toLowerCase();
    return (
      item.action_type.includes(filters.actions.type) &&
      (item.reason.toLowerCase().includes(searchLower) || item.by.toLowerCase().includes(searchLower))
    );
  });

  return (
    <div>
      <FilterSection className="wardogs-profile-filters">
        <TextField
          label={t("records.playerDetails.searchActions")}
          value={filters.actions.search}
          onChange={(e) =>
            handleFilterChange("actions", "search", e.target.value)
          }
          size="small"
        />
        <TextField
          select
          label={t("records.playerDetails.actionType")}
          value={filters.actions.type}
          onChange={(e) =>
            handleFilterChange("actions", "type", e.target.value)
          }
          size="small"
        >
          <MenuItem value="">{t("common.all")}</MenuItem>
          <MenuItem value="TEMPBAN">{t("actions.types.TEMPBAN")}</MenuItem>
          <MenuItem value="PERMABAN">{t("actions.types.PERMABAN")}</MenuItem>
          <MenuItem value="PUNISH">{t("actions.types.PUNISH")}</MenuItem>
          <MenuItem value="KICK">{t("actions.types.KICK")}</MenuItem>
          <MenuItem value="MESSAGE">{t("actions.types.MESSAGE")}</MenuItem>
        </TextField>
      </FilterSection>
      <ScrollableContent className="wardogs-profile-scroll">
        {filteredActions.map(
          (action, index) => (
            <ListItem key={index}>
              <Typography variant="subtitle1">
                {t(`actions.types.${action.action_type}`, { defaultValue: action.action_type })}
              </Typography>
              <Typography>{t("records.playerDetails.reason")}: {action.reason}</Typography>
              <Typography>{t("records.playerDetails.by")}: {action.by}</Typography>
              <Typography>{t("records.playerDetails.time")}: {formatDate(action.time)}</Typography>
            </ListItem>
          )
        )}
      </ScrollableContent>
    </div>
  );
};

export default ReceivedActions;
