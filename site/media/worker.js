// The explainers site's media: /<video id>/<file> is the release file of DanielChahine004/explainers, passed through
// with its byte ranges (players seek with them) but labelled as what it is. GitHub serves release files as
// application/octet-stream and as an attachment, which Safari (every browser on an iPhone) refuses to play as video.
// Files are named by their contents, so they never change and can be cached for good.

const REPO = "DanielChahine004/explainers";
const TYPES = { mp4: "video/mp4", jpg: "image/jpeg", png: "image/png", vtt: "text/vtt; charset=utf-8" };

export default {
	async fetch(req) {
		if (req.method === "OPTIONS") return new Response(null, { headers: { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "Range" } });
		if (req.method !== "GET" && req.method !== "HEAD") return new Response("method not allowed", { status: 405 });
		const m = new URL(req.url).pathname.match(/^\/([\w.-]+)\/([\w.-]+\.(mp4|jpg|png|vtt))$/);
		if (!m) return new Response("not found", { status: 404 });
		const range = req.headers.get("range");
		const up = await fetch(`https://github.com/${REPO}/releases/download/${m[1]}/${m[2]}`, {
			method: req.method, headers: range ? { Range: range } : {}, redirect: "follow",
		});
		if (!up.ok) return new Response("not found", { status: up.status === 416 ? 416 : 404 });
		const h = new Headers();
		for (const k of ["content-length", "content-range", "etag", "last-modified"]) if (up.headers.has(k)) h.set(k, up.headers.get(k));
		h.set("content-type", TYPES[m[3]]);
		h.set("accept-ranges", "bytes");
		h.set("cache-control", "public, max-age=31536000, immutable");
		h.set("access-control-allow-origin", "*");
		h.set("access-control-expose-headers", "content-length, content-range, accept-ranges");
		return new Response(up.body, { status: up.status, headers: h });
	},
};
