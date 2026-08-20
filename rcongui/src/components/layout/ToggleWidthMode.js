import WidthNormalIcon from '@mui/icons-material/WidthNormal';
import WidthFullIcon from '@mui/icons-material/WidthFull';
import MenuButton from './MenuButton';
import { useAppStore } from "@/stores/app-state";
import { useTranslation } from "react-i18next";

function ToggleWidthMode() {
  const { t } = useTranslation();
  const widthMode = useAppStore((state) => state.widthMode);
  const toggleWidthMode = useAppStore((state) => state.toggleWidthMode);

  return (
    <MenuButton
      onClick={toggleWidthMode}
      size="small"
      aria-label={t("common.toggleContentWidth")}
    >
      {widthMode === 'xl' ? (
        <WidthNormalIcon fontSize="small" />
      ) : (
        <WidthFullIcon fontSize="small" />
      )}
    </MenuButton>
  );
}

export default ToggleWidthMode;
