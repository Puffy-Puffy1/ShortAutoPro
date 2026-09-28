#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");
const {execFileSync} = require("node:child_process");

const root = path.resolve(__dirname, "..");
const bundlerPackage = require(path.join(root, "node_modules", "@remotion", "bundler", "package.json"));
if (bundlerPackage.version !== "4.0.529") {
  throw new Error(`Unexpected @remotion/bundler version: ${bundlerPackage.version}`);
}

for (const relative of [
  "node_modules/@remotion/bundler/dist/index.js",
  "node_modules/@remotion/bundler/dist/bundle.js",
]) {
  const source = fs.readFileSync(path.join(root, relative), "utf8");
  if (!source.includes('const getRspackConfig = () => require("./rspack-config");')) {
    throw new Error(`Lazy Rspack getter missing in ${relative}`);
  }
  const eager = /const\s+[A-Za-z_$][\w$]*\s*=\s*require\(["']\.\/rspack-config["']\);/;
  if (eager.test(source)) {
    throw new Error(`Eager Rspack require remains in ${relative}`);
  }
}

const result = execFileSync(process.execPath, ["-e", [
  'require("@remotion/bundler");',
  'if (Object.keys(require.cache).some(k => /[\\\\/]@remotion[\\\\/]bundler[\\\\/]dist[\\\\/]rspack-config\\\\.js$/.test(k))) process.exit(2);',
  'if (Object.keys(require.cache).some(k => k.includes("@rspack/core"))) process.exit(3);',
  'console.log("REMOTION_BUNDLER_LAZY_RSPACK=PASS");',
].join(" ")], {cwd: root, encoding: "utf8"});

process.stdout.write(result);
