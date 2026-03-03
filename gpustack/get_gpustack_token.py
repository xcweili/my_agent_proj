#!/usr/bin/env python3
import requests
import sys
from get_ip import get_local_ip
from get_token import get_api_key_from_file

def get_gpustack_token():
    """
    获取gpustack token的脚本
    步骤：
    1. 创建集群
    2. 获取集群token【用于注册节点】
    """
    
    # 配置
    ip = get_local_ip()
    base_url = f"http://{ip}"
    auth_token = get_api_key_from_file()
    if not auth_token:
        print("Error: Failed to get API key from file", file=sys.stderr)
        sys.exit(1)
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    try:
        # 步骤1: 创建集群
        create_cluster_url = f"{base_url}/v2/clusters"
        cluster_data = {
            "provider": "Docker",
            "name": "default_cluster",
            "worker_config": {}
        }
        
        response = requests.post(create_cluster_url, headers=headers, json=cluster_data, timeout=30)
        
        if response.status_code != 200:
            print(f"Error creating cluster: HTTP {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            sys.exit(1)
        
        cluster_info = response.json()
        cluster_id = cluster_info.get("id")
        
        if not cluster_id:
            print("Error: Could not get cluster ID from response", file=sys.stderr)
            sys.exit(1)
        
        # 步骤2: 获取集群token
        get_token_url = f"{base_url}/clusters/{cluster_id}/registration-token"
        
        response = requests.get(get_token_url, headers=headers, timeout=30)
        
        if response.status_code != 200:
            print(f"Error getting token: HTTP {response.status_code}", file=sys.stderr)
            print(f"Response: {response.text}", file=sys.stderr)
            sys.exit(1)
        
        token_info = response.json()
        token = token_info.get("token")
        
        if not token:
            print("Error: Could not get token from response", file=sys.stderr)
            sys.exit(1)
        
        # 输出token
        print(token)
        return token
        
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error getting token: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    get_gpustack_token()
