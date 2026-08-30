import React from "react";
import { useLoaderData } from "react-router-dom";
import OperationsMatrix from "./OperationsMatrix";

function GeneralSettings() {
  const loaderData = useLoaderData();

  return (
    <OperationsMatrix
      settings={loaderData.settings}
      autokickSettings={loaderData.autokickSettings}
    />
  );
}

export default GeneralSettings;
