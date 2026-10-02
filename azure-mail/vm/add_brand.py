#!/usr/bin/env python3
"""CLI wrapper around lib_brand.provision."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_brand import ENV_PATH, load_env, provision  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description="Create mailbox + ACS send domain from the mail VM.")
    p.add_argument("domain", help="example.com")
    p.add_argument("local_part", nargs="?", default="hi")
    p.add_argument("--password", default="")
    p.add_argument(
        "--provider",
        default="manual",
        help="hostinger|godaddy|cloudflare|namecom|namecheap|porkbun|manual",
    )
    p.add_argument("--skip-mailcow", action="store_true")
    p.add_argument("--skip-acs", action="store_true")
    args = p.parse_args()
    env = load_env(ENV_PATH)
    if not env:
        sys.exit(f"Missing {ENV_PATH}. Copy azure-mail/vm/brand.env.example there.")

    def log(msg: str) -> None:
        print(msg, flush=True)

    result = provision(
        env,
        args.domain,
        args.local_part,
        args.password,
        args.provider,
        log,
        skip_mailcow=args.skip_mailcow,
        skip_acs=args.skip_acs,
    )
    print()
    print("OK")
    print(f"  Webmail  {result['webmail']}")
    print(f"  Login    {result['email']}")
    print(f"  Password {result['password']}")
    print("  IMAP 993 / SMTP 587")
    if result.get("records"):
        print("  DNS:")
        for r in result["records"]:
            extra = f"  pri {r['priority']}" if r.get("priority") else ""
            print(f"    {r['type']:6} {r['host']:40} {r['value']}{extra}")


if __name__ == "__main__":
    main()
