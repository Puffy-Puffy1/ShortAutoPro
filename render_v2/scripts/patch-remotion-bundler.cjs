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
  let changed = false;
  const getter = 'const getRspackConfig = () => require("./rspack-config");';

  let variable = null;
  if (!source.includes(getter)) {
    const match = source.match(/const\s+([A-Za-z_$][\w$]*)\s*=\s*require\(["']\.\/rspack-config["']\);/);
    if (!match) fail(`Expected Rspack config require anchor not found in ${path.relative(root, file)}.`);
    variable = match[1];
    source = source.replace(match[0], getter);
    changed = true;
  }

  // Replace references from the original generated import binding when this is
  // the first patch pass.
  if (variable) {
    const escaped = variable.replace(/[.*+?^$()|[\]\\]/g, "\\$&");
    const next = source
      .replace(new RegExp("\\b" + escaped + "\\.rspackConfig", "g"), "getRspackConfig().rspackConfig")
      .replace(new RegExp("\\b" + escaped + "\\.createRspackCompiler", "g"), "getRspackConfig().createRspackCompiler")
      .replace(new RegExp("\\b" + escaped + "\\.rspack\\(", "g"), "getRspackConfig().rspack(");
    changed = changed || next !== source;
    source = next;
  }

  // In index.js these are object-literal exports. Direct values such as
  // getRspackConfig().rspackConfig execute the getter during require().
  const next = source
    .replace(/rspackConfig:\s*getRspackConfig\(\)\.rspackConfig\s*,/g,
      "rspackConfig: (...args) => getRspackConfig().rspackConfig(...args),")
    .replace(/createRspackCompiler:\s*getRspackConfig\(\)\.createRspackCompiler\s*,/g,
      "createRspackCompiler: (...args) => getRspackConfig().createRspackCompiler(...args),");
  changed = changed || next !== source;
  source = next;

  fs.writeFileSync(file, source);
  return changed;
}

if (!fs.existsSync(indexFile) || !fs.existsSync(bundleFile)) {
  fail("Expected Remotion bundler dist files are missing.");
}

const indexChanged = patchRspackRequire(indexFile);
const bundleChanged = patchRspackRequire(bundleFile);
const changed = indexChanged || bundleChanged;

console.log(`[ShortAutoPro] Remotion bundler Android lazy-Rspack patch: ${changed ? "APPLIED" : "ALREADY_PATCHED"}`);
