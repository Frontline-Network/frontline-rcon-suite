import { useMemo, useState, useEffect } from "react";
import Box from "@mui/material/Box";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemText from "@mui/material/ListItemText";
import { cmd } from "@/utils/fetchUtils";
import { useLoaderData, useSubmit } from "react-router-dom";
import { FixedSizeList } from "react-window";
import {
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  IconButton,
  ListItemIcon,
  Paper,
  Stack,
  TextField,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import DeleteIcon from "@mui/icons-material/Delete";
import SplitButton from "@/components/shared/SplitButton";
import { SearchInput } from "@/components/shared/SearchInput";
import debounce from "lodash/debounce";
import { InputFileUpload } from "@/components/shared/InputFileUpload";
import exportFile from "@/utils/exportFile";
import { isFakeMode } from "@/mirage/demo-data";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import ConfirmButton from "@/components/shared/ConfirmButton";

const INTENT = {
  SINGLE: 0,
  ALL: 1,
};

export const loader = async () => {
  const profanities = isFakeMode() ? ["beleidigung-demo", "spam-demo"] : await cmd.GET_PROFANITIES();
  return { profanities };
};

export const action = async ({ request }) => {
  const { profanities, ...rest } = Object.fromEntries(await request.formData());
  const payload = { profanities: profanities.length ? profanities.split(",") : [], ...rest };
  const result = await cmd.SET_PROFANITIES({ payload });
  return result;
};

const ProfanityFilter = () => {
  const { t } = useTranslation();
  const { profanities: serverProfanities } = useLoaderData();
  const [profanities, setProfanities] = useState(serverProfanities);
  const [checked, setChecked] = useState([]);
  const [searched, setSearched] = useState("");
  const [newProfanity, setNewProfanity] = useState("");
  const submit = useSubmit();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  const filteredProfanities = useMemo(
    () =>
      profanities.filter((word) =>
        word.toLowerCase().includes(searched.toLowerCase())
      ),
    [profanities, searched]
  );

  const handleToggle = (value) => () => {
    const currentIndex = checked.indexOf(value);
    const newChecked = [...checked];

    if (currentIndex === -1) {
      newChecked.push(value);
    } else {
      newChecked.splice(currentIndex, 1);
    }

    setChecked(newChecked);
  };

  const handleAddProfanity = () => {
    const word = newProfanity.trim()
    if (word) {
      setProfanities((prev) => [word, ...prev]);
      setNewProfanity("");
    }
  };

  const handleDeleteSingleProfanity = (word) => {
    setProfanities((prev) => prev.filter((entry) => entry !== word));
    setChecked((prev) => prev.filter((entry) => entry !== word));
  };

  const handleDeleteSelectedProfanities = () => {
    setProfanities((prev) => prev.filter((word) => !checked.includes(word)));
    setChecked([]);
  };

  const handleToggleSelectAll = (e) => {
    if (e.target.checked) {
      setChecked(filteredProfanities);
    } else {
      setChecked([]);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    const reader = new FileReader();

    reader.onload = (e) => {
      const text = e.target.result;
      const uploadedProfanities = text.split("\n");
      setProfanities(uploadedProfanities);
    };

    reader.readAsText(file);
  };

  const handleFileDownload = () => {
    exportFile(profanities, "profanities");
  };

  const submitChanges = (intent) => () => {
    const formData = new FormData();
    formData.append("profanities", profanities);
    console.log(profanities);
    if (intent === INTENT.ALL) {
      formData.append("forward", true);
    }
    submit(formData, { method: "POST" });
  };

  const onSearchedChange = debounce((event) => {
    setSearched(event.target.value);
  }, 500);

  useEffect(() => {
    setProfanities(serverProfanities);
  }, [serverProfanities]);

  return (
    <Box
      sx={{
        maxWidth: (theme) => theme.breakpoints.values.lg,
        minWidth: 0,
        pb: { xs: 10, md: 0 },
      }}
    >
      <PageHeader
        eyebrow={t("settings.profanity.eyebrow")}
        title={t("settings.profanity.title")}
        subtitle={t("settings.profanity.subtitle")}
      />
      <Stack
        component={Paper}
        direction={{ xs: "column", sm: "row" }}
        sx={{ p: 1, mb: 1 }}
        justifyContent="end"
        alignItems={"center"}
        gap={1}
      >
        <InputFileUpload
          text={t("settings.profanity.upload")}
          color={"secondary"}
          onChange={handleFileUpload}
          accept={".txt"}
          sx={{ minHeight: 44, width: { xs: "100%", sm: "auto" } }}
        />
        <Button
          onClick={handleFileDownload}
          variant="contained"
          color="secondary"
          sx={{ minHeight: 44, width: { xs: "100%", sm: "auto" } }}
        >
          {t("settings.profanity.download")}
        </Button>
        <Box sx={{ width: { xs: "100%", sm: "auto" } }}>
          {compact ? (
            <Stack direction="row" gap={1}>
              <Button
                variant="contained"
                onClick={submitChanges(INTENT.SINGLE)}
                sx={{ flex: 1, minHeight: 44 }}
              >
                {t("settings.profanity.apply")}
              </Button>
              <ConfirmButton
                onConfirm={submitChanges(INTENT.ALL)}
                title={t("settings.profanity.applyAllTitle")}
                description={t("settings.profanity.applyAllDescription")}
                buttonText={t("settings.profanity.allServers")}
                buttonProps={{ variant: "outlined", sx: { minHeight: 44, whiteSpace: "nowrap" } }}
              />
            </Stack>
          ) : <SplitButton
            options={[
              {
                name: t("settings.profanity.apply"),
                buttonProps: {
                  onClick: submitChanges(INTENT.SINGLE),
                },
              },
              {
                name: t("settings.profanity.applyAllServers"),
                buttonProps: {
                  onClick: submitChanges(INTENT.ALL),
                },
              },
            ]}
          />}
        </Box>
      </Stack>
      <Stack
        direction={"column"}
        gap={1}
        sx={{
          width: "100%",
          bgcolor: "background.paper",
          padding: 1,
        }}
      >
        <Stack direction={{ xs: "column", sm: "row" }} gap={1} sx={{ mb: 1, p: 0.5 }}>
          <TextField
            autoComplete={"off"}
            value={newProfanity}
            onChange={(e) => setNewProfanity(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAddProfanity()}
            variant="standard"
            fullWidth
            label={t("settings.profanity.newEntry")}
          />
          <Button onClick={handleAddProfanity} variant="contained" sx={{ minHeight: 44 }}>
            {t("settings.profanity.add")}
          </Button>
        </Stack>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "stretch", sm: "center" }}
          justifyContent={"space-between"}
          gap={1}
          sx={{ mb: 1, p: 0.5 }}
        >
          <FormControlLabel
            sx={{ px: 0.25 }}
            label={t("settings.profanity.select")}
            control={
              <Checkbox
                sx={{ mr: 1, "& .MuiSvgIcon-root": { fontSize: 16 } }}
                checked={
                  checked.length === filteredProfanities.length &&
                  checked.length !== 0
                }
                indeterminate={
                  checked.length > 0 &&
                  checked.length !== filteredProfanities.length
                }
                size="small"
                onChange={handleToggleSelectAll}
              />
            }
          />
          <Divider orientation={compact ? "horizontal" : "vertical"} flexItem />
          <SearchInput
            onChange={onSearchedChange}
            placeholder={t("settings.profanity.search")}
          />
          <Divider orientation={compact ? "horizontal" : "vertical"} flexItem />
          <Button
            onClick={handleDeleteSelectedProfanities}
            variant="contained"
            color="warning"
            disabled={!checked.length}
            sx={{ minWidth: "fit-content", minHeight: 44 }}
          >
            {t("settings.profanity.deleteSelected")}
          </Button>
        </Stack>
        <Divider orientation="horizontal" />
        <FixedSizeList
          height={compact ? 460 : 600}
          itemSize={compact ? 48 : 40}
          itemCount={filteredProfanities.length}
          itemData={filteredProfanities}
          overscanCount={5}
        >
          {({ index, style }) => {
            const labelId = `checkbox-list-label-${index}`;
            return (
              <ListItem
                key={index}
                style={style}
                disablePadding
                secondaryAction={
                  <IconButton
                    aria-label={`${t("common.delete")} ${filteredProfanities[index]}`}
                    onClick={() => handleDeleteSingleProfanity(filteredProfanities[index])}
                    sx={{ minWidth: 44, minHeight: 44 }}
                  >
                    <DeleteIcon />
                  </IconButton>
                }
              >
                <ListItemButton
                  role={undefined}
                  onClick={handleToggle(filteredProfanities[index])}
                  dense
                >
                  <ListItemIcon>
                    <Checkbox
                      edge="start"
                      checked={checked.includes(filteredProfanities[index])}
                      tabIndex={-1}
                      disableRipple
                      inputProps={{ "aria-labelledby": labelId }}
                    />
                  </ListItemIcon>
                  <ListItemText
                    id={labelId}
                    primary={filteredProfanities[index]}
                  />
                </ListItemButton>
              </ListItem>
            );
          }}
        </FixedSizeList>
      </Stack>
    </Box>
  );
};

export default ProfanityFilter;
