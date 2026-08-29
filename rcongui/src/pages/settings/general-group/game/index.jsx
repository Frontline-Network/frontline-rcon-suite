import React from "react";
import { useLoaderData } from "react-router-dom";
import GameControlMatrix from "./GameControlMatrix";

function GameTimersSettings() {
  const loaderData = useLoaderData();
  return <GameControlMatrix loaderData={loaderData} />;
}

export default GameTimersSettings;
