import { materialObjectControlTester } from "@jsonforms/material-renderers";
import { anyOfNullTester, renderer as anyOfNullRenderer } from "./anyOfNull";
import { renderer as objectRenderer } from "./object";
import {
  levelThresholdsTester,
  renderer as levelThresholdsRenderer,
} from "./levelThresholds";

export const schemaFormCustomRenderers = [
  { tester: levelThresholdsTester, renderer: levelThresholdsRenderer },
  { tester: anyOfNullTester, renderer: anyOfNullRenderer },
];

export const customRenderers = [
  ...schemaFormCustomRenderers,
  {
    tester: materialObjectControlTester,
    renderer: objectRenderer,
  },
];
