#!/usr/bin/env python3
"""Serve the bundled Category Builder UI on a loopback-only HTTP address."""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        parser.error("--host must be a loopback address")

    assets = Path(__file__).resolve().parent.parent / "assets"
    index = assets / "index.html"
    if not index.is_file():
        parser.error(f"bundled UI is missing: {index}")

    handler = partial(SimpleHTTPRequestHandler, directory=str(assets))
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"Category Builder UI: http://{args.host}:{server.server_port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
