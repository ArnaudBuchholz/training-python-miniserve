import os
import threading
from functools import partial
from http.server import HTTPServer, SimpleHTTPRequestHandler


def _make_handler(directory: str) -> type[SimpleHTTPRequestHandler]:
    return partial(SimpleHTTPRequestHandler, directory=directory)  # type: ignore[return-value]


def start_server(
    port: int = 8080,
    directory: str = ".",
    *,
    open_browser: bool = False,
) -> HTTPServer:
    """Start an HTTP file server and return the server instance.

    The server runs in a daemon thread so it stops automatically when the
    calling process exits.  Call ``server.shutdown()`` to stop it explicitly.

    Args:
        port: TCP port to listen on (default 8080).
        directory: Root directory to serve files from (default current dir).
        open_browser: If True, open the default browser after starting.

    Returns:
        The running ``HTTPServer`` instance.
    """
    directory = os.path.abspath(directory)
    handler = _make_handler(directory)
    server = HTTPServer(("", port), handler)

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    if open_browser:
        import webbrowser
        webbrowser.open(f"http://localhost:{port}")

    return server
