# UR5 + Robotiq 2F85 夹爪控制说明

这个目录用于通过电脑网线向 UR5 控制器发送 URScript，从而控制已经接到 UR 控制柜上的 Robotiq 2F85 二指夹爪。

目录中的几个核心文件：

- `gripper.script`
  Robotiq URCap 生成的原始 URScript 驱动模板。
- `control_gripper.py`
  夹爪控制脚本。会读取 `gripper.script`，拼出完整 URScript，然后发送到 UR5。
- `check_ur_status.py`
  读取 UR 控制器 dashboard 状态，用来排查“命令发出去了但机械臂/夹爪没动作”的情况。

## 工作原理

本项目不是直接从电脑连夹爪，而是：

1. 夹爪已经接到 UR5 控制柜。
2. 电脑通过网线连接 UR5 控制器。
3. Python 脚本把 URScript 发给 UR5。
4. UR5 再调用 Robotiq 的 URCap 接口控制夹爪。

所以，真正执行夹爪动作的是 UR 控制器，不是电脑直接驱动夹爪硬件。

## 当前默认配置

- UR5 控制器 IP：`192.168.0.10`
- 电脑有线网卡建议 IP：`192.168.0.20/24`
- URScript 发送端口：`30001`
- Dashboard 端口：`29999`
- 默认夹爪编号：`1`

## 使用前提

请先确认以下条件成立：

1. 夹爪已经正确连接到 UR 控制柜。
2. 示教器里的 Robotiq gripper 小程序可以正常控制夹爪。
3. 电脑和 UR5 之间网线已经连接好。
4. 机器人已经开机，并处于可运行状态。
5. `gripper.script` 文件保留在当前目录中。

## 网络配置

如果电脑直连 UR5，建议给电脑有线网卡配置固定 IP。

当前这台电脑实际使用的有线网卡名是：

```bash
enx00e04c504a70
```

可以用下面的命令临时配置网络：

```bash
sudo ip addr flush dev enx00e04c504a70
sudo ip addr add 192.168.0.20/24 dev enx00e04c504a70
sudo ip link set enx00e04c504a70 up
ping 192.168.0.10
```

如果 `ping 192.168.0.10` 能持续收到返回，说明电脑和 UR5 网络已经打通。

停止 `ping` 可以按：

```bash
Ctrl + C
```

## 机器人状态检查

如果夹爪不动作，先检查 UR 控制器状态：

```bash
python3 check_ur_status.py
```

正常情况下，至少应满足：

- `robotmode` 不是 `POWER_OFF`
- `safetystatus` 是 `NORMAL`

如果 `robotmode: POWER_OFF`，说明机器人还没有上电，需要先在示教器上执行：

1. `Power On`
2. `Brake Release`

在从电脑发送夹爪命令前，还建议确认：

1. UR5 电源已经打开
2. 示教器上的当前程序已经停止

如果示教器上有程序正在运行，外部下发的夹爪脚本可能不会按预期执行。

## 首次使用流程

建议第一次上电后按下面顺序操作：

1. 打开 UR5 电源

2. 在示教器上停止当前程序

3. 检查网络是否通

```bash
ping 192.168.0.10
```

4. 检查机器人状态

```bash
python3 check_ur_status.py
```

5. 第一次手动激活夹爪

```bash
python3 control_gripper.py activate
```

说明：

- `activate` 主要用于首次上电后的夹爪激活。
- 后续正常运行时，`open`、`close`、`move`、`grasp` 不会重复自动激活。

## 常用控制命令

完全张开：

```bash
python3 control_gripper.py open
```

完全闭合：

```bash
python3 control_gripper.py close
```

移动到指定开合百分比：

```bash
python3 control_gripper.py move --position 40
```

设置速度和力度：

```bash
python3 control_gripper.py move --position 40 --speed 60 --force 80
```

查看将要发送的 URScript，但不真正发送：

```bash
python3 control_gripper.py open --dry-run
```

## 位置含义

夹爪位置使用 0 到 100 的归一化范围：

- `0`：更接近全开
- `50`：大致半开
- `100`：更接近全闭

常见示例：

```bash
python3 control_gripper.py move --position 0
python3 control_gripper.py move --position 50
python3 control_gripper.py move --position 100
```

## 当前固定动作序列

脚本里提供了一个固定动作 `grasp`：

```bash
python3 control_gripper.py grasp
```

这个动作会按下面的顺序执行：

1. 移动到 `0`
2. 等待 `3` 秒
3. 移动到 `50`
4. 等待 `3` 秒
5. 移动到 `60`
6. 等待 `3` 秒
7. 移动到 `70`
8. 等待 `3` 秒
9. 移动到 `10`

也就是说，当前固定序列是：

```text
0 -> 50 -> 60 -> 70 -> 10
```

每一步之间间隔 `3` 秒。

## 参数说明

`control_gripper.py` 支持以下参数：

- `action`
  可选值：`activate`、`open`、`close`、`move`、`grasp`
- `--position`
  仅 `move` 需要，范围 `0` 到 `100`
- `--speed`
  夹爪速度百分比，范围 `0` 到 `100`
- `--force`
  夹爪力度百分比，范围 `0` 到 `100`
- `--robot-ip`
  机器人 IP，默认 `192.168.0.10`
- `--port`
  URScript 端口，默认 `30001`
- `--socket-id`
  Robotiq 夹爪编号，默认 `1`
- `--timeout`
  连接超时时间，默认 `5.0` 秒
- `--dry-run`
  只打印 URScript，不发送给机器人

查看帮助：

```bash
python3 control_gripper.py --help
python3 check_ur_status.py --help
```

## 典型使用场景

场景 1：首次上电后，先激活再控制

```bash
python3 check_ur_status.py
python3 control_gripper.py activate
python3 control_gripper.py open
python3 control_gripper.py close
```

场景 2：直接运行固定动作序列

```bash
python3 control_gripper.py grasp
```

场景 3：手动移动到某个位置

```bash
python3 control_gripper.py move --position 50
```

## 常见问题排查

### 1. 能 ping 通，但夹爪不动

先检查机器人状态：

```bash
python3 check_ur_status.py
```

重点看：

- `robotmode`
- `safetystatus`
- `programState`

如果机器人没上电，先在示教器上执行 `Power On` 和 `Brake Release`。

### 2. 终端提示 “URScript 已发送”，但没有动作

这通常说明：

- 网络是通的
- UR 端口是可连接的
- 但机器人当前状态不允许执行，或者机器人未处于正确运行状态

先运行：

```bash
python3 check_ur_status.py
```

同时检查：

1. UR5 是否已经上电
2. 示教器上的程序是否已经停止
3. 当前是否有弹窗、保护停或阻塞状态

### 3. 地址解析失败

如果出现类似：

```text
地址解析失败
```

通常是因为把占位符字符串当成了 IP 使用。请直接使用真实 IP，例如：

```bash
python3 control_gripper.py --robot-ip 192.168.0.10 open
```

### 4. 主机不可达或网络不可达

请检查：

1. 网线是否连接正常
2. 电脑有线网卡是否已经配置 `192.168.0.20/24`
3. UR 控制器 IP 是否确实是 `192.168.0.10`

## 文件说明

- [control_gripper.py](/mnt/DOCUMENT/UR5_2f85/control_gripper.py)
  主控制脚本
- [check_ur_status.py](/mnt/DOCUMENT/UR5_2f85/check_ur_status.py)
  UR 控制器状态检查脚本
- [gripper.script](/mnt/DOCUMENT/UR5_2f85/gripper.script)
  Robotiq URScript 模板

## 后续可扩展内容

如果后面还需要，可以继续扩展成下面几种形式：

- 把动作序列改成可配置，而不是写死在 `grasp` 里
- 增加一键启动脚本
- 加入机械臂位姿运动，形成完整抓取流程
- 把“张开 -> 接近 -> 闭合 -> 抬起”做成完整自动化程序
