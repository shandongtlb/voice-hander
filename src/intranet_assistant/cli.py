from __future__ import annotations

import argparse
import os
import sys

import uvicorn

from intranet_assistant.core.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Intranet assistant command line.")
    subparsers = parser.add_subparsers(dest="command")

    serve_parser = subparsers.add_parser("serve", help="Run the API service.")
    serve_parser.add_argument("--config", default="config.yaml", help="Path to YAML config.")
    serve_parser.add_argument("--host", default=None, help="Override configured host.")
    serve_parser.add_argument("--port", type=int, default=None, help="Override configured port.")
    serve_parser.add_argument("--reload", action="store_true", help="Enable uvicorn reload for development.")

    argv = sys.argv[1:]
    if not argv or argv[0].startswith("-"):
        argv = ["serve", *argv]
    args = parser.parse_args(argv)
    if args.command == "serve":
        serve(args)


def serve(args: argparse.Namespace) -> None:
    config_path = args.config
    settings = load_settings(config_path)
    os.environ["INTRANET_ASSISTANT_CONFIG"] = config_path
    host = args.host or settings.server.host
    port = args.port or settings.server.port
    print(f"Starting intranet assistant at http://{host}:{port}")
    uvicorn.run(
        "intranet_assistant.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
