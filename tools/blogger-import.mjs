#!/usr/bin/env node
// Sinh file XML (Atom, định dạng xuất của Blogger) để nhập theo lô bằng
// Blogger → Settings → Manage blog → Import content.
//
// Dùng:  node tools/blogger-import.mjs --in posts.json [--out out] [--live]
//        [--blog-id ID] [--author "Tên"] [--author-uri URL]
//        [--max-posts 300] [--max-mb 8] [--prefix monika-import]
//
// Đầu vào: mảng JSON, mỗi phần tử:
//   { "title": "...",                 (bắt buộc)
//     "html": "<p>...</p>",           (nội dung, mặc định rỗng)
//     "meta": { "type":"game", "ver":"1.0", "jar":"https://..." },
//                                     (tùy chọn, tự chèn khối <pre class="mk-meta"> lên đầu bài)
//     "labels": ["Game","Hành động"], (tùy chọn)
//     "published": "2026-11-23T04:00:00Z", (tùy chọn, mặc định bây giờ)
//     "slug": "ten-bai",              (tùy chọn, mặc định sinh từ tiêu đề)
//     "description": "mô tả tìm kiếm ≤150 ký tự", (tùy chọn)
//     "draft": true }                 (tùy chọn, ghi đè mặc định)
// Mặc định mọi bài là NHÁP; thêm --live để đăng ngay.
// Không phụ thuộc thư viện ngoài, cần Node 18 trở lên.

import { createHash } from "node:crypto";
import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

const SLUG_MAX = 40;

export const esc = (s) =>
  String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/'/g, "&apos;").replace(/"/g, "&quot;");

// Bỏ ký tự điều khiển XML 1.0 không hợp lệ (giữ tab, xuống dòng).
const clean = (s) => String(s).replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F￾￿]/g, "");

export function slugify(title) {
  let s = clean(title)
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/Đ/g, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  if (s.length > SLUG_MAX) {
    s = s.slice(0, SLUG_MAX);
    const i = s.lastIndexOf("-");
    if (i > 12) s = s.slice(0, i);
    s = s.replace(/-+$/, "");
  }
  return s || "bai-viet";
}

// Id số ổn định theo (tiêu đề + ngày đăng): chạy lại cùng dữ liệu ra cùng id.
export function postId(title, published) {
  const h = createHash("sha1").update(title + "|" + published).digest("hex").slice(0, 15);
  return (BigInt("0x" + h) % 10n ** 17n + 10n ** 16n).toString();
}

export function metaBlock(meta) {
  const lines = Object.entries(meta)
    .filter(([, v]) => v !== undefined && v !== null && v !== "")
    .map(([k, v]) => `${k}: ${String(v).replace(/[\r\n]+/g, " ")}`);
  return `<pre class="mk-meta">\n${esc(lines.join("\n")).replace(/&apos;/g, "'").replace(/&quot;/g, '"')}\n</pre>\n`;
}

export function buildEntry(p, o) {
  if (!p.title) throw new Error("bài thiếu title");
  const pub = new Date(p.published || o.now);
  if (isNaN(pub)) throw new Error("published sai định dạng: " + p.published);
  const iso = pub.toISOString();
  const draft = p.draft ?? o.draft;
  const html = (p.meta ? metaBlock(p.meta) : "") + (p.html || "");
  const slug = p.slug ? slugify(p.slug) : slugify(p.title);
  const path = `/${iso.slice(0, 4)}/${iso.slice(5, 7)}/${slug}.html`;
  const cats = (p.labels || [])
    .map((l) => l.trim())
    .filter(Boolean)
    .map((l) => `    <category scheme='tag:blogger.com,1999:blog-${o.blogId}' term='${esc(l)}'/>\n`)
    .join("");
  const desc = p.description ? `<blogger:metaDescription>${esc(clean(p.description).slice(0, 150))}</blogger:metaDescription>` : "<blogger:metaDescription/>";
  return {
    path,
    xml:
      `  <entry>\n` +
      `    <id>tag:blogger.com,1999:blog-${o.blogId}.post-${postId(p.title, iso)}</id>\n` +
      `    <blogger:type>POST</blogger:type>\n` +
      `    <blogger:status>${draft ? "DRAFT" : "LIVE"}</blogger:status>\n` +
      `    <author>\n      <name>${esc(o.author)}</name>\n      <uri>${esc(o.authorUri)}</uri>\n      <blogger:type>BLOGGER</blogger:type>\n    </author>\n` +
      `    <title>${esc(clean(p.title))}</title>\n` +
      `    <content type='html'>${esc(clean(html))}</content>\n` +
      `    ${desc}\n` +
      `    <blogger:created>${o.now.toISOString()}</blogger:created>\n` +
      `    <published>${iso}</published>\n` +
      `    <updated>${o.now.toISOString()}</updated>\n` +
      `    <blogger:location/>\n` +
      cats +
      `    <blogger:filename>${path}</blogger:filename>\n` +
      `    <link/>\n    <enclosure/>\n    <blogger:trashed/>\n` +
      `  </entry>\n`,
  };
}

const head = (o, n) =>
  `<?xml version='1.0' encoding='UTF-8'?>\n` +
  `<feed xmlns='http://www.w3.org/2005/Atom' xmlns:blogger='http://schemas.google.com/blogger/2018'>\n` +
  `  <id>tag:blogger.com,1999:blog-${o.blogId}</id>\n` +
  `  <title>${esc(o.blogTitle)}${n ? ` (phần ${n})` : ""}</title>\n`;
const tail = `</feed>\n`;

// Trả về mảng chuỗi XML, mỗi chuỗi là một file nhập.
export function buildFeeds(posts, opts = {}) {
  const o = {
    blogId: opts.blogId || "0000000000000000000",
    blogTitle: opts.blogTitle || "Monika",
    author: opts.author || "Monika",
    authorUri: opts.authorUri || "https://m.justmonika.top",
    draft: opts.draft ?? true,
    now: opts.now || new Date(),
    maxPosts: opts.maxPosts || 300,
    maxBytes: (opts.maxMb || 8) * 1024 * 1024,
  };
  const seen = new Set();
  const files = [];
  let cur = [];
  let bytes = 0;
  for (const p of posts) {
    const e = buildEntry(p, o);
    if (seen.has(e.path)) throw new Error("trùng đường dẫn bài: " + e.path + " (đổi slug hoặc published)");
    seen.add(e.path);
    const sz = Buffer.byteLength(e.xml);
    if (cur.length && (cur.length >= o.maxPosts || bytes + sz > o.maxBytes)) {
      files.push(cur);
      cur = [];
      bytes = 0;
    }
    cur.push(e.xml);
    bytes += sz;
  }
  if (cur.length) files.push(cur);
  const multi = files.length > 1;
  return files.map((es, i) => head(o, multi ? i + 1 : 0) + es.join("") + tail);
}

function parseArgs(argv) {
  const a = {};
  for (let i = 0; i < argv.length; i++) {
    const k = argv[i];
    if (!k.startsWith("--")) throw new Error("tham số lạ: " + k);
    const key = k.slice(2);
    if (key === "live") a.live = true;
    else a[key] = argv[++i];
  }
  return a;
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (!a.in) {
    console.error("Thiếu --in posts.json (xem phần đầu file này để biết định dạng).");
    process.exit(2);
  }
  const posts = JSON.parse(readFileSync(a.in, "utf8"));
  if (!Array.isArray(posts) || !posts.length) throw new Error("--in phải là mảng JSON có ít nhất 1 bài");
  const feeds = buildFeeds(posts, {
    blogId: a["blog-id"],
    blogTitle: a["blog-title"],
    author: a.author,
    authorUri: a["author-uri"],
    draft: !a.live,
    maxPosts: a["max-posts"] ? +a["max-posts"] : undefined,
    maxMb: a["max-mb"] ? +a["max-mb"] : undefined,
  });
  const out = a.out || "out";
  mkdirSync(out, { recursive: true });
  const prefix = a.prefix || "monika-import";
  feeds.forEach((x, i) => {
    const f = join(out, `${prefix}-${String(i + 1).padStart(3, "0")}.xml`);
    writeFileSync(f, x);
    console.log(`${f}  ${(Buffer.byteLength(x) / 1024).toFixed(1)} KB`);
  });
  console.log(`${posts.length} bài, ${feeds.length} file, chế độ ${a.live ? "ĐĂNG NGAY" : "NHÁP"}`);
}

if (import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((e) => {
    console.error("Lỗi:", e.message);
    process.exit(1);
  });
}
