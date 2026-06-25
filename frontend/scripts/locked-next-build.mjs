import { mkdir, rm } from "node:fs/promises";
import { spawn } from "node:child_process";
import path from "node:path";

const lockDir = path.resolve(".next-build.lock");
const staleAfterMs = 2 * 60 * 1000;

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function acquireLock() {
  const startedAt = Date.now();
  while (true) {
    try {
      await mkdir(lockDir);
      return;
    } catch (error) {
      if (error?.code !== "EEXIST") throw error;
      if (Date.now() - startedAt > staleAfterMs) {
        await rm(lockDir, { recursive: true, force: true });
        continue;
      }
      await sleep(500);
    }
  }
}

async function runBuild() {
  await acquireLock();
  try {
    const distDir = process.env.NEXT_DIST_DIR || ".next";
    if (process.env.CLEAN_NEXT_DIST === "1") {
      await rm(path.resolve(distDir), { recursive: true, force: true });
    }
    const nextBin = path.resolve("node_modules", "next", "dist", "bin", "next");
    const child = spawn(process.execPath, [nextBin, "build"], {
      stdio: "inherit",
      shell: false
    });
    const exitCode = await new Promise((resolve) => child.on("exit", resolve));
    process.exitCode = exitCode ?? 1;
  } finally {
    await rm(lockDir, { recursive: true, force: true });
  }
}

runBuild().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
