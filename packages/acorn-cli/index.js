#!/usr/bin/env node

const { spawnSync } = require("child_process");
const path = require("path");

const BINARY = "acorn";

function findBinary() {
  const which = process.platform === "win32" ? "where" : "which";
  const result = spawnSync(which, [BINARY], { stdio: "ignore" });
  return result.status === 0;
}

function installMessage() {
  const lines = [
    "",
    "  Acorn CLI is not installed.",
    "",
    "  Install it with one of:",
    "",
    "    macOS:  brew install acorn/tap/acorn",
    "    Python: pip install acorn",
    "    All:    pipx install acorn",
    "",
    "  See https://github.com/SilasFu/Acorn for details.",
    "",
  ];
  return lines.join("\n");
}

function run(args) {
  const result = spawnSync(BINARY, args, { stdio: "inherit", shell: false });

  if (result.error) {
    if (result.error.code === "ENOENT") {
      console.error(installMessage());
      process.exit(1);
    }
    console.error(`Error running acorn: ${result.error.message}`);
    process.exit(1);
  }

  process.exit(result.status ?? 0);
}

const args = process.argv.slice(2);

if (!findBinary()) {
  console.error(installMessage());
  process.exit(1);
}

run(args);
