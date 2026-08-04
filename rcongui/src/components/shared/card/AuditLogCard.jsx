import {
  Card,
  CardContent,
  CardHeader,
  Stack,
  Typography,
  Box,
} from "@mui/material";
import dayjs from "dayjs";
import { CodeBlock } from "@/components/shared/CodeBlock";
import { useTranslation } from "react-i18next";

/**
 * @typedef {Object} AuditLog
 * @property {number} id
 * @property {string} username
 * @property {string} creation_time
 * @property {string} command
 * @property {string} command_arguments
 * @property {string} command_result
 */

/**
 * @typedef {Object} AuditLogCardProps
 * @property {AuditLog} auditLog
 */

/**
 * AuditLogCard component
 *
 * @param {AuditLogCardProps} props - The audit log object
 * @returns {JSX.Element} The AuditLogCard component
 */
export const AuditLogCard = ({ auditLog, ...props }) => {
  const { t } = useTranslation();

  const prettyLine = (label, value) => {
    return (
      <Typography>
        {label}: <Box component="span" sx={{ fontWeight: "bold", bgColor: "background.paper" }}>
          {value}
        </Box>
      </Typography>
    );
  };

  return (
    <Card {...props}>
      <CardHeader title={t("records.auditLogs.details")} sx={{ mb: 2 }} />
      <CardContent>
        {auditLog ? (
          <Stack spacing={1}>
            {prettyLine("ID", auditLog.id)}
            {prettyLine(t("records.auditLogs.actionColumn"), auditLog.command)}
            {prettyLine(t("records.auditLogs.userColumn"), auditLog.username)}
            {prettyLine(t("records.auditLogs.time"), dayjs(auditLog.creation_time).format("lll"))}
            {prettyLine(t("records.auditLogs.utcTime"), dayjs(auditLog.creation_time).utc().format("lll"))}
            <Typography variant="h6">{t("records.auditLogs.arguments")}</Typography>
            <CodeBlock text={auditLog.command_arguments} />
            <Typography variant="h6">{t("records.auditLogs.result")}</Typography>
            <CodeBlock text={auditLog.command_result} />
          </Stack>
        ) : (
          <Typography>{t("records.auditLogs.selectRow")}</Typography>
        )}
      </CardContent>
    </Card>
  );
};
