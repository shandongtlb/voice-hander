from __future__ import annotations

import argparse
import os
import uvicorn

from intranet_assistant.core.config import load_settings


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the intranet assistant API.")
    parser.add_argument("--config", default="config.yaml", help="Path to YAML config.")
    parser.add_argument("--host", default=None, help="Override configured host.")
    parser.add_argument("--port", type=int, default=None, help="Override configured port.")
    args = parser.parse_args()

    settings = load_settings(args.config)
    os.environ["INTRANET_ASSISTANT_CONFIG"] = args.config
    host = args.host or settings.server.host
    port = args.port or settings.server.port
    uvicorn.run(
        "intranet_assistant.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
