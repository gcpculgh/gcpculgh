import { Zip, ZipPassThrough } from "fflate";

const MAX_FILES = 30;
const MAX_FILE_SIZE = 50 * 1024 * 1024;
const ALLOWED_PREFIX = "media/";
const TOKEN_TTL = 60;

const ALLOWED_ORIGINS = [
    "https://www.gcpculgh.com",
    "https://gcpculgh.com",
];

const rateLimit = new Map();
const MAX_REQ_PER_WINDOW = 10;
const WINDOW_MS = 10000;

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": request.headers.get("Origin") || "*",
          "Access-Control-Allow-Methods": "POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type",
          "Access-Control-Max-Age": "86400",
        },
      });
    }

    if (request.method !== "POST") {
      return json({ error: "POST only" }, 405);
    }

    // RATE LIMIT
    const ip = request.headers.get("CF-Connecting-IP") || "unknown";
    const now = Date.now();
    const rlEntry = rateLimit.get(ip);
    if (rlEntry && now - rlEntry.start < WINDOW_MS) {
      if (rlEntry.count >= MAX_REQ_PER_WINDOW) {
        return json({ error: "Rate limited" }, 429);
      }
      rlEntry.count++;
    } else {
      rateLimit.set(ip, { start: now, count: 1 });
    }

    // ORIGIN
    const origin = request.headers.get("Origin");
    if (!ALLOWED_ORIGINS.includes(origin)) {
      return json({ error: "Forbidden" }, 403);
    }

    // PARSE BODY
    let body;
    try { body = await request.json(); } catch {
      return json({ error: "Invalid JSON" }, 400);
    }

    const { keys, filename, token, timestamp } = body;

    if (!Array.isArray(keys) || keys.length === 0) {
      return json({ error: "No files" }, 400);
    }
    if (keys.length > MAX_FILES) {
      return json({ error: `Max ${MAX_FILES}` }, 400);
    }

    // TOKEN EXPIRY
    if (!timestamp || (Date.now() / 1000 - timestamp) > TOKEN_TTL) {
      return json({ error: "Token expired" }, 401);
    }

    // VERIFY HMAC
    const payload = `${timestamp}:${[...keys].sort().join(",")}`;
    const expected = await hmacSign(payload, env.DOWNLOAD_SECRET);
    if (!token || !timingSafeEqual(token, expected)) {
      return json({ error: "Invalid token" }, 401);
    }

    // KEY SANITIZATION
    for (const key of keys) {
      if (typeof key !== "string" || !key.startsWith(ALLOWED_PREFIX)) {
        return json({ error: "Invalid path" }, 403);
      }
      if (key.includes("..") || key.includes("//")) {
        return json({ error: "Path traversal" }, 403);
      }
    }

    // BUILD ZIP
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const zip = new Zip((err, chunk, final) => {
      if (err) { writer.abort(err); return; }
      if (chunk) writer.write(chunk);
      if (final) writer.close();
    });

    (async () => {
      for (const key of keys) {
        const obj = await env.BUCKET.get(key);
        if (!obj || obj.size > MAX_FILE_SIZE) continue;
        const buf = await obj.arrayBuffer();
        const zipEntry = new ZipPassThrough(key.split("/").pop());
        zip.add(zipEntry);
        zipEntry.push(new Uint8Array(buf), true);
      }
      zip.end();
    })();

    return new Response(readable, {
      headers: {
        "Content-Type": "application/zip",
        "Content-Disposition": `attachment; filename="${filename || "selection"}.zip"`,
        "Access-Control-Allow-Origin": origin,
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
      },
    });
  },
};

async function hmacSign(payload, secret) {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode(payload));
  return btoa(String.fromCharCode(...new Uint8Array(sig)));
}

function timingSafeEqual(a, b) {
  if (a.length !== b.length) return false;
  let result = 0;
  for (let i = 0; i < a.length; i++) {
    result |= a.charCodeAt(i) ^ b.charCodeAt(i);
  }
  return result === 0;
}

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}   