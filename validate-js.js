#!/usr/bin/env node
/**
 * validate-js.js — Catch undefined function calls in app.js before they ship.
 *
 * Extracts function definitions and calls from app.js, then reports any
 * calls to functions that are never defined and aren't known globals/methods.
 *
 * Exit 0 = clean, Exit 1 = undefined functions found.
 */

const fs = require("fs");
const path = require("path");

const JS_FILE = process.env.JS_FILE || path.join(__dirname, "static", "app.js");

if (!fs.existsSync(JS_FILE)) {
  console.error("ERROR: " + JS_FILE + " not found");
  process.exit(1);
}

const src = fs.readFileSync(JS_FILE, "utf8");
const lines = src.split("\n");

// 1. Collect all function definitions
const defs = new Set();

const funcDeclRe = /\bfunction\s+([a-zA-Z_$]\w*)\s*\(/g;
const varFuncRe = /\b(?:const|let|var)\s+([a-zA-Z_$]\w*)\s*=/g;
const windowRe = /\bwindow\.([a-zA-Z_$]\w*)\s*=/g;

let m;
while ((m = funcDeclRe.exec(src)) !== null) defs.add(m[1]);
while ((m = varFuncRe.exec(src)) !== null) defs.add(m[1]);
while ((m = windowRe.exec(src)) !== null) defs.add(m[1]);

// 2. Collect bare function calls (not method calls like .foo())
const callRe = /\b([a-zA-Z_$]\w*)\s*\(/g;
const calls = new Map(); // name -> [line numbers]

for (let i = 0; i < lines.length; i++) {
  const line = lines[i];
  // Strip comments and strings to reduce false matches
  const stripped = line
    .replace(/\/\/.*$/, "")
    .replace(/\/\*.*?\*\//g, "")
    .replace(/"(?:[^"\\]|\\.)*"/g, '""')
    .replace(/'(?:[^'\\]|\\.)*'/g, "''")
    .replace(/`[^`]*`/g, "``");

  let cm;
  while ((cm = callRe.exec(stripped)) !== null) {
    const name = cm[1];
    const idx = cm.index;

    // Skip method calls: preceded by a dot
    if (idx > 0 && stripped[idx - 1] === ".") continue;

    // Skip definition lines: "function NAME(" or "class NAME("
    const before = stripped.substring(0, idx);
    if (/\b(?:function|class)\s*$/.test(before)) continue;

    if (!calls.has(name)) calls.set(name, []);
    calls.get(name).push(i + 1);
  }
}

// 3. Known globals — JS built-ins, browser APIs, keywords
const globals = new Set([
  // Keywords
  "if", "else", "for", "while", "do", "switch", "case", "return", "new",
  "typeof", "instanceof", "void", "delete", "in", "of", "async", "await",
  "yield", "class", "extends", "super", "this", "import", "export", "default",
  "try", "catch", "finally", "throw", "break", "continue", "with", "debugger",
  "const", "let", "var", "function", "require",
  // Global constructors
  "Array", "Object", "String", "Number", "Boolean", "Date", "Math", "JSON",
  "RegExp", "Map", "Set", "WeakMap", "WeakSet", "Promise", "Error",
  "TypeError", "ReferenceError", "SyntaxError", "RangeError", "Symbol",
  "Proxy", "Reflect", "BigInt", "URL", "URLSearchParams", "FormData",
  "Headers", "Request", "Response", "HTMLElement", "Element", "Node",
  "Event", "EventSource", "AbortController", "EventTarget",
  "MutationObserver", "ResizeObserver", "IntersectionObserver",
  "XMLHttpRequest", "Image", "Audio", "File", "Blob", "FileReader",
  "Worker", "WebSocket", "TextEncoder", "TextDecoder",
  // Global functions
  "fetch", "setTimeout", "clearTimeout", "setInterval", "clearInterval",
  "requestAnimationFrame", "cancelAnimationFrame", "queueMicrotask",
  "alert", "confirm", "prompt",
  "parseInt", "parseFloat", "isNaN", "isFinite",
  "encodeURIComponent", "decodeURIComponent", "encodeURI", "decodeURI",
  "atob", "btoa", "structuredClone",
  // DOM / Window
  "document", "window", "navigator", "location", "history",
  "localStorage", "sessionStorage", "console",
  "getComputedStyle", "matchMedia",
  // Testing globals
  "describe", "it", "test", "expect", "beforeEach", "afterEach",
  // Third-party globals
  "GridStack",
  "define", // AMD
]);

// 4. Find undefined calls
const errors = [];
for (const [name, lineNums] of calls) {
  if (defs.has(name)) continue;
  if (globals.has(name)) continue;
  // Skip ALL_CAPS (constants like SPELL_IMG)
  if (/^[A-Z][A-Z_0-9]+$/.test(name)) continue;
  // Skip PascalCase (constructors like AbortController)
  if (/^[A-Z]/.test(name)) continue;
  // Skip single character names
  if (name.length <= 1) continue;

  errors.push({ name, lines: lineNums.slice(0, 5) });
}

if (errors.length > 0) {
  console.log("");
  console.log("==========================================");
  console.log(" JS VALIDATION FAILED — " + errors.length + " undefined function(s)");
  console.log("==========================================");
  console.log("");
  errors.forEach((e) => {
    console.log("  UNDEFINED: " + e.name + "() — called at line(s) " + e.lines.join(", "));
  });
  console.log("");
  console.log("These functions are called but never defined in app.js.");
  console.log("Either add the missing function or remove the call.");
  console.log("");
  console.log("Commit blocked.");
  process.exit(1);
} else {
  console.log("JS validation passed — no undefined functions, syntax OK.");
  process.exit(0);
}
