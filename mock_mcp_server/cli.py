"""CLI-вход для запуска мокового MCP-сервера.

Примеры:
    python -m mock_mcp_server --transport stdio
    python -m mock_mcp_server --transport streamable-http --host 0.0.0.0 --port 8081
"""

from __future__ import annotations

import argparse
import os

from .server import build_app


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Запуск мокового MCP-сервера HR-агента")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http", "sse"],
        default=os.environ.get("MOCK_MCP_TRANSPORT", "stdio"),
        help="Транспорт MCP (по умолчанию stdio или $MOCK_MCP_TRANSPORT)",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Адрес интерфейса для HTTP (по умолчанию 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8081, help="Порт для HTTP (по умолчанию 8081)")
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    mcp = build_app()

    if args.transport in ("streamable-http", "sse"):
        mcp.run(transport=args.transport, host=args.host, port=args.port)
    else:
        mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
