#!/usr/bin/env python3
"""
MYSTERY API  --  an undocumented practice server for HTTP recon drills.

Run it:      python3 mystery_api.py
Then:        curl -i http://127.0.0.1:8000/

There is NO documentation. That is the point. Everything you need is
discoverable from status codes, headers and error bodies.

Three levels, mirroring a gamified assessment:
  Level 1 -- discovery + authentication
  Level 2 -- pagination + rate limits + content types
  Level 3 -- graph traversal + aggregation

Stuck for more than 45 minutes?   python3 mystery_api.py --spoilers
Requires nothing but the Python standard library.
"""

import hashlib
import json
import re
import sys
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000

# ----------------------------------------------------------------------------
# In-memory state
# ----------------------------------------------------------------------------

SESSIONS = {}          # token -> {"handle": str, "levels": set()}
RATE_LOG = {}          # token -> deque of timestamps

RECORDS = []
for i in range(1, 61):
    RECORDS.append({
        "id": i,
        "tag": "alpha" if i % 3 == 0 else ("beta" if i % 3 == 1 else "gamma"),
        "value": (i * 7) % 23,
    })
ALPHA_SUM = sum(r["value"] for r in RECORDS if r["tag"] == "alpha")

# Level 3 graph. Real path is start -> k2 -> f9 -> q4 -> t1 -> end.
# Decoys have empty "next" or loop back.
GRAPH = {
    "start": {"seq": 1, "payload": "H", "next": ["k2", "z0"]},
    "z0":    {"seq": 0, "payload": "?", "next": []},
    "k2":    {"seq": 2, "payload": "T", "next": ["f9", "m5"]},
    "m5":    {"seq": 0, "payload": "?", "next": ["z0"]},
    "f9":    {"seq": 3, "payload": "T", "next": ["q4"]},
    "q4":    {"seq": 4, "payload": "P", "next": ["t1", "z0"]},
    "t1":    {"seq": 5, "payload": "9", "next": ["end"]},
    "end":   {"seq": 6, "payload": "!", "next": []},
}
PHRASE = "".join(GRAPH[n]["payload"] for n in ["start", "k2", "f9", "q4", "t1", "end"])

FLAGS = {
    1: "L1{you-read-the-headers}",
    2: "L2{pagination-is-not-optional}",
    3: "L3{errors-were-the-docs}",
}


# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------

def make_token(handle):
    return "tok_" + hashlib.md5(handle.encode()).hexdigest()[:12]


def rate_limited(token):
    """Allow 5 requests per 3 second window, per token."""
    now = time.time()
    log = RATE_LOG.setdefault(token, deque())
    while log and now - log[0] > 3.0:
        log.popleft()
    if len(log) >= 5:
        return True
    log.append(now)
    return False


class Handler(BaseHTTPRequestHandler):
    server_version = "mystery/1.4"
    sys_version = ""

    # -- plumbing ------------------------------------------------------------

    def log_message(self, fmt, *args):
        sys.stderr.write("  %s %s\n" % (self.command, self.path))

    def send_json(self, code, payload, headers=None, body=True):
        raw = json.dumps(payload, indent=2).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("X-Request-Id", hashlib.md5(
            (self.path + str(time.time())).encode()).hexdigest()[:8])
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if body:
            self.wfile.write(raw)

    def read_body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def want_json(self):
        """Returns (ok, parsed_or_error_response_sent)."""
        ctype = (self.headers.get("Content-Type") or "").split(";")[0].strip()
        if ctype != "application/json":
            self.send_json(415, {
                "error": "unsupported_media_type",
                "detail": "this endpoint speaks json and nothing else",
                "received": ctype or "(none)",
            }, {"Accept-Post": "application/json"})
            return False, None
        try:
            return True, json.loads(self.read_body() or b"{}")
        except json.JSONDecodeError as e:
            self.send_json(400, {"error": "malformed_json", "detail": str(e)})
            return False, None

    def auth(self):
        """Returns token string, or None (and sends 401)."""
        hdr = self.headers.get("Authorization") or ""
        m = re.match(r"^Bearer\s+(\S+)$", hdr)
        if not m or m.group(1) not in SESSIONS:
            self.send_json(401, {
                "error": "unauthenticated",
                "detail": "present a bearer token you have earned",
            }, {"WWW-Authenticate": 'Bearer realm="mystery"'})
            return None
        return m.group(1)

    # -- verbs ---------------------------------------------------------------

    def do_HEAD(self):
        self.dispatch("HEAD")

    def do_GET(self):
        self.dispatch("GET")

    def do_POST(self):
        self.dispatch("POST")

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Allow", "GET, HEAD, POST, OPTIONS")
        self.send_header("X-Hint", "not every path accepts every verb")
        self.end_headers()

    def do_PUT(self):
        self.send_json(405, {"error": "method_not_allowed"}, {"Allow": "GET, POST"})

    do_DELETE = do_PATCH = do_PUT

    # -- routing -------------------------------------------------------------

    def dispatch(self, verb):
        path = self.path.split("?")[0]
        query = {}
        if "?" in self.path:
            for pair in self.path.split("?", 1)[1].split("&"):
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    query[k] = v

        # ---------- root / discovery ----------
        if path == "/":
            return self.send_json(200, {
                "service": "mystery",
                "version": "1.4",
                "motd": "undocumented on purpose. probe, don't guess.",
            }, {"X-Hint": "GET /status", "Link": '</status>; rel="describedby"'},
                body=(verb != "HEAD"))

        if path == "/status":
            hdr = self.headers.get("Authorization")
            if not hdr:
                return self.send_json(401, {
                    "error": "unauthenticated",
                    "detail": "no credentials supplied",
                    "obtain_credentials_at": "/session",
                }, {"WWW-Authenticate": 'Bearer realm="mystery"'})
            tok = self.auth()
            if not tok:
                return
            s = SESSIONS[tok]
            return self.send_json(200, {
                "handle": s["handle"],
                "levels_cleared": sorted(s["levels"]),
                "next": "/level/1",
            })

        # ---------- level 1: auth ----------
        if path == "/session":
            if verb != "POST":
                return self.send_json(405, {
                    "error": "method_not_allowed",
                    "detail": "sessions are created, not fetched",
                }, {"Allow": "POST"})
            ok, body = self.want_json()
            if not ok:
                return
            missing = [f for f in ("handle", "accepts_terms") if f not in body]
            if missing:
                return self.send_json(422, {
                    "error": "validation_failed",
                    "missing_fields": missing,
                    "schema": {"handle": "string", "accepts_terms": "boolean(true)"},
                })
            if body.get("accepts_terms") is not True:
                return self.send_json(422, {
                    "error": "validation_failed",
                    "field": "accepts_terms",
                    "detail": "must be boolean true, not a string",
                })
            tok = make_token(str(body["handle"]))
            SESSIONS[tok] = {"handle": body["handle"], "levels": set()}
            return self.send_json(201, {
                "token": tok,
                "scheme": "Bearer",
                "next": "/level/1",
            }, {"Location": "/status"})

        m = re.match(r"^/level/(\d+)$", path)
        if m:
            lvl = int(m.group(1))
            tok = self.auth()
            if not tok:
                return
            s = SESSIONS[tok]
            if lvl == 1:
                s["levels"].add(1)
                return self.send_json(200, {
                    "level": 1,
                    "flag": FLAGS[1],
                    "brief": "sum the value of every record tagged alpha, "
                             "then POST {\"alpha_sum\": <int>} here to verify",
                    "records_at": "/records",
                    "verify_at": "/level/2/verify",
                })
            if lvl == 2:
                if 2 not in s["levels"]:
                    return self.send_json(403, {
                        "error": "locked",
                        "detail": "clear level 2 first",
                        "verify_at": "/level/2/verify",
                    })
                return self.send_json(200, {
                    "level": 3,
                    "brief": "walk the graph from /nodes/start, order nodes by seq, "
                             "concatenate payloads, POST {\"phrase\": \"...\"} to verify",
                    "verify_at": "/level/3/verify",
                })
            return self.send_json(404, {"error": "no_such_level"})

        # ---------- level 2: pagination + rate limit ----------
        if path == "/records":
            tok = self.auth()
            if not tok:
                return
            if rate_limited(tok):
                return self.send_json(429, {
                    "error": "rate_limited",
                    "detail": "5 requests per 3 seconds. back off.",
                }, {"Retry-After": "2"})
            try:
                cursor = int(query.get("cursor", 0))
            except ValueError:
                return self.send_json(400, {
                    "error": "bad_parameter", "parameter": "cursor",
                    "expected": "integer offset",
                })
            limit = 10  # deliberately ignores any client-supplied limit
            page = RECORDS[cursor:cursor + limit]
            headers = {"X-Total-Count": str(len(RECORDS))}
            nxt = cursor + limit
            if nxt < len(RECORDS):
                headers["Link"] = '</records?cursor=%d>; rel="next"' % nxt
            return self.send_json(200, {"items": page, "count": len(page)}, headers)

        if path == "/level/2/verify":
            if verb != "POST":
                return self.send_json(405, {"error": "method_not_allowed"},
                                      {"Allow": "POST"})
            tok = self.auth()
            if not tok:
                return
            ok, body = self.want_json()
            if not ok:
                return
            if body.get("alpha_sum") != ALPHA_SUM:
                return self.send_json(422, {
                    "error": "wrong_answer",
                    "hint": "did you read every page? check the Link header.",
                })
            SESSIONS[tok]["levels"].add(2)
            return self.send_json(200, {
                "flag": FLAGS[2], "next": "/level/2",
            })

        # ---------- level 3: graph traversal ----------
        m = re.match(r"^/nodes/([a-z0-9]+)$", path)
        if m:
            tok = self.auth()
            if not tok:
                return
            if 2 not in SESSIONS[tok]["levels"]:
                return self.send_json(403, {"error": "locked",
                                            "detail": "clear level 2 first"})
            node = GRAPH.get(m.group(1))
            if not node:
                return self.send_json(404, {"error": "no_such_node"})
            return self.send_json(200, {
                "id": m.group(1),
                "seq": node["seq"],
                "payload": node["payload"],
                "next": ["/nodes/%s" % n for n in node["next"]],
            })

        if path == "/level/3/verify":
            if verb != "POST":
                return self.send_json(405, {"error": "method_not_allowed"},
                                      {"Allow": "POST"})
            tok = self.auth()
            if not tok:
                return
            ok, body = self.want_json()
            if not ok:
                return
            if body.get("phrase") != PHRASE:
                return self.send_json(422, {
                    "error": "wrong_answer",
                    "hint": "nodes with seq 0 are decoys. order by seq, ascending.",
                })
            SESSIONS[tok]["levels"].add(3)
            return self.send_json(200, {
                "flag": FLAGS[3],
                "message": "cleared. you never needed documentation.",
            })

        # ---------- utility ----------
        if path == "/echo":
            return self.send_json(200, {
                "method": verb,
                "query": query,
                "headers": dict(self.headers),
                "body": (self.read_body() or b"").decode("utf-8", "replace"),
            })

        return self.send_json(404, {
            "error": "not_found",
            "path": path,
            "hint": "start at / and follow what you are given",
        })


SPOILERS = """
WALKTHROUGH  (read only after a genuine attempt)

Recon
  curl -i http://127.0.0.1:8000/            -> note the X-Hint and Link headers
  curl -i http://127.0.0.1:8000/status      -> 401 names /session
  curl -i -X GET http://127.0.0.1:8000/session   -> 405 + Allow: POST

Level 1
  POST /session with Content-Type: application/json
  Empty body -> 422 that prints the whole schema. That error IS the doc.
  Body: {"handle":"you","accepts_terms":true}  -> 201 with token
  All later calls: Authorization: Bearer <token>
  GET /level/1 -> flag + the level 2 brief

Level 2
  GET /records is paginated 10 at a time and ignores any limit you pass.
  The Link header carries rel="next". Follow it until it disappears (60 records).
  Rate limit is 5 requests / 3 seconds -> handle 429 and honour Retry-After.
  Sum value where tag == "alpha", POST {"alpha_sum": N} to /level/2/verify.

Level 3
  GET /nodes/start, then breadth-first through the "next" links.
  Nodes with seq == 0 are decoys; m5 loops back to z0.
  Sort real nodes by seq, concatenate payload, POST {"phrase": "..."} to
  /level/3/verify.

Every single thing above was recoverable from status codes, the Allow header,
the Link header, the WWW-Authenticate header, and validation error bodies.
"""

if __name__ == "__main__":
    if "--spoilers" in sys.argv:
        print(SPOILERS)
        sys.exit(0)
    print("mystery api listening on http://127.0.0.1:%d" % PORT)
    print("no documentation will be provided. start with:  curl -i http://127.0.0.1:%d/\n" % PORT)
    try:
        ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nbye")
