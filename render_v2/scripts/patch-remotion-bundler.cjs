#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const bundlerRoot = path.join(root, "node_modules", "@remotion", "bundler", "dist");
const indexFile = path.join(bundlerRoot, "index.js");
const bundleFile = path.join(bundlerRoot, "bundle.js");
const packageFile = path.join(root, "node_modules", "@remotion", "bundler", "package.json");

function fail(message) {
  console.error("[ShortAutoPro] " + message);
  process.exit(1);
}

if (!fs.existsSync(packageFile)) fail("Remotion bundler is not installed; run npm install again.");
const version = JSON.parse(fs.readFileSync(packageFile, "utf8")).version;
if (version !== "4.0.529") fail(`Unsupported @remotion/bundler version ${version}; expected 4.0.529.`);

function patchRspackRequire(file) {
  let source = fs.readFileSync(file, "utf8");
  if (source.includes('const getRspackConfig = () => require("./rspack-config");')) return false;

  const match = source.match(/const\s+([A-Za-z_$][\w$]*)\s*=\s*require\(["']\.\/rspack-config["']\);/);
  if (!match) fail(`Expected Rspack config require anchor not found in ${path.relative(root, file)}.`);

  const variable = match[1];
  source = source.replace(match[0], 'const getRspackConfig = () => require("./rspack-config");');

  const escaped = variable.replace(/[.*+?^$()|[\]\\]/g, "\\$&");
  const variablePattern = new RegExp("\\b" + escaped + "\\.rspackConfig", "g");
  source = source.replace(variablePattern, "getRspackConfig().rspackConfig");
  source = source.replace(new RegExp("\\b" + escaped + "\\.createRspackCompiler", "g"), "getRspackConfig().createRspackCompiler");
  source = source.replace(new RegExp("\\b" + escaped + "\\.rspack\\(", "g"), "getRspackConfig().rspack(");

  fs.writeFileSync(file, source);
  return true;
}

if (!fs.existsSync(indexFile) || !fs.existsSync(bundleFile)) {
  fail("Expected Remotion bundler dist files are missing.");
}

const indexChanged = patchRspackRequire(indexFile);
const bundleChanged = patchRspackRequire(bundleFile);
const changed = indexChanged || bundleChanged;

console.log(`[ShortAutoPro] Remotion bundler Android lazy-Rspack patch: ${changed ? "APPLIED" : "ALREADY_PATCHED"}`);
