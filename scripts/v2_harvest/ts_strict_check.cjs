#!/usr/bin/env node
"use strict";

const fs = require("fs");
const ts = require("typescript");

const tsPath = process.argv[2];
const mode = process.argv[3] || "transpile";
if (!tsPath) {
  console.error("Usage: node ts_strict_check.cjs <file.ts> [transpile|check]");
  process.exit(2);
}

const options = {
  target: ts.ScriptTarget.ES2022,
  module: ts.ModuleKind.ES2022,
  strict: true,
  noImplicitAny: true,
  strictNullChecks: true,
  noUnusedLocals: true,
  noUnusedParameters: true,
  lib: ["lib.es2022.d.ts", "lib.dom.d.ts"],
  skipLibCheck: false,
};

const program = ts.createProgram([tsPath], options);
const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length > 0) {
  for (const d of diagnostics) {
    const msg = ts.flattenDiagnosticMessageText(d.messageText, "\n");
    const pos = d.file && d.start !== undefined
      ? d.file.getLineAndCharacterOfPosition(d.start)
      : { line: 0, character: 0 };
    console.error(`${tsPath}:${pos.line + 1}:${pos.character + 1} - error TS${d.code}: ${msg}`);
  }
  process.exit(1);
}

if (mode === "transpile") {
  const source = fs.readFileSync(tsPath, "utf8");
  const out = ts.transpileModule(source, { compilerOptions: options });
  process.stdout.write(out.outputText);
} else {
  console.log(`OK: ${tsPath} (TS ${ts.version} strict:true, 0 diagnostics)`);
}
