import { lazy, Suspense, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import { Form, json, useActionData, useLoaderData } from "react-router-dom";
import {
  Button,
  InputBase,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Skeleton,
  Stack,
  styled,
  TextField,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { cmd } from "@/utils/fetchUtils";
import SearchIcon from "@mui/icons-material/Search";
import AddIcon from "@mui/icons-material/Add";
import CancelIcon from "@mui/icons-material/Cancel";
import EditIcon from "@mui/icons-material/Edit";
import DeleteIcon from "@mui/icons-material/Delete";
import SaveIcon from "@mui/icons-material/Save";
import SaveAsIcon from "@mui/icons-material/SaveAs";
import dayjs from "dayjs";
import debounce from "lodash/debounce";
import { BroadcastFields } from "@/components/shared/BroadcastFields";
import { parseBroadcastMessages, unpackBroadcastMessage } from "@/utils/lib";
import { useTheme } from "@mui/material/styles";
import { isFakeMode } from "@/mirage/demo-data";
import { useTranslation } from "react-i18next";

const Editor = lazy(() => import("@monaco-editor/react"));

const MODE = {
  READ: 0,
  EDIT: 1,
  CREATE: 2,
};

const INTENT = {
  CREATE: "create",
  UPDATE: "update",
  DELETE: "delete",
};

const initialState = {
  mode: MODE.READ,
  id: 0,
  title: "",
  content: "",
};

export const loader = async ({ params }) => {
  const { category } = params;
  if (isFakeMode()) {
    return { category, messages: [{ id: 1, title: "Frontline Standard", content: "Willkommen beim Frontline Network.", updated_at: new Date().toISOString(), updated_by: "Frontline Admin" }] };
  }
  const messages = await cmd.GET_MESSAGE_TEMPLATES({ params });
  messages.reverse(); // sort desc by updated_by
  return {
    category,
    messages,
  };
};

export const action = async ({ request }) => {
  const formData = Object.fromEntries(await request.formData());
  const { intent, category, ...message } = formData;

  const title = message.title;
  const content = message.content;
  const id = message.id;

  const hasTitle = !!title?.trim()?.length;
  const hasContent = !!content?.trim()?.length;

  let data;

  switch (intent) {
    case INTENT.CREATE:
      if (!hasTitle || !hasContent) {
        throw json(
          {
            message: "Missing title or content message attributes.",
            error: "Form error",
            command: intent,
          },
          { status: 400 }
        );
      }
      data = await cmd.ADD_MESSAGE_TEMPLATE({
        payload: {
          title,
          content,
          category,
        },
      });
      return json({ intent, message: { ...data.arguments, id: data.result } });

    case INTENT.UPDATE:
      if (!hasTitle || !hasContent || !id) {
        throw json(
          {
            message: "Missing title, content or id message attributes.",
            error: "Form error",
            command: intent,
          },
          { status: 400 }
        );
      }
      data = await cmd.EDIT_MESSAGE_TEMPLATE({
        payload: {
          id,
          title,
          content,
          category,
        },
      });
      return json({ intent, message: data.arguments });

    case INTENT.DELETE:
      if (!id) {
        throw json(
          {
            message: "Missing id message attributes.",
            error: "Form error",
            command: intent,
          },
          { status: 400 }
        );
      }
      data = await cmd.DELETE_MESSAGE_TEMPLATE({ payload: { id } });
      return json({ intent, message: data.arguments });

    default:
      throw new Error("Invalid intent");
  }
};

const SearchWrapper = styled(Box)({
  display: "flex",
  alignItems: "center",
  justifyContent: "start",
  width: "100%",
});

const StyledTextField = styled(TextField)((theme) => ({
  "& .MuiOutlinedInput-root, & .MuiOutlinedInput-notchedOutline": {
    borderRadius: 0,
  },
}));

function EditorActions({ editor, actions, compact = false }) {
  const { t } = useTranslation();
  const canBeSaved = editor.title.trim() && editor.content.trim();

  if (editor.mode === MODE.READ) return null;

  return (
    <Box
      sx={(theme) => ({
        display: "flex",
        flexWrap: "wrap",
        gap: theme.spacing(0.75),
        justifyContent: "flex-end",
        padding: theme.spacing(1.5, 2),
        borderTop: "1px solid",
        borderColor: theme.palette.divider,
        bgcolor: theme.palette.background.default,
        ...(compact && {
          position: "sticky",
          bottom: "calc(64px + env(safe-area-inset-bottom))",
          zIndex: theme.zIndex.appBar,
          boxShadow: theme.shadows[8],
        }),
        "& .MuiButton-root": {
          minHeight: 44,
          ...(compact && { flex: "1 1 132px" }),
        },
      })}
    >
      {editor.mode === MODE.CREATE && (
        <>
          <Button
            variant="outlined"
            color="inherit"
            onClick={actions.cancelCreate}
            startIcon={<CancelIcon />}
          >
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            type="submit"
            name="intent"
            value={INTENT.CREATE}
            startIcon={<SaveIcon />}
            disabled={!canBeSaved}
          >
            {t("common.save")}
          </Button>
        </>
      )}
      {editor.mode === MODE.EDIT && (
        <>
          <Button
            variant="outlined"
            color="inherit"
            onClick={actions.cancelEdit}
            startIcon={<CancelIcon />}
          >
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            type="submit"
            name="intent"
            value={INTENT.UPDATE}
            startIcon={<SaveIcon />}
            disabled={!canBeSaved}
          >
            {t("common.save")}
          </Button>
          <Button
            variant="outlined"
            type="submit"
            name="intent"
            value={INTENT.CREATE}
            startIcon={<SaveAsIcon />}
            disabled={!canBeSaved}
          >
            {t("settings.templates.saveAsNew")}
          </Button>
        </>
      )}
    </Box>
  );
}

function EditorFields({ editor, category, setEditor, compact = false }) {
  const { t } = useTranslation();
  const theme = useTheme();

  const handleOnInputChange = (event) => {
    const key = event.target.name;
    setEditor((prev) => ({
      ...prev,
      [key]: event.target.value,
    }));
  };

  const handleOnBroadcastChange = (value) => {
    setEditor((prev) => ({
      ...prev,
      content: parseBroadcastMessages(value),
    }));
  };

  const handleAutosettingsChange = (value) => {
    setEditor((prev) => ({
      ...prev,
      content: value,
    }));
  };

  return (
    <>
      <input name="id" value={editor.id} hidden readOnly />
      <input name="category" value={category} hidden readOnly />
      {editor.mode === MODE.READ ? (
        editor.id ? (
          <Box
            component="section"
            aria-label={t("settings.templates.preview")}
            sx={{
              minHeight: { xs: 220, md: 300 },
              p: { xs: 1.5, sm: 2 },
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "background.default",
            }}
          >
            <Typography variant="overline" color="text.secondary">
              {t("settings.templates.messageContent")}
            </Typography>
            {category === "broadcast" ? (
              <Box sx={{ mt: 1.5 }}>
                <BroadcastFields
                  messages={unpackBroadcastMessage(editor.content ?? "")}
                  disabled
                  onChange={handleOnBroadcastChange}
                />
              </Box>
            ) : category === "auto_settings" ? (
              <Box
                component="pre"
                sx={{
                  m: 0,
                  mt: 1.5,
                  whiteSpace: "pre-wrap",
                  overflowWrap: "anywhere",
                  color: "text.primary",
                  fontFamily: "monospace",
                  fontSize: "0.875rem",
                  lineHeight: 1.65,
                }}
              >
                {editor.content}
              </Box>
            ) : (
              <Typography
                variant="body1"
                sx={{ mt: 1.5, whiteSpace: "pre-wrap", lineHeight: 1.75 }}
              >
                {editor.content}
              </Typography>
            )}
          </Box>
        ) : (
          <Stack
            alignItems="center"
            justifyContent="center"
            spacing={0.75}
            sx={{ minHeight: 300, px: 2, textAlign: "center" }}
          >
            <Typography variant="h6">
              {t("settings.templates.noSelection")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("settings.templates.noSelectionDescription")}
            </Typography>
          </Stack>
        )
      ) : (
        <Stack spacing={1.5}>
          <StyledTextField
            name="title"
            value={editor.title}
            onChange={handleOnInputChange}
            label={t("settings.templates.messageTitle")}
            placeholder={t("settings.templates.messageTitle")}
            fullWidth
            required
          />
          {category === "broadcast" ? (
            <BroadcastFields
              messages={unpackBroadcastMessage(editor.content ?? "")}
              onChange={handleOnBroadcastChange}
            />
          ) : category === "auto_settings" ? (
            <Suspense fallback={<Skeleton variant="rectangular" height="52vh" />}>
              <Editor
                height={compact ? "44vh" : "52vh"}
                defaultLanguage="json"
                value={editor.content}
                defaultValue=""
                theme={theme.palette.mode === "dark" ? "vs-dark" : "vs-light"}
                onChange={handleAutosettingsChange}
              />
            </Suspense>
          ) : (
            <StyledTextField
              name="content"
              value={editor.content}
              onChange={handleOnInputChange}
              label={t("settings.templates.messageContent")}
              placeholder={t("settings.templates.messageContent")}
              multiline
              minRows={compact ? 9 : 12}
              fullWidth
              required
            />
          )}
        </Stack>
      )}
    </>
  );
}

function MessageList({ messages, onMessageClick, selected, compact = false }) {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        minHeight: compact ? 0 : 280,
        maxHeight: compact ? "none" : "calc(100vh - 340px)",
        overflowY: compact ? "visible" : "auto",
        overflowX: compact ? "auto" : "hidden",
        scrollbarWidth: "thin",
        scrollbarGutter: "auto",
      }}
    >
      <List
        aria-label={t("settings.templates.library")}
        disablePadding={!compact}
        sx={
          compact
            ? {
                display: "flex",
                flexDirection: "row",
                gap: 1,
                p: 1,
                width: "max-content",
              }
            : undefined
        }
      >
        {messages.length ? (
          messages.map((message, index) => (
            <ListItem
              key={message.id}
              disablePadding
              sx={compact ? { width: 244, flex: "0 0 244px" } : undefined}
            >
              <ListItemButton
                onClick={() => onMessageClick(index)}
                selected={selected !== undefined && message.id === selected}
                sx={{
                  minHeight: compact ? 76 : 82,
                  px: 1.5,
                  py: 1.25,
                  border: compact ? "1px solid" : 0,
                  borderBottom: compact ? undefined : "1px solid",
                  borderLeft: "3px solid",
                  borderColor:
                    message.id === selected ? "primary.main" : "divider",
                  alignItems: "flex-start",
                  "&.Mui-selected": { bgcolor: "action.selected" },
                  "&.Mui-selected:hover": { bgcolor: "action.selected" },
                }}
              >
                <ListItemText
                  disableTypography
                  sx={{
                    m: 0,
                    minWidth: 0,
                  }}
                  primary={
                    <Stack direction="row" gap={1} justifyContent="space-between">
                      <Typography
                        variant="subtitle2"
                        sx={{ overflow: "hidden", textOverflow: "ellipsis" }}
                      >
                        {message.title}
                      </Typography>
                      <Typography variant="overline" color="text.secondary">
                        #{message.id}
                      </Typography>
                    </Stack>
                  }
                  secondary={
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{
                        display: "-webkit-box",
                        mt: 0.5,
                        overflow: "hidden",
                        WebkitBoxOrient: "vertical",
                        WebkitLineClamp: 2,
                      }}
                    >
                      {t("settings.templates.lastUpdated", {
                        date: dayjs(message.updated_at).format("LL"),
                        user: message.updated_by,
                      })}
                    </Typography>
                  }
                />
              </ListItemButton>
            </ListItem>
          ))
        ) : (
          <ListItem>
            <ListItemText
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              primary={t("settings.templates.noMessages")}
            />
          </ListItem>
        )}
      </List>
    </Box>
  );
}

const MessagesDetailPage = () => {
  const { t } = useTranslation();
  const { category, messages } = useLoaderData();
  const action = useActionData();
  const [editor, setEditor] = useState(initialState);
  const [searchValue, setSearchValue] = useState("");
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  useEffect(() => {
    if (!action) return;
    switch (action.intent) {
      case INTENT.DELETE:
        setEditor(initialState);
        break;
      case INTENT.CREATE:
      case INTENT.UPDATE:
        let msg = messages.find(
          (msg) => Number(msg.id) === Number(action.message.id)
        );
        if (msg) {
          setEditor({
            mode: MODE.READ,
            ...msg,
          });
        } else {
          setEditor(initialState);
        }
        break;

      default:
        break;
    }
  }, [action, messages]);

  useEffect(() => {
    const firstMessage = messages[0];
    setEditor(firstMessage ? { mode: MODE.READ, ...firstMessage } : initialState);
  }, [category, messages]);

  const handleMessageClick = (index) => {
    const message = messages[index];
    if (!message) return;
    setEditor({
      mode: MODE.READ,
      ...message,
    });
  };

  const handleCreate = () => {
    setEditor({ mode: MODE.CREATE, id: 0, title: "", content: "" });
  };

  const handleCancelCreate = () => {
    const firstMessage = messages[0];
    setEditor(firstMessage ? { mode: MODE.READ, ...firstMessage } : initialState);
  };

  const handleCancelUpdate = () => {
    setEditor((prev) => {
      return {
        ...(messages.find((msg) => Number(msg.id) === Number(prev.id)) ??
          initialState),
        mode: MODE.READ,
      };
    });
  };

  const handleUpdate = () => {
    setEditor((prev) => ({ ...prev, mode: MODE.EDIT }));
  };

  const handleSearchChange = debounce((event) => {
    setSearchValue(event.target.value);
  }, 500);

  const filteredMessages = messages.filter(({ title, id, updated_by }) => {
    return `${id} ${title} ${updated_by}`
      .toLowerCase()
      .includes(searchValue.toLowerCase());
  });

  const actionHandlers = {
    create: handleCreate,
    update: handleUpdate,
    cancelCreate: handleCancelCreate,
    cancelEdit: handleCancelUpdate,
  };

  return (
    <Stack
      direction={compact ? "column" : "row"}
      alignItems="stretch"
      gap={1.5}
      sx={{ minWidth: 0 }}
    >
      <Paper
        component="aside"
        variant="outlined"
        sx={{
          minWidth: compact ? 0 : 360,
          width: compact ? "100%" : 360,
          borderRadius: 0,
          overflow: "hidden",
          flex: "0 0 auto",
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          gap={1}
          sx={{
            px: 1.5,
            py: 1.25,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Box sx={{ minWidth: 0 }}>
            <Typography component="h2" variant="h6">
              {t("settings.templates.library")}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t("settings.templates.templateCount", { count: messages.length })}
            </Typography>
          </Box>
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={handleCreate}
            disabled={editor.mode !== MODE.READ}
            sx={{ flex: "0 0 auto" }}
          >
            {t("settings.templates.createNew")}
          </Button>
        </Stack>

        <SearchWrapper
          sx={{
            px: 1.25,
            minHeight: 48,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <SearchIcon color="action" fontSize="small" />
          <InputBase
            sx={{ ml: 1, flex: 1, minWidth: 0 }}
            placeholder={t("settings.templates.search")}
            inputProps={{ "aria-label": t("settings.templates.search") }}
            onChange={handleSearchChange}
          />
        </SearchWrapper>

        <MessageList
          selected={editor.id}
          messages={filteredMessages}
          onMessageClick={handleMessageClick}
          compact={compact}
        />
      </Paper>

      <Box component={Form} method="POST" sx={{ flex: "1 1 auto", minWidth: 0 }}>
        <Paper variant="outlined" sx={{ borderRadius: 0, overflow: "hidden" }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "stretch", sm: "center" }}
            justifyContent="space-between"
            gap={1.5}
            sx={{
              px: { xs: 1.5, sm: 2 },
              py: 1.5,
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography variant="overline" color="primary.main">
                {t(`settings.templates.${category}`)}
              </Typography>
              <Typography
                component="h2"
                variant="h5"
                sx={{ overflowWrap: "anywhere" }}
              >
                {editor.mode === MODE.CREATE
                  ? t("settings.templates.createNew")
                  : editor.title || t("settings.templates.select")}
              </Typography>
              {editor.mode === MODE.READ && editor.id ? (
                <Typography variant="caption" color="text.secondary">
                  {t("settings.templates.lastUpdated", {
                    date: dayjs(editor.updated_at).format("LL"),
                    user: editor.updated_by,
                  })}
                </Typography>
              ) : null}
            </Box>

            {editor.mode === MODE.READ && editor.id ? (
              <Stack direction="row" gap={0.75} flexWrap="wrap">
                <Button
                  variant="outlined"
                  startIcon={<EditIcon />}
                  onClick={handleUpdate}
                >
                  {t("common.edit")}
                </Button>
                <Button
                  color="error"
                  type="submit"
                  name="intent"
                  value={INTENT.DELETE}
                  startIcon={<DeleteIcon />}
                >
                  {t("common.delete")}
                </Button>
              </Stack>
            ) : null}
          </Stack>

          <Box sx={{ p: { xs: 1.5, sm: 2 } }}>
            <EditorFields
              editor={editor}
              setEditor={setEditor}
              category={category}
              compact={compact}
            />
          </Box>

          <EditorActions
            editor={editor}
            compact={compact}
            actions={actionHandlers}
          />
        </Paper>
      </Box>
    </Stack>
  );
};

export default MessagesDetailPage;
