#!/usr/bin/env python3
import os
import sys
import asyncio
import shutil
import json
import requests
from pathlib import Path
from modelscope import snapshot_download
from get_ip import get_local_ip
from get_token import get_api_key_from_file

async def download_model(model_name):
    """
    从model_scope下载指定模型到models目录下
    
    Args:
        model_name: 模型名称
    """
    # 创建models目录
    models_dir = Path("models")
    models_dir.mkdir(exist_ok=True)
    
    # 处理model名中包含斜杠的情况，创建嵌套目录
    model_path_parts = model_name.split('/')
    model_dir = models_dir
    for part in model_path_parts:
        model_dir = model_dir / part
    
    if model_dir.exists():
        print(f"警告: 模型目录 {model_dir} 已存在，将覆盖现有内容")
        shutil.rmtree(model_dir)
    model_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"开始下载模型: {model_name}")
    
    try:
        # 使用modelscope的snapshot_download方法下载模型
        # 设置local_dir为model_dir，这样模型文件会直接存放在以model_name命名的目录下
        downloaded_dir = snapshot_download(
            model_id=model_name,
            local_dir=str(model_dir)
        )
        
        print(f"{model_name} 下载完成!")
        print(f"模型已保存到: {downloaded_dir}")
        
        return True
        
    except Exception as e:
        print(f"{model_name} 错误: {e}")
        return False

async def create_model_instance(model_name, backend_parameters):
    """
    创建model实例
    调用 /v2/models 接口创建模型
    
    Args:
        model_name: 模型名称
        backend_parameters: 后端参数列表
    """
    
    # 配置
    ip = get_local_ip()
    base_url = f"http://{ip}"
    auth_token = get_api_key_from_file()
    if not auth_token:
        print(f"{model_name} Error: Failed to get API key from file")
        return False
    
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }
    
    # 构建local_path，使用/app/models/ + 实际的model_name
    local_path = f"/app/models/{model_name}"
    
    # 模型数据
    model_data = {
        "name": model_name.replace("/", "_"),
        "source": "local_path",
        "cluster_id": 1,
        "backend": "vLLM",
        "backend_version": None,
        "replicas": 1,
        "extended_kv_cache": {
            "enabled": False
        },
        "speculative_config": {
            "enabled": False
        },
        "categories": [],
        "backend_parameters": backend_parameters,
        "distributed_inference_across_workers": False,
        "restart_on_error": True,
        "generic_proxy": False,
        "local_path": local_path,
        "placement_strategy": "spread",
        "gpu_selector": None
    }
    
    try:
        # 调用API创建模型
        create_model_url = f"{base_url}/v2/models"
        
        response = requests.post(create_model_url, headers=headers, json=model_data, timeout=60)
        
        if response.status_code != 200:
            print(f"{model_name} Error creating model: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
        model_info = response.json()
        print(f"{model_name} Model created successfully:")
        print(f"Model ID: {model_info.get('id')}")
        print(f"Model Name: {model_info.get('name')}")
        print(f"Status: {model_info.get('status')}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"{model_name} Network error: {e}")
        return False
    except Exception as e:
        print(f"{model_name} Error creating model: {e}")
        return False

async def process_model(model_config):
    """
    处理单个模型：先下载，然后创建
    
    Args:
        model_config: 模型配置对象，包含name和backend_parameters
    """
    model_name = model_config.get("name")
    backend_parameters = model_config.get("backend_parameters", [])
    
    if not model_name:
        print("Error: 模型配置缺少name字段")
        return False
    
    # 先下载模型
    download_success = await download_model(model_name)
    if not download_success:
        return False
    
    # 下载成功后，创建模型实例
    create_success = await create_model_instance(model_name, backend_parameters)
    return create_success

def load_models_config(config_file="models_config.json"):
    """
    从JSON配置文件加载模型配置
    
    Args:
        config_file: 配置文件路径
        
    Returns:
        模型配置列表
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        if not isinstance(config, list):
            print(f"Error: 配置文件格式错误，应该是一个对象数组")
            return []
        
        return config
        
    except FileNotFoundError:
        print(f"Error: 配置文件 {config_file} 不存在")
        return []
    except json.JSONDecodeError as e:
        print(f"Error: 配置文件JSON格式错误: {e}")
        return []
    except Exception as e:
        print(f"Error: 读取配置文件失败: {e}")
        return []

async def main():
    # 从JSON配置文件加载模型配置
    model_configs = load_models_config()
    
    if not model_configs:
        print("没有可用的模型配置，程序退出")
        return
    
    print(f"从配置文件加载了 {len(model_configs)} 个模型配置")
    
    # 创建任务列表
    tasks = []
    for model_config in model_configs:
        task = asyncio.create_task(process_model(model_config))
        tasks.append(task)
    
    # 等待所有任务完成
    results = await asyncio.gather(*tasks)
    
    # 统计结果
    success_count = sum(results)
    total_count = len(results)
    
    print(f"\n处理完成: {success_count}/{total_count} 个模型处理成功")

if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
