import { cp, mkdir } from "node:fs/promises";
import { resolve } from "node:path";

const projectRoot = resolve(import.meta.dirname, "..");
const publicDirectory = resolve(projectRoot, "public");

await mkdir(publicDirectory, { recursive: true });
await Promise.all([
  cp(resolve(projectRoot, "../assets/rcongui"), publicDirectory, {
    recursive: true,
    force: true,
  }),
  cp(resolve(projectRoot, "../assets/images"), publicDirectory, {
    recursive: true,
    force: true,
  }),
]);

console.log(
  "Prepared Frontline assets for local development and visual tests."
);
