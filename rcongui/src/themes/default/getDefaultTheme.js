import {
  dataDisplayCustomizations,
  feedbackCustomizations,
  foundationCustomizations,
  navigationCustomizations,
  surfacesCustomizations,
  // inputsCustomizations,
} from "./customizations";
import { FRONTLINE_GEOMETRY } from "../foundation.mjs";

async function getColorPrimitives(schemeName) {
  switch (schemeName) {
    case "original":
      return import("./primitives/default");
    case "github":
      return import("./primitives/github");
    case "highContrast":
      return import("./primitives/highContrast");
    case "lime":
      return import("./primitives/lime");
    default:
      return import("./primitives/frontline");
  }
}

export default async function getDefaultTheme(themeComponents, selectedScheme = "default") {
  const {
    brand,
    gray,
    green,
    orange,
    red,
    typography,
    shadows,
    shape,
    geometry,
    colorSchemes,
  } = await getColorPrimitives(selectedScheme);

  const colors = { brand, gray, green, orange, red };

  return {
    // For more details about CSS variables configuration, see https://mui.com/material-ui/customization/css-theme-variables/configuration/
    cssVariables: {
      colorSchemeSelector: "data-mui-color-scheme",
      cssVarPrefix: "template",
    },
    defaultColorScheme: "dark",
    colorSchemes, // Recently added in v6 for building light & dark mode app, see https://mui.com/material-ui/customization/palette/#color-schemes
    typography,
    shadows,
    shape,
    frontline: { geometry: geometry ?? FRONTLINE_GEOMETRY },
    components: {
      ...dataDisplayCustomizations(colors),
      ...feedbackCustomizations(colors),
      ...navigationCustomizations(colors),
      ...surfacesCustomizations(colors),
      ...foundationCustomizations(colors),
      // This needs to be worked on
      // ...inputsCustomizations(colors),
      ...themeComponents,
    },
  };
}
