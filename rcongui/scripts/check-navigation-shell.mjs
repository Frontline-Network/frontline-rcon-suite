import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const dashboard = read("src/pages/dashboard.jsx");
const bottomNavigation = read(
  "src/components/layout/MobileBottomNavigation.jsx"
);
const mobileNavigationRoutes = read(
  "src/components/layout/mobile-navigation.mjs"
);
const serverStatus = read("src/components/Header/server-status.jsx");
const serverSwitcher = read(
  "src/components/layout/navigation/ServerRailSwitcher.jsx"
);
const desktopNavigation = read(
  "src/components/layout/navigation/CommandNavigationShell.jsx"
);
const mobileNavigation = read(
  "src/components/layout/navigation/MobileCommandNavigation.jsx"
);
const breadcrumbs = read("src/components/layout/NavbarBreadcrumbs.js");

assert.match(dashboard, /compact \? <MobileOperationsHub \/> : <Dashboard \/>/);
assert.doesNotMatch(dashboard, /Navigate to="\/views\/live"/);

assert.match(bottomNavigation, /value: "server-operations",\s+to: "\/"/);
assert.match(
  mobileNavigationRoutes,
  /pathname === "\/" \|\| pathname\.startsWith\("\/mobile\/operations"\)/
);
assert.match(
  mobileNavigationRoutes,
  /pathname\.startsWith\("\/views\/live"\)\) return "operations"/
);

assert.match(serverStatus, /<ServerRailSwitcher/);
assert.match(serverStatus, /variant="status"/);
assert.match(serverSwitcher, /KeyboardArrowDownRoundedIcon/);
assert.match(serverSwitcher, /t\("sidebar\.switchServer"\)/);
assert.match(serverSwitcher, /placement=\{isStatusTrigger \? "bottom" : "right"\}/);
assert.match(desktopNavigation, /topSlot=\{<ServerRailSwitcher \/>\}/);
assert.doesNotMatch(mobileNavigation, /ServerRailSwitcher/);

assert.match(breadcrumbs, /data-testid="mobile-route-back"/);
assert.match(breadcrumbs, /to=\{parentPath\}/);
assert.match(breadcrumbs, /location\.pathname !== current\.path/);

console.log(
  "Navigation shell contract passed: mobile start, global server switching, compact destinations and detail back paths stay connected."
);
