#!/usr/bin/env python3
"""Query basic UR controller status over the dashboard server."""

from __future__ import annotations

import argparse
import socket
import sys


DEFAULT_ROBOT_IP = "192.168.0.10"
DEFAULT_DASHBOARD_PORT = 29999
DEFAULT_TIMEOUT = 3.0

COMMANDS = [
    "robotmode",
    "safetystatus",
    "programState",
    "running",
    "is in remote control",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check UR controller state via dashboard server."
    )
    parser.add_argument(
        "--robot-ip",
        default=DEFAULT_ROBOT_IP,
        help=f"UR controller IP address, default: {DEFAULT_ROBOT_IP}",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_DASHBOARD_PORT,
        help=f"Dashboard port, default: {DEFAULT_DASHBOARD_PORT}",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Socket timeout in seconds, default: {DEFAULT_TIMEOUT}",
    )
    return parser.parse_args()


def read_line(sock: socket.socket) -> str:
    data = b""
    while not data.endswith(b"\n"):
        chunk = sock.recv(4096)
        if not chunk:
            break
        data += chunk
    return data.decode("utf-8", errors="replace").strip()


def send_command(sock: socket.socket, command: str) -> str:
    sock.sendall((command + "\n").encode("utf-8"))
    return read_line(sock)


def main() -> int:
    args = parse_args()

    try:
        with socket.create_connection(
            (args.robot_ip, args.port), timeout=args.timeout
        ) as sock:
            welcome = read_line(sock)
            print(f"dashboard: {welcome}")

            for command in COMMANDS:
                response = send_command(sock, command)
                print(f"{command}: {response}")
    except Exception as exc:
        print(
            f"无法连接到 UR dashboard {args.robot_ip}:{args.port}: {exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
