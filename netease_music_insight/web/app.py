"""Launch Music Insight Local Web in the default browser."""
import argparse
import logging
import sys

from ..desktop.app import _configure_logging, app_root
from .server import start_server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Music Insight Local Web")
    parser.add_argument("--smoke", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = app_root()
    if args.smoke:
        server, thread = start_server(root, open_browser=False)
        try:
            assert server.server_address[0] == "127.0.0.1"
            print("Music Insight Local Web ready:", server.origin)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
        return 0
    _configure_logging(root)
    server, thread = start_server(root)
    print("Music Insight Local Web:", server.origin)
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
