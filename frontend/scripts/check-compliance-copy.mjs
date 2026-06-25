import { readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const bannedPhrases = [
  "推薦買進",
  "保證獲利",
  "穩賺",
  "包賺",
  "必漲",
  "飆股",
  "命中率",
  "勝率",
  "獲利率"
];

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..");
const scanRoots = [
  "frontend/app",
  "frontend/lib",
  "backend/app",
  "docs",
  "README.md"
];

const allowedExtensions = new Set([".ts", ".tsx", ".py", ".md"]);

const violations = [];

for (const file of collectFiles(scanRoots)) {
  const path = join(repoRoot, file);
  const text = readFileSync(path, "utf8");
  for (const phrase of bannedPhrases) {
    if (text.includes(phrase)) {
      violations.push(`${file}: ${phrase}`);
    }
  }
}

if (violations.length > 0) {
  console.error("High-risk investment wording found:");
  for (const violation of violations) {
    console.error(`- ${violation}`);
  }
  process.exit(1);
}

console.log("Compliance copy check passed.");

function collectFiles(items) {
  const files = [];
  for (const item of items) {
    const path = join(repoRoot, item);
    const stats = statSync(path);
    if (stats.isDirectory()) {
      for (const child of readdirSync(path)) {
        files.push(...collectFiles([join(item, child)]));
      }
      continue;
    }
    const extension = path.slice(path.lastIndexOf("."));
    if (allowedExtensions.has(extension)) {
      files.push(item);
    }
  }
  return files;
}
