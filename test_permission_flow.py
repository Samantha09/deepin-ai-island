#!/usr/bin/env python3
"""测试 PermissionRequest 完整流程：模拟 Claude Code hook -> AI Island -> 响应。"""

import json
import socket
import sys
import time

SOCKET_PATH = "/tmp/ai-island.sock"


def test_permission_request():
    """模拟 Claude Code 触发 PermissionRequest hook。"""
    print("=== 测试 PermissionRequest 流程 ===")

    # 1. 连接 AI Island socket
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(5.0)
    try:
        sock.connect(SOCKET_PATH)
        print(f"[OK] 连接到 socket: {SOCKET_PATH}")
    except (socket.error, OSError) as e:
        print(f"[FAIL] 连接失败: {e}")
        return False

    # 2. 发送 PermissionRequest 事件（使用 hook_event_name，和 Claude Code 一样）
    event_data = {
        "session_id": "test-session-123",
        "transcript_path": "/tmp/test.jsonl",
        "cwd": "/tmp",
        "permission_mode": "acceptEdits",
        "hook_event_name": "PermissionRequest",
        "tool_name": "Bash",
        "tool_input": {"command": "echo test", "description": "Test command"},
        "tool_use_id": "tool_test_abc123",
    }

    try:
        sock.sendall(json.dumps(event_data, ensure_ascii=False).encode("utf-8"))
        print(f"[OK] 发送 PermissionRequest 事件")
        print(f"     tool_use_id: {event_data['tool_use_id']}")
    except OSError as e:
        print(f"[FAIL] 发送失败: {e}")
        return False

    # 3. 等待 AI Island 的响应（模拟用户点击 Allow/Deny）
    # 这里我们不点击 UI，而是手动测试 respond_to_permission
    # 实际流程中，AI Island 会保持 socket 打开，等待用户点击
    print("[INFO] 等待 AI Island 响应（模拟 3 秒后自动 allow）...")
    time.sleep(3)

    # 4. 另一个客户端发送 allow 响应给 AI Island
    # 实际流程中，island_window._on_permission_responded 会调用 respond_to_permission
    # 这里我们直接测试 AI Island 的响应是否正确

    # 先关闭这个 socket（因为 AI Island 会保持它打开等待响应）
    # 不关闭，而是等待 AI Island 发送响应
    try:
        sock.settimeout(10.0)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
            try:
                resp = json.loads(b"".join(chunks).decode("utf-8"))
                print(f"[OK] 收到 AI Island 响应: {json.dumps(resp, ensure_ascii=False)}")

                # 验证响应格式
                if "hookSpecificOutput" in resp:
                    hso = resp["hookSpecificOutput"]
                    if hso.get("hookEventName") == "PermissionRequest":
                        decision = hso.get("decision", {})
                        if decision.get("behavior") in ("allow", "deny"):
                            print(f"[OK] 响应格式正确: behavior={decision['behavior']}")
                            return True
                        else:
                            print(f"[FAIL] 响应缺少 behavior: {decision}")
                            return False
                    else:
                        print(f"[FAIL] 响应 hookEventName 不对: {hso.get('hookEventName')}")
                        return False
                else:
                    print(f"[FAIL] 响应缺少 hookSpecificOutput: {resp}")
                    return False
            except (json.JSONDecodeError, UnicodeDecodeError):
                continue
    except socket.timeout:
        print("[FAIL] 等待响应超时（AI Island 没有发送响应）")
        return False
    except OSError as e:
        print(f"[FAIL] 接收响应失败: {e}")
        return False
    finally:
        sock.close()

    return False


def test_permission_via_api():
    """通过 AI Island 的 respond_to_permission API 测试响应。"""
    print("\n=== 测试 respond_to_permission API ===")

    # 这个方法需要在 AI Island 运行时，通过 QTimer 或直接调用
    # 这里我们只测试 hook 脚本对响应的包装是否正确

    # 模拟 AI Island 发送的响应（approved: true）
    ai_response = {"approved": True}

    # 模拟 hook 脚本的包装逻辑
    decision = "allow" if ai_response.get("approved") else "deny"
    wrapped = {
        "hookSpecificOutput": {
            "hookEventName": "PermissionRequest",
            "decision": {
                "behavior": decision
            }
        }
    }

    output = json.dumps(wrapped, ensure_ascii=False)
    print(f"[OK] Hook 脚本输出: {output}")

    # 验证格式
    parsed = json.loads(output)
    hso = parsed.get("hookSpecificOutput", {})
    if hso.get("hookEventName") == "PermissionRequest" and hso.get("decision", {}).get("behavior") == "allow":
        print("[OK] 响应格式验证通过")
        return True
    else:
        print("[FAIL] 响应格式验证失败")
        return False


if __name__ == "__main__":
    ok1 = test_permission_via_api()
    ok2 = test_permission_request() if ok1 else False

    print("\n=== 测试结果 ===")
    if ok1 and ok2:
        print("全部通过")
        sys.exit(0)
    else:
        print("有失败")
        sys.exit(1)
