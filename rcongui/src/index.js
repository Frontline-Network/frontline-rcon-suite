import App from "./App";
import "./index.css";
import { i18nReady } from "./i18n";
import * as serviceWorker from "./serviceWorker";
import { createRoot } from "react-dom/client";
import { makeServer } from "./mirage";

const app = document.getElementById('root');

const root = createRoot(app);

if (import.meta.env.MODE === "fake") {
  makeServer({ environment: "development" });
}

i18nReady.then(() => root.render(<App />)).catch((error) => {
  console.error("Could not load the saved language", error);
  root.render(<App />);
});

// If you want your app to work offline and load faster, you can change
// unregister() to register() below. Note this comes with some pitfalls.
// Learn more about service workers: https://bit.ly/CRA-PWA
serviceWorker.unregister();
