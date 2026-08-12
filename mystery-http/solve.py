#!/usr/bin/env python3
"""
Clear all three mystery API levels using http_toolkit.Client.

Demonstrates the recon workflow the toolkit was built for:
  probe → auth from error bodies → paginate Link headers → crawl graph.
"""

from http_toolkit import Client, crawl


def main():
    api = Client("http://127.0.0.1:8000", log="solve.requests.log.jsonl")

    print("--- recon ---")
    api.discover()
    api.probe("/")
    api.probe("/status")
    api.probe("/session")

    # Level 1: create session from the 422 schema, then claim flag
    print("--- level 1 ---")
    r = api.post("/session", body={})
    print("empty POST /session ->", r.status, r.json)
    r = api.post("/session", body={"handle": "candidate", "accepts_terms": True})
    assert r.status == 201, r.text
    token = r.json["token"]
    api.set_bearer(token)
    print("token:", token)

    r = api.get("/status")
    print("status:", r.json)

    r = api.get("/level/1")
    assert r.ok, r.text
    flag1 = r.json["flag"]
    print("FLAG 1:", flag1)

    # Level 2: paginate /records, sum alpha values, verify
    print("--- level 2 ---")
    alpha_sum = 0
    n = 0
    for item in api.paginate("/records"):
        n += 1
        if item.get("tag") == "alpha":
            alpha_sum += item["value"]
    print("records=%d alpha_sum=%d" % (n, alpha_sum))

    r = api.post("/level/2/verify", body={"alpha_sum": alpha_sum})
    assert r.ok, r.text
    flag2 = r.json["flag"]
    print("FLAG 2:", flag2)

    r = api.get("/level/2")
    print("level/2 brief:", r.json)

    # Level 3: BFS the graph, drop decoys (seq==0), order by seq
    print("--- level 3 ---")
    nodes = crawl(api, "/nodes/start")
    real = sorted(
        (n for n in nodes if n and n.get("seq")),
        key=lambda n: n["seq"],
    )
    phrase = "".join(n["payload"] for n in real)
    print("phrase:", phrase, "from", [n["id"] for n in real])

    r = api.post("/level/3/verify", body={"phrase": phrase})
    assert r.ok, r.text
    flag3 = r.json["flag"]
    print("FLAG 3:", flag3)
    print("message:", r.json.get("message"))

    r = api.get("/status")
    print("final status:", r.json)
    print("\nALL CLEARED")
    print("  ", flag1)
    print("  ", flag2)
    print("  ", flag3)


if __name__ == "__main__":
    main()
