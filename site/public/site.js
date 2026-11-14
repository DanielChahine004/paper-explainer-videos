// The catalogue and reels pages (tools/catalog.py, tools/reels.py) as the friends' website. tools/publish.py writes
// them out with this file and config.js; this sets window.SITE, which the pages use in place of catalog.py's server:
//   videos()  index.json: the list and the playlists
//   reels()   reels.json: every scene as a reel
//   notes(id) a video's notes: those already pulled into its feedback.json (notes.json, with what each led to),
//             plus comments on the video's GitHub issue not pulled yet
//   addNote / delNote  comment on that issue as the signed-in GitHub user, or delete your own comment
// A note is an issue comment carrying its moment in a marker, so publish.py can pull it into <video>/feedback.json
// for the next fix, and reply on the issue once it is resolved.
"use strict";
(() => {
	const C = window.SITE_CFG || {};
	const API = (C.api || "https://api.github.com").replace(/\/$/, "");
	const ls = {
		get(k, d) { try { const v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch { return d; } },
		set(k, v) { try { v == null ? localStorage.removeItem(k) : localStorage.setItem(k, JSON.stringify(v)); } catch { /* private window */ } },
	};

	// ---- sign-in: the paperstore GitHub App, through its sign-in worker, which sends the token back in the hash ----
	const back = new URLSearchParams(location.hash.slice(1));
	if (back.get("token")) {
		const exp = +back.get("expires_in") || 0;
		ls.set("site:auth", { token: back.get("token"), refresh: back.get("refresh") || "", exp: exp ? Date.now() + exp * 1000 : 0 });
		history.replaceState(null, "", location.pathname + location.search + (back.get("then") && back.get("then") !== "/" ? back.get("then") : ""));
	}
	function signIn() {
		location.href = C.auth + "/login?back=" + encodeURIComponent(location.href.split("#")[0]) + "&then=" + encodeURIComponent(location.hash || "/");
	}
	function signOut() { ls.set("site:auth", null); ls.set("site:me", null); render(); }
	async function token() {
		const a = ls.get("site:auth", null);
		if (!a) return null;
		if (a.exp && Date.now() > a.exp - 60000) {
			if (!a.refresh) { signOut(); return null; }
			const r = await fetch(C.auth + "/refresh", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ refresh_token: a.refresh }) }).catch(() => null);
			if (!r || !r.ok) { signOut(); return null; }
			const t = await r.json();
			ls.set("site:auth", { token: t.access_token, refresh: t.refresh_token || "", exp: t.expires_in ? Date.now() + t.expires_in * 1000 : 0 });
		}
		return ls.get("site:auth", null).token;
	}
	async function gh(path, opt = {}) {
		const t = await token();
		const h = { Accept: "application/vnd.github+json", ...(opt.body ? { "Content-Type": "application/json" } : {}) };
		if (t) h.Authorization = "Bearer " + t;
		const r = await fetch(API + path, { ...opt, headers: h, cache: "no-cache" });
		if (r.status === 401 && t) signOut();
		return r;
	}
	async function me() {
		const m = ls.get("site:me", null);
		if (m || !ls.get("site:auth", null)) return m;
		const r = await gh("/user");
		if (!r.ok) return null;
		const login = (await r.json()).login;
		ls.set("site:me", login);
		return login;
	}

	// ---- data -------------------------------------------------------------------------------------------------------
	const json = (f) => fetch(f, { cache: "no-cache" }).then((r) => (r.ok ? r.json() : Promise.reject(new Error(f + " " + r.status))));
	let idx = null;
	async function videos() {
		idx = await json("index.json");
		// the catalogue's own fields: mtime is the render it shows, born when the video first went up
		return [idx.videos.map((v) => ({ ...v, mtime: v.updated, born: v.added })), idx.playlists || []];
	}
	let pub = null, pubAt = 0;
	async function published() {
		if (!pub || Date.now() - pubAt > 20000) { pub = await json("notes.json").catch(() => pub || {}); pubAt = Date.now(); }
		return pub;
	}
	const MARK = /<!--\s*note\s+(\{.*?\})\s*-->/s;
	const fmt = (s) => { s = Math.max(0, Math.round(s)); return Math.floor(s / 60) + ":" + String(s % 60).padStart(2, "0"); };
	async function issue(id) { if (!idx) await videos(); return idx.videos.find((v) => v.id === id)?.issue; }

	async function notes(id) {
		const [p, n, login] = await Promise.all([published(), issue(id), me()]);
		const out = (p[id] || []).map((x) => ({ ...x }));
		const have = new Map(out.filter((x) => x.gh).map((x) => [x.gh, x]));
		if (n) {
			const r = await gh(`/repos/${C.repo}/issues/${n}/comments?per_page=100`).catch(() => null);
			const live = r && r.ok ? await r.json() : null;
			if (live) {
				const ids = new Set(live.map((c) => c.id));
				for (const c of live) {
					c.body = (c.body || "").replace(/\r\n/g, "\n");
					const m = MARK.exec(c.body);
					if (!m) continue;
					let meta; try { meta = JSON.parse(m[1]); } catch { continue; }
					const text = (c.body.split("\n\n").slice(1).join("\n\n").replace(MARK, "").trim()) || "";
					const x = have.get(c.id);
					if (x) { x.text = text || x.text; continue; }
					out.push({ nid: "gh" + c.id, gh: c.id, t: +meta.t || 0, text, by: c.user?.login, status: "open", at: c.created_at });
				}
				// a comment deleted on GitHub (and not yet resolved) is gone from the site too
				for (let i = out.length - 1; i >= 0; i--) if (out[i].gh && !ids.has(out[i].gh) && out[i].status === "open") out.splice(i, 1);
			}
		}
		for (const x of out) x.mine = !!(login && x.by === login && x.gh);
		return out;
	}
	async function addNote(id, t, text) {
		if (!ls.get("site:auth", null)) {
			if (confirm("Sign in with GitHub to leave a note? Your note is posted as a comment under your GitHub name.")) signIn();
			return false;
		}
		const n = await issue(id);
		const body = `**${fmt(t)}** · [watch](${C.base || location.href.split("#")[0]}#v=${encodeURIComponent(id)}&t=${Math.floor(t)})\n\n${text}\n\n<!-- note ${JSON.stringify({ t: Math.round(t * 10) / 10 })} -->`;
		const r = n ? await gh(`/repos/${C.repo}/issues/${n}/comments`, { method: "POST", body: JSON.stringify({ body }) }).catch(() => null) : null;
		if (!r || !r.ok) {
			alert(r && (r.status === 403 || r.status === 404) ? "GitHub didn't let this account comment here." : "Couldn't post the note. Try again in a moment.");
			return false;
		}
		return true;
	}
	async function delNote(id, n) {
		if (!n.gh) return false;
		const r = await gh(`/repos/${C.repo}/issues/comments/${n.gh}`, { method: "DELETE" }).catch(() => null);
		if (r && r.ok) pub = null;
		return !!(r && r.ok);
	}
	async function reels() { return json("reels.json"); }

	// ---- who is signed in, in the catalogue's header -------------------------------------------------------------------
	async function render() {
		const h = document.querySelector("header");
		if (!h) return;
		let b = document.getElementById("who");
		if (!b) {
			b = document.createElement("a"); b.id = "who"; b.href = "#";
			b.style.cssText = "color:var(--mute);text-decoration:none;font-size:14px";
			h.insertBefore(b, document.getElementById("q"));
		}
		const login = await me();
		b.textContent = login ? "@" + login : "Sign in to comment";
		b.title = login ? "Signed in with GitHub (tap to sign out)" : "Notes are GitHub comments: sign in to leave one";
		b.onclick = (e) => { e.preventDefault(); if (login) { if (confirm("Sign out?")) signOut(); } else signIn(); };
	}
	addEventListener("DOMContentLoaded", render);

	window.SITE = { videos, reels, notes, addNote, delNote, signIn, signOut, me };
})();
