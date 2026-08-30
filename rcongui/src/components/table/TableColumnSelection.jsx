import {
  Box,
  Checkbox,
  IconButton,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Tooltip,
} from "@mui/material";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import { useTranslation } from "react-i18next";

import { PopoverMenu } from "@/components/shared/PopoverMenu";

const TableColumnSelection = ({
  table,
  onColumnVisibilityChange,
  renderButton,
  getColumnLabel,
}) => {
  const { t } = useTranslation();
  const columns = table.getAllColumns().filter((column) => column.getCanHide());

  return (
    <PopoverMenu
      id="column-picker"
      description={t("selection.columnsDescription")}
      renderButton={(props) =>
        renderButton ? (
          renderButton(props)
        ) : (
          <IconButton
            {...props}
            aria-label={t("selection.columns")}
            size="small"
            sx={{ borderRadius: 0 }}
          >
            <Tooltip title={t("selection.columns")}>
              <ViewColumnIcon sx={{ fontSize: 16 }} />
            </Tooltip>
          </IconButton>
        )
      }
      sx={{ width: "200px" }}
    >
      <List
        sx={{
          width: "100%",
          bgcolor: "background.paper",
          position: "relative",
          overflowY: "auto",
          overflowX: "hidden",
          maxHeight: 300,
          "& ul": { padding: 0 },
        }}
      >
        {columns.map((column) => {
          const label =
            getColumnLabel?.(column) ??
            column.columnDef.meta?.label ??
            (typeof column.columnDef.header === "string"
              ? column.columnDef.header
              : column.id);

          return (
            <ListItem
              key={column.id}
              dense
              disableGutters
              sx={{ "& .MuiButtonBase-root": { opacity: 1 } }}
            >
              <ListItemButton
                onClick={() =>
                  onColumnVisibilityChange(column.id, !column.getIsVisible())
                }
              >
                <Box
                  sx={{
                    display: "flex",
                    alignItems: "center",
                    overflow: "hidden",
                    px: 0,
                    py: 0.25,
                    gap: 1,
                  }}
                >
                  <ListItemIcon>
                    <Checkbox
                      edge="start"
                      checked={column.getIsVisible()}
                      disabled={!column.getCanHide()}
                      tabIndex={-1}
                      disableRipple
                      inputProps={{
                        "aria-labelledby": `picker-${column.id}`,
                      }}
                    />
                  </ListItemIcon>
                  <ListItemText id={`picker-${column.id}`} primary={label} />
                </Box>
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
    </PopoverMenu>
  );
};

export default TableColumnSelection;
