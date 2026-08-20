import * as React from "react";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  Divider,
  FormControlLabel,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import GroupRemoveIcon from "@mui/icons-material/GroupRemove";
import ErrorIcon from "@mui/icons-material/Error";
import CheckIcon from "@mui/icons-material/Check";
import ReplayRoundedIcon from "@mui/icons-material/ReplayRounded";
import FactCheckRoundedIcon from "@mui/icons-material/FactCheckRounded";
import { Link } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useTranslation } from "react-i18next";
import { teamsLiveQueryOptions } from "@/queries/teams-live-query";
import { gameQueryOptions } from "@/queries/game-query";
import { cmd } from "@/utils/fetchUtils";
import { useThemedImages } from "@/hooks/useThemedImages";
import { useAuth } from "@/hooks/useAuth";
import AdminActionContext, {
  useAdminActionContext,
} from "@/components/shared/AdminActionContext";
import { ReasonField } from "./fields/ReasonField";

const UNASSIGNED = "unassigned";
const OUTCOME = Object.freeze({
  PENDING: "pending",
  ERROR: "error",
  SUCCESS: "success",
});

const getOptionId = (option) => `${option.team}-${option.unit_name}`;

export default function DisbandSquadDialog() {
  const { t } = useTranslation();
  const themedImg = useThemedImages();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));
  const { permissions } = useAuth();
  const actionContext = useAdminActionContext();
  const [dialogOpen, setDialogOpen] = React.useState(false);
  const [step, setStep] = React.useState("selection");
  const [reviewTargets, setReviewTargets] = React.useState([]);
  const [reviewReason, setReviewReason] = React.useState("");
  const [outcomes, setOutcomes] = React.useState(new Map());
  const [isExecuting, setIsExecuting] = React.useState(false);

  const { data: teamData, refetch: refetchTeamData } = useQuery({
    ...teamsLiveQueryOptions,
  });
  const { data: gameState } = useQuery({ ...gameQueryOptions.state() });

  const canDisband = Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some(
        (entry) => entry.permission === "can_disband_squad"
      )
  );
  const canViewAudit = Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some(
        (entry) => entry.permission === "can_view_audit_logs"
      )
  );

  const { mutateAsync: disbandSquad } = useMutation({
    mutationFn: (data) =>
      cmd.DISBAND_SQUAD({
        payload: {
          team_name: data.team,
          squad_name: data.unit_name,
          reason: data.reason,
        },
        throwRouteError: false,
      }),
  });

  const unitOptions = React.useMemo(() => {
    const units = [];
    for (const team in teamData || {}) {
      for (const unitName in teamData[team].squads) {
        const unit = teamData[team].squads[unitName];
        if (unitName === UNASSIGNED) continue;
        units.push({
          team,
          faction: gameState?.current_map?.map?.[team]?.name,
          unit_name: unitName,
          type: unit.type,
          count: unit.players.length,
          leader:
            unit.players.find((player) =>
              ["officer", "tankcommander", "spotter"].includes(player.role)
            )?.name ?? "",
        });
      }
    }
    return units.sort((a, b) =>
      `${a.team}-${a.unit_name}`.localeCompare(`${b.team}-${b.unit_name}`)
    );
  }, [teamData, gameState]);

  const {
    handleSubmit,
    formState: { errors: formErrors },
    setValue,
    watch,
    reset,
    ...formProps
  } = useForm({ defaultValues: { reason: "", squads: [] } });
  const selectedSquads = watch("squads");
  const selectedSquadsSet = new Set(selectedSquads);
  const getIdOption = React.useCallback(
    (id) => unitOptions.find((option) => getOptionId(option) === id),
    [unitOptions]
  );

  React.useEffect(() => {
    const available = new Set(unitOptions.map(getOptionId));
    const filtered = selectedSquads.filter((id) => available.has(id));
    if (filtered.length !== selectedSquads.length) setValue("squads", filtered);
  }, [unitOptions, selectedSquads, setValue]);

  const openDialog = () => {
    reset({ reason: "", squads: [] });
    setReviewTargets([]);
    setReviewReason("");
    setOutcomes(new Map());
    setStep("selection");
    setDialogOpen(true);
  };

  const closeDialog = () => {
    if (!isExecuting) setDialogOpen(false);
  };

  const toggleUnit = (option) => {
    const id = getOptionId(option);
    setValue(
      "squads",
      selectedSquadsSet.has(id)
        ? selectedSquads.filter((value) => value !== id)
        : [...selectedSquads, id],
      { shouldValidate: true }
    );
  };

  const toggleTeam = (team) => () => {
    const ids = unitOptions
      .filter((option) => option.team === team)
      .map(getOptionId);
    const allSelected = ids.every((id) => selectedSquadsSet.has(id));
    setValue(
      "squads",
      allSelected
        ? selectedSquads.filter((id) => !ids.includes(id))
        : [...new Set([...selectedSquads, ...ids])],
      { shouldValidate: true }
    );
  };

  const prepareReview = (data) => {
    const targets = data.squads.map(getIdOption).filter(Boolean);
    setReviewTargets(targets);
    setReviewReason(data.reason);
    setOutcomes(new Map());
    setStep("review");
  };

  const executeTargets = async (targets) => {
    if (!actionContext.canExecute || targets.length === 0) return;
    setIsExecuting(true);
    setOutcomes((previous) => {
      const next = new Map(previous);
      targets.forEach((target) =>
        next.set(getOptionId(target), { state: OUTCOME.PENDING, message: null })
      );
      return next;
    });

    await Promise.all(
      targets.map(async (target) => {
        const id = getOptionId(target);
        try {
          const result = await disbandSquad({
            ...target,
            reason: reviewReason,
          });
          if (result?.failed) {
            throw new Error(result.error || t("actions.disband.commandFailed"));
          }
          setOutcomes((previous) => {
            const next = new Map(previous);
            next.set(id, { state: OUTCOME.SUCCESS, message: null });
            return next;
          });
        } catch (error) {
          setOutcomes((previous) => {
            const next = new Map(previous);
            next.set(id, {
              state: OUTCOME.ERROR,
              message: error?.message || t("errors.unexpected"),
            });
            return next;
          });
        }
      })
    );

    setIsExecuting(false);
    setStep("results");
    await refetchTeamData();
  };

  const failedTargets = reviewTargets.filter(
    (target) => outcomes.get(getOptionId(target))?.state === OUTCOME.ERROR
  );
  const successfulCount = reviewTargets.filter(
    (target) => outcomes.get(getOptionId(target))?.state === OUTCOME.SUCCESS
  ).length;

  const tooltip = !canDisband
    ? t("actions.disband.permissionMissing")
    : unitOptions.length === 0
    ? t("actions.disband.noSquads")
    : t("actions.disbandSquad");

  return (
    <>
      <Tooltip title={tooltip} describeChild>
        <span>
          <IconButton
            aria-label={t("actions.disbandSquad")}
            onClick={openDialog}
            disabled={!canDisband || unitOptions.length === 0}
          >
            <GroupRemoveIcon />
          </IconButton>
        </span>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        fullScreen={fullScreen}
        maxWidth="md"
        fullWidth
        onClose={closeDialog}
        slotProps={{
          paper: {
            component: "form",
            onSubmit: handleSubmit(prepareReview),
          },
        }}
      >
        <DialogTitle>{t("actions.disband.title")}</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <AdminActionContext context={actionContext} />

            {step === "selection" && (
              <>
                <DialogContentText>
                  {t("actions.disband.effect")}
                </DialogContentText>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  divider={<Divider flexItem orientation="vertical" />}
                  sx={{
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 2,
                  }}
                >
                  {["allies", "axis"].map((team) => {
                    const teamUnits = unitOptions.filter(
                      (option) => option.team === team
                    );
                    const selectedCount = teamUnits.filter((option) =>
                      selectedSquadsSet.has(getOptionId(option))
                    ).length;
                    return (
                      <Stack flex="1 1 50%" minWidth={0} key={team}>
                        <FormControlLabel
                          sx={{ px: 2, minHeight: 48 }}
                          label={
                            <Typography variant="h6">
                              {t(`views.team.factions.${team}`)}
                            </Typography>
                          }
                          control={
                            <Checkbox
                              disabled={teamUnits.length === 0}
                              checked={
                                teamUnits.length > 0 &&
                                selectedCount === teamUnits.length
                              }
                              indeterminate={
                                selectedCount > 0 &&
                                selectedCount < teamUnits.length
                              }
                              onChange={toggleTeam(team)}
                            />
                          }
                        />
                        <Divider />
                        <List
                          sx={{
                            maxHeight: fullScreen ? "unset" : 300,
                            overflowY: "auto",
                          }}
                        >
                          {teamUnits.length === 0 && (
                            <ListItem>
                              <ListItemText
                                secondary={t("actions.disband.noSquads")}
                              />
                            </ListItem>
                          )}
                          {teamUnits.map((option) => (
                            <ListItem key={getOptionId(option)} disablePadding>
                              <ListItemButton
                                onClick={() => toggleUnit(option)}
                              >
                                <Checkbox
                                  checked={selectedSquadsSet.has(
                                    getOptionId(option)
                                  )}
                                  tabIndex={-1}
                                  disableRipple
                                />
                                <Box
                                  component="img"
                                  src={themedImg.getRoleIconSrc(option.type)}
                                  alt=""
                                  width={20}
                                  height={20}
                                  sx={{ mr: 1 }}
                                />
                                <ListItemText
                                  primary={`${option.unit_name}${
                                    option.count ? ` (${option.count})` : ""
                                  }`}
                                  secondary={
                                    option.leader ||
                                    t("views.live.noSquadLeader")
                                  }
                                />
                              </ListItemButton>
                            </ListItem>
                          ))}
                        </List>
                      </Stack>
                    );
                  })}
                </Stack>
                <ReasonField
                  errors={formErrors}
                  setValue={setValue}
                  {...formProps}
                />
              </>
            )}

            {step === "review" && (
              <>
                <Alert severity="error" icon={<FactCheckRoundedIcon />}>
                  {t("actions.disband.reviewWarning", {
                    count: reviewTargets.length,
                  })}
                </Alert>
                <Box>
                  <Typography variant="overline" color="primary.light">
                    {t("actions.disband.targets")}
                  </Typography>
                  <List dense>
                    {reviewTargets.map((target) => (
                      <ListItem key={getOptionId(target)}>
                        <ListItemText
                          primary={`${t(
                            `views.team.factions.${target.team}`
                          )} · ${target.unit_name}`}
                          secondary={t("actions.disband.targetDetails", {
                            count: target.count,
                            leader:
                              target.leader || t("views.live.noSquadLeader"),
                          })}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
                <Box>
                  <Typography variant="overline" color="primary.light">
                    {t("fields.reason")}
                  </Typography>
                  <Typography sx={{ whiteSpace: "pre-wrap" }}>
                    {reviewReason}
                  </Typography>
                </Box>
                <Alert severity="warning">
                  {t("actions.disband.irreversible")}
                </Alert>
              </>
            )}

            {step === "results" && (
              <>
                <Alert severity={failedTargets.length ? "warning" : "success"}>
                  {t("actions.disband.resultSummary", {
                    success: successfulCount,
                    failed: failedTargets.length,
                  })}
                </Alert>
                <List aria-label={t("actions.disband.results")}>
                  {reviewTargets.map((target) => {
                    const outcome = outcomes.get(getOptionId(target));
                    return (
                      <ListItem key={getOptionId(target)}>
                        <Box sx={{ display: "flex", mr: 1 }}>
                          {outcome?.state === OUTCOME.SUCCESS ? (
                            <CheckIcon color="success" />
                          ) : outcome?.state === OUTCOME.ERROR ? (
                            <ErrorIcon color="error" />
                          ) : (
                            <CircularProgress size={20} />
                          )}
                        </Box>
                        <ListItemText
                          primary={`${t(
                            `views.team.factions.${target.team}`
                          )} · ${target.unit_name}`}
                          secondary={
                            outcome?.state === OUTCOME.ERROR
                              ? outcome.message
                              : t(
                                  `actions.disband.outcome.${
                                    outcome?.state || OUTCOME.PENDING
                                  }`
                                )
                          }
                        />
                      </ListItem>
                    );
                  })}
                </List>
              </>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ flexWrap: "wrap" }}>
          {step === "selection" && (
            <>
              <Button onClick={closeDialog}>{t("common.cancel")}</Button>
              <Button
                type="submit"
                variant="contained"
                disabled={selectedSquads.length === 0}
              >
                {t("actions.disband.review")}
              </Button>
            </>
          )}
          {step === "review" && (
            <>
              <Button
                onClick={() => setStep("selection")}
                disabled={isExecuting}
              >
                {t("common.previous")}
              </Button>
              <Button
                type="button"
                color="error"
                variant="contained"
                onClick={() => executeTargets(reviewTargets)}
                disabled={isExecuting || !actionContext.canExecute}
              >
                {isExecuting
                  ? t("common.processing")
                  : t("actions.disband.execute", {
                      count: reviewTargets.length,
                    })}
              </Button>
            </>
          )}
          {step === "results" && (
            <>
              <Tooltip
                title={
                  canViewAudit
                    ? ""
                    : t("actions.disband.auditPermissionMissing")
                }
              >
                <span>
                  <Button
                    component={canViewAudit ? Link : "button"}
                    to={
                      canViewAudit
                        ? "/records/audit-logs?commands=disband_squad_by_name"
                        : undefined
                    }
                    onClick={canViewAudit ? closeDialog : undefined}
                    disabled={!canViewAudit}
                  >
                    {t("actions.disband.openAudit")}
                  </Button>
                </span>
              </Tooltip>
              {failedTargets.length > 0 && (
                <Button
                  startIcon={<ReplayRoundedIcon />}
                  onClick={() => executeTargets(failedTargets)}
                  disabled={isExecuting || !actionContext.canExecute}
                >
                  {t("actions.disband.retryFailed", {
                    count: failedTargets.length,
                  })}
                </Button>
              )}
              <Button variant="contained" onClick={closeDialog}>
                {t("common.close")}
              </Button>
            </>
          )}
        </DialogActions>
      </Dialog>
    </>
  );
}
