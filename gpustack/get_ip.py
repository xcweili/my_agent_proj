#!/usr/bin/env python3
import socket
import subprocess

def get_local_ip():
    """
    获取本机IP地址
    支持多种获取方式，按优先级尝试：
    1. 使用hostname -I命令
    2. 使用socket连接外部服务器
    3. 回退到localhost
    
    Returns:
        str: 本机IP地址
    """
    try:
        # 方法1: 使用hostname -I
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        if result.returncode == 0:
            ip = result.stdout.strip().split()[0]
            if ip:
                return ip
    except Exception:
        pass
    
    try:
        # 方法2: 使用socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        pass
    
    # 回退到localhost
    return "localhost"

if __name__ == "__main__":
    print(get_local_ip())
