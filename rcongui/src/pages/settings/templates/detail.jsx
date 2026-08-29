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

  return (
    <Paper
      elevation={0}
      sx={(theme) => ({
        display: "flex",
        flexWrap: "wrap",
        gap: theme.spacing(0.75),
        padding: theme.spacing(1),
        borderRadius: 0,
        ...(compact && {
          position: "sticky",
          bottom: "calc(64px + env(safe-area-inset-bottom))",
          zIndex: theme.zIndex.appBar,
          mt: 1,
          border: "1px solid",
          borderColor: theme.palette.divider,
          boxShadow: theme.shadows[8],
        }),
        "& .MuiButton-root": {
          minHeight: 44,
          ...(compact && { flex: "1 1 132px" }),
        },
      })}
    >
      <Box sx={{ flexGrow: 1 }} />
      {editor.mode === MODE.READ && editor.id !== 0 && (
        <Button onClick={actions.update} startIcon={<EditIcon />}>
          {t("common.edit")}
        </Button>
      )}
      {editor.mode === MODE.CREATE && (
        <>
          <Button onClick={actions.cancelCreate} startIcon={<CancelIcon />}>
            {t("common.cancel")}
          </Button>
          <Button
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
          <Button onClick={actions.cancelEdit} startIcon={<CancelIcon />}>
            {t("common.cancel")}
          </Button>
          <Button
            type="submit"
            name="intent"
            value={INTENT.UPDATE}
            startIcon={<SaveIcon />}
            disabled={!canBeSaved}
          >
            {t("common.save")}
          </Button>
          <Button
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
      {editor.mode !== MODE.CREATE && editor.id !== 0 && (
        <>
          <Button
            color="warning"
            type="submit"
            name="intent"
            value={INTENT.DELETE}
            startIcon={<DeleteIcon />}
          >
            {t("common.delete")}
          </Button>
        </>
      )}
      {editor.mode === MODE.READ && (
        <>
          <Button onClick={actions.create} startIcon={<AddIcon />}>
            {t("settings.templates.createNew")}
          </Button>
        </>
      )}
    </Paper>
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
      <StyledTextField
        name="title"
        value={editor.title}
        onChange={handleOnInputChange}
        placeholder={t("settings.templates.messageTitle")}
        fullWidth
        required
        disabled={editor.mode === MODE.READ}
      />
      {category === "broadcast" ? (
        <BroadcastFields
          messages={unpackBroadcastMessage(editor.content ?? "")}
          disabled={editor.mode === MODE.READ}
          onChange={handleOnBroadcastChange}
        />
      ) : category === "auto_settings" ? (
        <Suspense fallback={<Skeleton variant="rectangular" height="70vh" />}>
          <StyledTextField
            multiline
            minRows={compact ? 9 : 16}
            fullWidth
            name="content"
            value={editor.content}
            required
            readOnly={editor.mode === MODE.READ}
            sx={{ display: editor.mode === MODE.READ ? "block" : "none" }}
          />
          <Box sx={{ display: editor.mode === MODE.READ ? "none" : "block" }}>
            <Editor
              height={compact ? "52vh" : "70vh"}
              defaultLanguage="json"
              value={editor.content}
              defaultValue=""
              theme={theme.palette.mode === "dark" ? "vs-dark" : "vs-light"}
              onChange={handleAutosettingsChange}
            />
          </Box>
        </Suspense>
      ) : (
        <StyledTextField
          name="content"
          value={editor.content}
          onChange={handleOnInputChange}
          placeholder={t("settings.templates.messageContent")}
          multiline
          minRows={compact ? 9 : 16}
          fullWidth
          required
          disabled={editor.mode === MODE.READ}
        />
      )}
    </>
  );
}

function MessageList({ messages, onMessageClick, selected, compact = false }) {
  const { t } = useTranslation();
  return (
    <Paper
      sx={{
        borderRadius: 0,
        minHeight: compact ? 0 : "300px",
        maxHeight: compact ? "none" : "calc(100vh - 256px)",
        overflowY: compact ? "visible" : "auto",
        overflowX: compact ? "auto" : "hidden",
        scrollbarWidth: "thin",
        scrollbarGutter: "auto",
      }}
    >
      <List
        sx={compact ? {
          display: "flex",
          gap: 1,
          p: 1,
          width: "max-content",
        } : undefined}
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
                sx={compact ? {
                  minHeight: 68,
                  border: "1px solid",
                  borderColor: message.id === selected ? "primary.main" : "divider",
                  alignItems: "flex-start",
                } : undefined}
              >
                <ListItemText
                  sx={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                  primary={`#${message.id} - ${message.title}`}
                  secondary={t("settings.templates.lastUpdated", {
                    date: dayjs(message.updated_at).format("LL"),
                    user: message.updated_by,
                  })}
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
    </Paper>
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
      id: message.id,
      title: message.title,
      content: message.content,
    });
  };

  const handleCreate = () => {
    setEditor({ mode: MODE.CREATE, id: 0, title: "", content: "" });
  };

  const handleCancelCreate = () => {
    setEditor(initialState);
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

  return (
    <Stack direction={compact ? "column" : "row"} gap={compact ? 1.5 : 0} sx={{ minWidth: 0 }}>
      <Stack direction="column" sx={{ minWidth: compact ? 0 : 300, width: compact ? "100%" : 300 }}>
        <Paper
          sx={(theme) => ({
            padding: theme.spacing(0.5),
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            borderRadius: 0,
            border: "1px solid",
            borderColor: theme.palette.divider,
          })}
        >
          <SearchWrapper>
            <Box sx={{ p: "10px", display: "grid", alignItems: "center" }}>
              <SearchIcon />
            </Box>
            <InputBase
              sx={{ ml: 1, flex: 1, minWidth: 0 }}
              placeholder={t("settings.templates.search")}
              inputProps={{ "aria-label": t("settings.templates.search") }}
              onChange={handleSearchChange}
            />
          </SearchWrapper>
        </Paper>
        <MessageList
          selected={editor.id}
          messages={filteredMessages}
          onMessageClick={handleMessageClick}
          compact={compact}
        />
      </Stack>
      <Box component={Form} method="POST" sx={{ flexGrow: 1, width: "100%", minWidth: 0 }}>
        {!compact && <EditorActions
          editor={editor}
          actions={{ create: handleCreate, update: handleUpdate, cancelCreate: handleCancelCreate, cancelEdit: handleCancelUpdate }}
        />}
        <Paper variant="outlined" sx={{ p: { xs: 1.5, sm: 2 }, borderRadius: 0 }}>
          <Typography variant="overline" color="primary.main" sx={{ fontWeight: 800 }}>
            {editor.mode === MODE.CREATE
              ? t("settings.templates.createNew")
              : editor.title || t("settings.templates.select")}
          </Typography>
        <EditorFields
          editor={editor}
          setEditor={setEditor}
          category={category}
          compact={compact}
        />
        </Paper>
        {compact && <EditorActions
          editor={editor}
          compact
          actions={{ create: handleCreate, update: handleUpdate, cancelCreate: handleCancelCreate, cancelEdit: handleCancelUpdate }}
        />}
      </Box>
    </Stack>
  );
};

export default MessagesDetailPage;
