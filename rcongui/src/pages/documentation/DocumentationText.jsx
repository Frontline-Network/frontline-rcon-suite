import { Box } from "@mui/material";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Used only for our authored help; backend docstrings are rendered as plain text.
export default function DocumentationText({ children }) {
  return (
    <Box
      sx={{
        lineHeight: 1.8,
        overflowWrap: "anywhere",
        maxWidth: 980,
        "& h3": {
          fontSize: "1.1rem",
          lineHeight: 1.4,
          mt: 3.5,
          mb: 1,
          color: "text.primary",
        },
        "& h3:first-of-type": { mt: 0 },
        "& p, & ul, & ol": { mt: 0, mb: 2, color: "text.secondary" },
        "& li": { mb: 0.75 },
        "& ul, & ol": { pl: 2.5 },
        "& strong": { color: "text.primary", fontWeight: 600 },
        "& pre": {
          p: 2,
          overflowX: "auto",
          bgcolor: "action.hover",
          borderLeft: 2,
          borderColor: "primary.main",
          fontSize: "0.8rem",
          lineHeight: 1.65,
          whiteSpace: "pre-wrap",
          overflowWrap: "anywhere",
        },
        "& table": {
          width: "100%",
          borderCollapse: "collapse",
          mb: 3,
          textAlign: "left",
          fontSize: "0.875rem",
        },
        "& th, & td": {
          p: 1.5,
          verticalAlign: "top",
          borderBottom: 1,
          borderColor: "divider",
        },
        "& th": { bgcolor: "action.hover", fontWeight: 600 },
        "& th:first-of-type, & td:first-of-type": {
          width: "25%",
          minWidth: { xs: 76, sm: 110 },
          overflowWrap: "normal",
          wordBreak: "normal",
        },
        "& td": { color: "text.secondary" },
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
    </Box>
  );
}
