#!/usr/bin/env python3
import requests
import json
import sys
import subprocess
from get_ip import get_local_ip

def get_token():
    """
    获取gpustack API token的脚本
    步骤：
    1. 从docker容器中获取初始管理员密码
    2. 使用POST请求登录获取cookie
    3. 调用API获取API key并保存到文件
    4. 提供读取key的函数【用于后续调用API】
    """
    
    try:
        # 步骤1: 从docker容器中获取初始管理员密码
        print("Getting initial admin password from docker container...")
        password_cmd = ["sudo", "docker", "exec", "-it", "gpustack", "cat", "/var/lib/gpustack/initial_admin_password"]
        
        try:
            password_result = subprocess.run(password_cmd, capture_output=True, text=True, check=True)
            password = password_result.stdout.strip()
            if not password:
                print("Error: Failed to get password from docker container", file=sys.stderr)
                sys.exit(1)
            print("Password obtained successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error executing docker command: {e}", file=sys.stderr)
            print(f"Command output: {e.output}", file=sys.stderr)
            print(f"Command stderr: {e.stderr}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error getting password: {e}", file=sys.stderr)
            sys.exit(1)
        
        # 步骤2: 使用POST请求登录获取cookie
        ip = get_local_ip()
        login_url = f"http://{ip}/auth/login"
        
        print(f"Logging in to {login_url}...")
        
        # 准备登录数据
        login_data = {
            "username": "admin",
            "password": password
        }
        
        # 发送POST请求
        response = requests.post(login_url, data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
        
        if response.status_code != 200:
            print(f"Error logging in: HTTP {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            sys.exit(1)
        
        # 提取cookie
        cookies = response.cookies.get_dict()
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        if not cookie_str:
            print("Error: No cookies found in response", file=sys.stderr)
            sys.exit(1)
        print("Login successful, cookie obtained")
        
        # 步骤3: 调用API获取API key
        api_url = f"http://{ip}/v2/api-keys"
        headers = {
            "Cookie": cookie_str,
            "Content-Type": "application/json"
        }
        
        data = {
            "name": "api_test",
            "expires_in": 0,
            "allowed_model_names": []
        }
        
        print(f"Creating API key at {api_url}...")
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        
        if response.status_code != 200:
            print(f"Error creating API key: HTTP {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            sys.exit(1)
        
        api_key_info = response.json()
        
        # 检查value字段是否存在且不为空
        if "value" not in api_key_info or not api_key_info["value"]:
            print("Error: No value field found in response", file=sys.stderr)
            sys.exit(1)
        
        # 保存到本地文件
        with open("gpustack_key.json", "w", encoding="utf-8") as f:
            json.dump(api_key_info, f, indent=2, ensure_ascii=False)
        
        print("API key saved to gpustack_key.json")
        return api_key_info["value"]
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def get_api_key_from_file():
    """
    读取gpustack_key.json文件，返回其中的value字段值
    """
    try:
        with open("gpustack_key.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "value" not in data:
            print("Error: No value field found in gpustack_key.json", file=sys.stderr)
            return None
        
        return data["value"]
        
    except FileNotFoundError:
        print("Error: gpustack_key.json file not found", file=sys.stderr)
        return None
    except json.JSONDecodeError:
        print("Error: Invalid JSON in gpustack_key.json", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error reading API key: {e}", file=sys.stderr)
        return None

if __name__ == "__main__":
    # 执行获取token的流程
    token = get_token()
    print(f"Obtained API key: {token}")
    
    # 测试读取函数
    read_token = get_api_key_from_file()
    if read_token:
        print(f"Read API key from file: {read_token}")
