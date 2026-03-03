#!/usr/bin/env python3
import requests
import json
import sys
from get_ip import get_local_ip

def get_token():
    """
    获取gpustack API token的脚本
    步骤：
    1. 访问本地IP的端口，获取cookie
    2. 调用API获取API key并保存到文件
    3. 提供读取key的函数【用于后续调用API】
    """
    
    try:
        # 步骤1: 访问本地IP的端口，获取cookie
        ip = get_local_ip()
        base_url = f"http://{ip}"
        
        # 发送请求获取cookie
        response = requests.get(base_url, timeout=30)
        
        if response.status_code != 200:
            print(f"Error accessing {base_url}: HTTP {response.status_code}", file=sys.stderr)
            sys.exit(1)
        
        # 提取cookie
        cookies = response.cookies.get_dict()
        cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
        
        if not cookie_str:
            print("Error: No cookies found in response", file=sys.stderr)
            sys.exit(1)
        
        # 步骤2: 调用API获取API key
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
