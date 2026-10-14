"""Private local CLI. Starting the tunnel exposes only the restricted receiver."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "django-service"))
from dashboard import tunnel_manager as tunnel


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("start", "status", "stop", "restart", "serve"))
    args = parser.parse_args()
    try:
        if args.action == "serve":
            tunnel.serve()
            return
        print("[%s] Receiver tunnel: %s" % (datetime.now().isoformat(timespec="seconds"), args.action), flush=True)
        if args.action in ("stop", "restart"):
            tunnel.stop_public()
            print("Managed receiver and tunnel stopped; temporary links are now offline.", flush=True)
        if args.action in ("start", "restart"):
            print(json.dumps(tunnel.ensure_public(), indent=2), flush=True)
        elif args.action == "status":
            status = tunnel.rpc("status", tunnel.config())
            if status["state"] == "ready":
                tunnel.confirm_public(status)
            print(json.dumps(status, indent=2), flush=True)
    except tunnel.TunnelError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
