#!/usr/bin/env node
const fs = require("fs");
const path = require("path");

const REQUIRED_FIELDS = ["id", "name", "type", "description", "function", "language", "module"];
const VALID_LANGUAGES = ["python", "javascript", "typescript", "shell"];

const registryPath = path.join(__dirname, "..", "registry", "capabilities.json");

let raw;
try {
  raw = fs.readFileSync(registryPath, "utf8");
} catch (e) {
  console.error(`FAILED: Cannot read ${registryPath}: ${e.message}`);
  process.exit(1);
}

let data;
try {
  data = JSON.parse(raw);
} catch (e) {
  console.error(`FAILED: Invalid JSON: ${e.message}`);
  process.exit(1);
}

if (!data || typeof data !== "object" || !Array.isArray(data.capabilities)) {
  console.error("FAILED: Top-level must be { capabilities: [...] }");
  process.exit(1);
}

const errors = [];
const seenIds = new Set();
const seenNames = new Set();
const caps = data.capabilities;

caps.forEach((cap, i) => {
  const pfx = `capabilities[${i}]`;

  if (!cap || typeof cap !== "object") {
    errors.push(`${pfx}: entry must be an object`);
    return;
  }

  REQUIRED_FIELDS.forEach((f) => {
    if (!cap[f] || typeof cap[f] !== "string" || !cap[f].trim()) {
      errors.push(`${pfx}: missing or empty required field '${f}'`);
    }
  });

  if (cap.id) {
    if (seenIds.has(cap.id)) errors.push(`${pfx}: duplicate id '${cap.id}'`);
    seenIds.add(cap.id);
  }

  if (cap.name) {
    if (seenNames.has(cap.name)) errors.push(`${pfx}: duplicate name '${cap.name}'`);
    seenNames.add(cap.name);
  }

  if (cap.language && !VALID_LANGUAGES.includes(cap.language)) {
    errors.push(`${pfx}: invalid language '${cap.language}'`);
  }

  const known = new Set(REQUIRED_FIELDS);
  Object.keys(cap).forEach((k) => {
    if (!known.has(k)) errors.push(`${pfx}: unknown field '${k}'`);
  });
});

const ids = caps.map((c) => c.id || "");
const sorted = [...ids].sort();
if (JSON.stringify(ids) !== JSON.stringify(sorted)) {
  errors.push("Capabilities are not sorted by 'id'");
}

const modulePaths = caps
  .filter((c) => c.module)
  .map((c) => ({
    id: c.id,
    module: c.module,
    filePath: path.join(__dirname, "..", ...c.module.split(".")) + ".py",
  }));

modulePaths.forEach(({ id, module, filePath }) => {
  if (!fs.existsSync(filePath)) {
    errors.push(`${id}: module '${module}' not found at ${filePath}`);
  }
});

if (errors.length) {
  console.error(`FAILED — ${errors.length} error(s):\n`);
  errors.forEach((e) => console.error(`  ✗ ${e}`));
  process.exit(1);
} else {
  console.log(`PASSED — ${caps.length} capabilities validated, 0 errors.`);
  console.log(`Module files verified: ${modulePaths.length}/${caps.length}`);
  process.exit(0);
}
