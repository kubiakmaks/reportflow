from __future__ import annotations

import argparse
import threading
from pathlib import Path

from .mock_api import DEMO_TOKEN, start_demo_server
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate the ReportFlow demo report.")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Run the local deterministic demo")
    demo.add_argument("--output", type=Path, default=Path("output"), help="Output directory")
    args = parser.parse_args()

    server, url = start_demo_server()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        run_pipeline(url, DEMO_TOKEN, args.output)
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
