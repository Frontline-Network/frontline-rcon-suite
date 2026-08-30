import { materialObjectControlTester } from "@jsonforms/material-renderers";
import { anyOfNullTester, renderer as anyOfNullRenderer } from "./anyOfNull";
import { renderer as objectRenderer } from "./object";
import {
  levelThresholdsTester,
  renderer as levelThresholdsRenderer,
} from "./levelThresholds";
import {
  stableIntegerControlTester,
  stableNumberControlTester,
  stableNumericControlRenderer,
} from "@/pages/settings/config-form/StableNumericControl";
import { playerFlagsRenderer, playerFlagsTester } from "./playerFlags";

export const schemaFormCustomRenderers = [
  {
    tester: playerFlagsTester,
    renderer: playerFlagsRenderer,
  },
  {
    tester: stableIntegerControlTester,
    renderer: stableNumericControlRenderer,
  },
  {
    tester: stableNumberControlTester,
    renderer: stableNumericControlRenderer,
  },
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
