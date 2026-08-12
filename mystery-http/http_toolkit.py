#!/usr/bin/env python3
"""
HTTP TOOLKIT -- the starter kit you should be able to retype from memory.

Works with `requests` if installed, falls back to the standard library.
Nothing here is clever. It is deliberately boring, because boring code is
what you can debug at minute 50 of a 60 minute level.

Usage:
    from http_toolkit import Client
    api = Client("http://127.0.0.1:8000")
    api.probe("/")                      # recon a single endpoint
    api.set_bearer("tok_abc")
    for item in api.paginate("/records"):
        ...

Everything is logged to requests.log.jsonl so you can prove your process
and replay your own steps.
"""

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

LOG_PATH = "requests.log.jsonl"


class Response:
    def __init__(self, status, headers, body_bytes, url, method):
        self.status = status
        self.headers = headers
        self.raw = body_bytes
        self.url = url
        self.method = method

    @property
    def text(self):
        return self.raw.decode("utf-8", "replace")

    @property
    def json(self):
        try:
            return json.loads(self.raw or b"{}")
        except json.JSONDecodeError:
            return None

    @property
    def ok(self):
        return 200 <= self.status < 300

    def __repr__(self):
        return "<%d %s %s>" % (self.status, self.method, self.url)


class Client:
    def __init__(self, base, timeout=15, log=LOG_PATH):
        self.base = base.rstrip("/")
        self.timeout = timeout
        self.headers = {"Accept": "application/json",
                        "User-Agent": "candidate-toolkit/1.0"}
        self.log = log
        self.history = []

    # -- config --------------------------------------------------------------

    def set_bearer(self, token):
        self.headers["Authorization"] = "Bearer " + token

    def set_header(self, k, v):
        self.headers[k] = v

    # -- core ----------------------------------------------------------------

    def request(self, method, path, body=None, params=None, extra_headers=None,
                retries=4):
        url = path if path.startswith("http") else self.base + path
        if params:
            url += ("&" if "?" in url else "?") + urllib.parse.urlencode(params)

        headers = dict(self.headers)
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        headers.update(extra_headers or {})

        attempt = 0
        while True:
            attempt += 1
            req = urllib.request.Request(url, data=data, method=method)
            for k, v in headers.items():
                req.add_header(k, v)
            started = time.time()
            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as r:
                    resp = Response(r.status, dict(r.headers), r.read(), url, method)
            except urllib.error.HTTPError as e:
                resp = Response(e.code, dict(e.headers), e.read(), url, method)
            except urllib.error.URLError as e:
                if attempt > retries:
                    raise
                time.sleep(min(2 ** attempt, 10))
                continue

            self._record(resp, round((time.time() - started) * 1000))

            # honour the server's own instructions before inventing your own
            if resp.status == 429 and attempt <= retries:
                wait = float(resp.headers.get("Retry-After", 2))
                print("  429 -- sleeping %.1fs" % wait)
                time.sleep(wait)
                continue
            if resp.status in (502, 503, 504) and attempt <= retries:
                time.sleep(min(2 ** attempt, 10))
                continue
            return resp

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, body=None, **kw):
        return self.request("POST", path, body=body, **kw)

    def _record(self, resp, ms):
        entry = {"ts": time.strftime("%H:%M:%S"), "method": resp.method,
                 "url": resp.url, "status": resp.status, "ms": ms,
                 "preview": resp.text[:200]}
        self.history.append(entry)
        try:
            with open(self.log, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError:
            pass

    # -- recon ---------------------------------------------------------------

    def probe(self, path):
        """Print everything an unfamiliar endpoint is willing to tell you."""
        print("=" * 60)
        print("PROBE", path)
        for method in ("GET", "POST", "OPTIONS", "HEAD"):
            try:
                r = self.request(method, path, retries=0)
            except Exception as e:
                print("  %-7s ERROR %s" % (method, e))
                continue
            interesting = {k: v for k, v in r.headers.items() if k.lower() in (
                "allow", "link", "location", "www-authenticate", "retry-after",
                "content-type", "x-total-count", "accept-post")
                or k.lower().startswith("x-")}
            print("  %-7s %s  %s" % (method, r.status, interesting or ""))
            if method == "GET" and r.raw:
                print("          body: %s" % r.text[:300].replace("\n", " "))
        print()

    def discover(self, paths=None):
        """Shotgun the usual suspects. Cheap, and occasionally decisive."""
        paths = paths or ["/", "/api", "/v1", "/health", "/status", "/version",
                          "/openapi.json", "/swagger.json", "/docs",
                          "/.well-known/openapi.json", "/routes", "/endpoints"]
        for p in paths:
            try:
                r = self.get(p, retries=0)
                if r.status != 404:
                    print("%-30s %s  %s" % (p, r.status, r.text[:120].replace("\n", " ")))
            except Exception:
                pass

    # -- pagination ----------------------------------------------------------

    def paginate(self, path, items_key="items", max_pages=200):
        """Handles Link rel=next, then falls back to common cursor keys."""
        url, pages = path, 0
        while url and pages < max_pages:
            pages += 1
            r = self.get(url)
            if not r.ok:
                print("stopped at page %d: %s %s" % (pages, r.status, r.text[:200]))
                return
            data = r.json or {}
            batch = data.get(items_key) if isinstance(data, dict) else data
            for item in (batch or []):
                yield item

            url = None
            link = r.headers.get("Link", "")
            m = re.search(r'<([^>]+)>;\s*rel="next"', link)
            if m:
                url = m.group(1)
            else:
                for key in ("next", "next_url", "next_cursor", "nextPage"):
                    if isinstance(data, dict) and data.get(key):
                        val = str(data[key])
                        url = val if val.startswith(("/", "http")) else \
                            "%s?cursor=%s" % (path.split("?")[0], val)
                        break
            if not batch:
                return


def crawl(client, start_path, next_key="next", id_key="id"):
    """Breadth-first walk of a linked-resource graph. Cycle safe."""
    seen, queue, out = set(), [start_path], []
    while queue:
        path = queue.pop(0)
        if path in seen:
            continue
        seen.add(path)
        r = client.get(path)
        if not r.ok:
            continue
        node = r.json
        out.append(node)
        for nxt in (node.get(next_key) or []):
            if nxt not in seen:
                queue.append(nxt)
    return out


if __name__ == "__main__":
    api = Client("http://127.0.0.1:8000")
    api.discover()
    api.probe("/session")
