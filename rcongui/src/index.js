import App from "./App";
import "./index.css";
import i18n, { i18nReady } from "./i18n";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import * as serviceWorker from "./serviceWorker";
import { createRoot } from "react-dom/client";
import { makeServer } from "./mirage";

const app = document.getElementById('root');

const root = createRoot(app);

if (import.meta.env.MODE === "fake") {
  makeServer({ environment: "development" });
}

function Application({ languageLoadFailed = false }) {
  const [showLanguageError, setShowLanguageError] = useState(languageLoadFailed);
  const { t } = useTranslation();
  useEffect(() => {
    const clear = () => setShowLanguageError(false);
    i18n.on("languageChanged", clear);
    return () => i18n.off("languageChanged", clear);
  }, []);
  return <>{showLanguageError && <div role="alert">{t("language.loadFailed")}</div>}<App /></>;
}

i18nReady.then(() => root.render(<Application />)).catch((error) => {
  console.error("Could not load the saved language", error);
  root.render(<Application languageLoadFailed />);
});

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
