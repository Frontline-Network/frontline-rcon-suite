import { styled } from "@mui/material/styles";
import Button from "@mui/material/Button";
import CloudUploadIcon from "@mui/icons-material/CloudUpload";

const VisuallyHiddenInput = styled("input")({
  clip: "rect(0 0 0 0)",
  clipPath: "inset(50%)",
  height: 1,
  overflow: "hidden",
  position: "absolute",
  bottom: 0,
  left: 0,
  whiteSpace: "nowrap",
  width: 1,
});

export function InputFileUpload({
  text,
  icon,
  color,
  variant,
  accept,
  onChange,
  inputProps,
  ...buttonProps
}) {
  return (
    <Button
      component="label"
      variant={variant ?? "contained"}
      color={color ?? "primary"}
      startIcon={icon ?? <CloudUploadIcon />}
      {...buttonProps}
    >
      {text ?? "Upload file"}
      <VisuallyHiddenInput
        type="file"
        accept={accept}
        onChange={onChange}
        {...inputProps}
      />
    </Button>
  );
}
