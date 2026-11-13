import { JSDOM } from "jsdom";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
export const html = readFileSync(join(root, "index.html"), "utf8");
export const js = readFileSync(join(root, "app.js"), "utf8");
export const css = readFileSync(join(root, "style.css"), "utf8");

const opened = [];
export function closeAll() { while (opened.length) { try { opened.pop().close(); } catch {} } }

export const tick = (ms = 20) => new Promise((r) => setTimeout(r, ms));
export async function until(fn, timeout = 2000) {
  const end = Date.now() + timeout;
  while (Date.now() < end) {
    if (fn()) return true;
    await tick(10);
  }
  return false;
}

/** routes: { "GET /path": body | (opts,url)=>body | {status, body} } ; en uzun önek eşleşir. */
export function loadApp({ routes = {}, hash = "", token = "", confirmResult = true } = {}) {
  const dom = new JSDOM(html, { url: "http://localhost:8000/app/" + hash, runScripts: "outside-only", pretendToBeVisual: true });
  const { window } = dom;
  opened.push(window);
  const calls = [];
  const errors = [];
  if (token) window.sessionStorage.setItem("akilli_token", token);
  window.confirm = () => confirmResult;
  window.prompt = () => "yeterince uzun gerekçe";
  window.alert = () => {};
  window.fetch = async (url, opts = {}) => {
    const method = (opts.method || "GET").toUpperCase();
    const body = opts.body ? JSON.parse(opts.body) : undefined;
    calls.push({ method, url, body });
    const keys = Object.keys(routes).filter((k) => `${method} ${url}`.startsWith(k)).sort((a, b) => b.length - a.length);
    let status = 200, payload = {};
    if (keys.length) {
      let r = routes[keys[0]];
      if (typeof r === "function") r = r(opts, url);
      if (r && typeof r === "object" && "status" in r && "body" in r) { status = r.status; payload = r.body; } else payload = r;
    } else { status = 404; payload = { detail: "Tanımsız test rotası: " + method + " " + url }; }
    return { ok: status < 400, status, json: async () => payload, blob: async () => new window.Blob(["x"]) };
  };
  window.addEventListener("error", (e) => errors.push(e.error || e.message));
  try { window.eval(js); } catch (e) { errors.push(e); }
  const $ = (id) => window.document.getElementById(id);
  return { window, document: window.document, $, calls, errors };
}
