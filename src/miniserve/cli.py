import argparse
import sys
import time

from miniserve.server import start_server


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="miniserve",
        description="Serve static files over HTTP.",
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        default=8080,
        help="Port to listen on (default: 8080)",
    )
    parser.add_argument(
        "--dir", "-d",
        default=".",
        metavar="DIRECTORY",
        help="Directory to serve (default: current directory)",
    )
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="Open the browser automatically after starting",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    server = start_server(port=args.port, directory=args.dir, open_browser=args.open)
    print(f"Serving {args.dir!r} at http://localhost:{args.port}  (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
        sys.exit(0)


if __name__ == "__main__":
    main()
