#!/usr/bin/env python3
"""Send Robotiq gripper commands to a UR controller over Ethernet.

This script reuses the vendor-provided `gripper.script` file in this folder,
replaces the demo movement at the end with the requested command, and sends
the generated URScript program to the UR controller.
"""

from __future__ import annotations

import argparse
import errno
import socket
import sys
from pathlib import Path


DEFAULT_UR_PORT = 30001
DEFAULT_ROBOT_IP = "192.168.0.10"
DEFAULT_GRIPPER_SOCKET_ID = "1"
DEFAULT_TIMEOUT = 5.0
SCRIPT_PATH = Path(__file__).with_name("gripper.script")
TAIL_MARKER = '  $ 1 "机器人程序"\n'


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def load_base_program() -> str:
    if not SCRIPT_PATH.exists():
        raise FileNotFoundError(f"Missing URScript template: {SCRIPT_PATH}")

    script = SCRIPT_PATH.read_text(encoding="utf-8")
    marker_index = script.rfind(TAIL_MARKER)
    if marker_index == -1:
        raise RuntimeError(
            "Could not find the demo section in gripper.script. "
            "The template format may have changed."
        )
    return script[:marker_index]


def build_motion_lines(
    action: str,
    socket_id: str,
    position: int | None,
    speed: int,
    force: int,
) -> list[str]:
    lines = [
        "  # Custom command injected by control_gripper.py",
        f'  rq_set_speed_norm({speed}, "{socket_id}")',
        f'  rq_set_force_norm({force}, "{socket_id}")',
    ]

    if action == "activate":
        lines.append(f'  rq_activate_and_wait("{socket_id}")')
    elif action == "open":
        lines.append(f'  rq_open_and_wait("{socket_id}")')
    elif action == "close":
        lines.append(f'  rq_close_and_wait("{socket_id}")')
    elif action == "move":
        if position is None:
            raise ValueError("The 'move' action requires --position.")
        lines.append(f'  rq_move_and_wait_norm({position}, "{socket_id}")')
    elif action == "grasp":
        sequence = [0, 50, 60, 70, 10]
        for index, step in enumerate(sequence):
            lines.append(f'  rq_move_and_wait_norm({step}, "{socket_id}")')
            if index != len(sequence) - 1:
                lines.append("  sleep(3.0)")
    else:
        raise ValueError(f"Unsupported action: {action}")

    lines.append("end")
    lines.append("gripper()")
    lines.append("")
    return lines


def build_program(
    action: str,
    socket_id: str,
    position: int | None,
    speed: int,
    force: int,
) -> str:
    base_program = load_base_program()
    motion_lines = build_motion_lines(action, socket_id, position, speed, force)
    return base_program + "\n".join(motion_lines)


def send_program(robot_ip: str, port: int, program: str, timeout: float) -> None:
    with socket.create_connection((robot_ip, port), timeout=timeout) as sock:
        sock.sendall(program.encode("utf-8"))


def format_error(exc: Exception, robot_ip: str, port: int) -> str:
    if isinstance(exc, socket.timeout):
        return (
            f"连接超时：无法连接到 UR 控制器 {robot_ip}:{port}。"
            "请确认机械臂已开机、网线已连接，并且电脑与机械臂在同一网段。"
        )

    if isinstance(exc, socket.gaierror):
        return (
            f"地址解析失败：{robot_ip} 不是有效的 IP 地址或主机名。"
            "如果你是直接连接 UR5，请使用类似 192.168.0.10 的实际地址。"
        )

    if isinstance(exc, OSError):
        if exc.errno == errno.EHOSTUNREACH:
            return (
                f"主机不可达：无法到达 {robot_ip}:{port}。"
                "请检查电脑网卡是否已设置为 192.168.0.x 网段。"
            )
        if exc.errno == errno.ENETUNREACH:
            return (
                f"网络不可达：当前电脑没有到 {robot_ip}:{port} 的路由。"
                "请先给有线网卡配置 192.168.0.20/24。"
            )
        if exc.errno == errno.ECONNREFUSED:
            return (
                f"连接被拒绝：{robot_ip}:{port} 没有接受连接。"
                "请确认 UR 远程控制和脚本端口可用。"
            )

    return f"控制夹爪失败：{exc}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Control a Robotiq 2F gripper through a UR controller."
    )
    parser.add_argument(
        "--robot-ip",
        default=DEFAULT_ROBOT_IP,
        help=(
            "IP address of the UR controller, "
            f"default: {DEFAULT_ROBOT_IP}"
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_UR_PORT,
        help=f"UR script port, default: {DEFAULT_UR_PORT}",
    )
    parser.add_argument(
        "--socket-id",
        default=DEFAULT_GRIPPER_SOCKET_ID,
        help='Robotiq gripper socket ID in URCap, default: "1"',
    )
    parser.add_argument(
        "action",
        choices=["activate", "open", "close", "move", "grasp"],
        help="Gripper action to execute",
    )
    parser.add_argument(
        "--position",
        type=int,
        help="Target opening in percent for move, 0=open, 100=closed",
    )
    parser.add_argument(
        "--speed",
        type=int,
        default=100,
        help="Gripper speed in percent, 0-100, default: 100",
    )
    parser.add_argument(
        "--force",
        type=int,
        default=100,
        help="Gripper force in percent, 0-100, default: 100",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT,
        help=f"Socket timeout in seconds, default: {DEFAULT_TIMEOUT}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the generated URScript instead of sending it",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    speed = clamp(args.speed, 0, 100)
    force = clamp(args.force, 0, 100)
    position = None if args.position is None else clamp(args.position, 0, 100)

    try:
        program = build_program(
            action=args.action,
            socket_id=args.socket_id,
            position=position,
            speed=speed,
            force=force,
        )
        if args.dry_run:
            sys.stdout.write(program)
            return 0

        send_program(args.robot_ip, args.port, program, args.timeout)
    except Exception as exc:
        print(format_error(exc, args.robot_ip, args.port), file=sys.stderr)
        return 1

    print(
        f"URScript 已发送到 {args.robot_ip}:{args.port} "
        f"(gripper socket {args.socket_id}, action={args.action})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
