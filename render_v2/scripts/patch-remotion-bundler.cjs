#!/usr/bin/env node
"use strict";

const fs = require("node:fs");
const path = require("node:path");

const root = __dirname.includes(path.sep)
  ? path.resolve(__dirname, "..")
  : process.cwd();

const bundlerRoot = path.join(root, "node_modules", "@remotion", "bundler", "dist");
const indexFile = path.join(bundlerRoot, "index.js");
const bundleFile = path.join(bundlerRoot, "bundle.js");
const packageFile = path.join(root, "node_modules", "@remotion", "bundler", "package.json");

function fail(message) {
  console.error("[ShortAutoPro] " + message);
  process.exit(1);
}

if (!fs.existsSync(packageFile)) {
  fail("Remotion bundler is not installed; run npm install first.");
}

const version = JSON.parse(fs.readFileSync(packageFile, "utf8")).version;
if (version !== "4.0.529") {
  fail(`Unsupported @remotion/bundler version ${version}; expected 4.0.529.`);
}

function patchFile(file, replacements) {
  let source = fs.readFileSync(file, "utf8");
  let changed = false;

  for (const [before, after] of replacements) {
    if (source.includes(after)) continue;
    if (!source.includes(before)) {
      fail(`Expected patch anchor not found in ${path.relative(root, file)}.`);
    }
    source = source.replace(before, after);
    changed = true;
  }

  if (changed) fs.writeFileSync(file, source);
  return changed;
}

if (!fs.existsSync(indexFile) || !fs.existsSync(bundleFile)) {
  fail("Expected Remotion bundler dist files are missing.");
}

const indexChanged = patchFile(indexFile, [
  [
    'const rspack_config_1 = require("./rspack-config");',
    'const getRspackConfig = () => require("./rspack-config");',
  ],
  [
    'rspackConfig: rspack_config_1.rspackConfig,',
    'rspackConfig: (...args) => getRspackConfig().rspackConfig(...args),',
  ],
  [
    'createRspackCompiler: rspack_config_1.createRspackCompiler,',
    'createRspackCompiler: (...args) => getRspackConfig().createRspackCompiler(...args),',
  ],
]);

const bundleChanged = patchFile(bundleFile, [
  [
    'const rspack_config_1 = require("./rspack-config");',
    'const getRspackConfig = () => require("./rspack-config");',
  ],
  [
    'return rspack_config_1.rspackConfig(configArgs);',
    'return getRspackConfig().rspackConfig(configArgs);',
  ],
]);

console.log(`[ShortAutoPro] Remotion bundler Android lazy-Rspack patch: ${indexChanged || bundleChanged ? "APPLIED" : "ALREADY_PATCHED"}`);
