#!/usr/bin/env python3
"""UpBain launcher.

Usage:
    python tool/run.py              # Production mode
    python tool/run.py --dev        # Development with auto-reload
    python tool/run.py --port 8080  # Custom port
"""
import argparse
import os
import sys
from pathlib import Path

# Ensure tool/ is on Python path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

import uvicorn


def main():
    parser = argparse.ArgumentParser(description="UpBain Control Dashboard")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    parser.add_argument("--dev", action="store_true", help="Enable auto-reload")
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    print(f"Starting UpBain on http://{args.host}:{args.port}")
    print(f"API docs: http://{args.host}:{args.port}/api/docs")

    uvicorn.run(
        "backend.app:app",
        host=args.host,
        port=args.port,
        reload=args.dev,
        workers=args.workers if not args.dev else 1,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
