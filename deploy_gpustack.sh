#!/bin/bash

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 超时时间（秒）
TIMEOUT=1800  # 30分钟

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查docker是否安装
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    log_info "Docker is installed."
}

# 获取本机IP地址
get_local_ip() {
    # 尝试多种方式获取本机IP
    local ip
    
    # 方法1: 使用hostname -I
    if command -v hostname &> /dev/null; then
        ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    fi
    
    # 方法2: 使用ip命令
    if [ -z "$ip" ] && command -v ip &> /dev/null; then
        ip=$(ip route get 1 2>/dev/null | awk '{print $7}' | head -1)
    fi
    
    # 方法3: 使用ifconfig
    if [ -z "$ip" ] && command -v ifconfig &> /dev/null; then
        ip=$(ifconfig 2>/dev/null | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}' | head -1)
    fi
    
    # 方法4: 回退到localhost
    if [ -z "$ip" ]; then
        log_warn "Could not detect local IP, using localhost"
        ip="localhost"
    fi
    
    echo "$ip"
}

# 等待容器启动完成
wait_for_container() {
    local container_name=$1
    local timeout=$2
    local elapsed=0
    
    log_info "Waiting for container '$container_name' to be ready..."
    
    while [ $elapsed -lt $timeout ]; do
        # 检查容器是否存在
        if ! docker ps -a --format '{{.Names}}' | grep -q "^${container_name}$"; then
            log_error "Container '$container_name' not found"
            return 1
        fi
        
        # 检查容器是否在运行
        if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
            log_info "Container '$container_name' is running"
            return 0
        fi
        
        # 检查容器是否启动失败
        local status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null || echo "")
        if [ "$status" = "exited" ] || [ "$status" = "dead" ]; then
            log_error "Container '$container_name' failed to start. Status: $status"
            log_error "Container logs:"
            docker logs "$container_name" 2>&1 | tail -20
            return 1
        fi
        
        sleep 5
        elapsed=$((elapsed + 5))
        
        # 每60秒输出一次进度
        if [ $((elapsed % 60)) -eq 0 ]; then
            local minutes=$((elapsed / 60))
            log_info "Still waiting... (${minutes} minutes elapsed)"
        fi
    done
    
    log_error "Timeout waiting for container '$container_name' to start (${timeout} seconds)"
    log_error "Container logs:"
    docker logs "$container_name" 2>&1 | tail -20
    return 1
}

# 清理旧的容器
cleanup_old_containers() {
    local containers=("gpustack" "gstack-worker")
    
    for container in "${containers[@]}"; do
        if docker ps -a --format '{{.Names}}' | grep -q "^${container}$"; then
            log_info "Removing old container '$container'..."
            docker stop "$container" 2>/dev/null || true
            docker rm "$container" 2>/dev/null || true
        fi
    done
}

# 启动gpustack服务
start_gpustack() {
    log_info "Starting gpustack service..."
    
    docker run -d \
        --name gpustack \
        --restart=unless-stopped \
        --gpus all \
        --network=host \
        --ipc=host \
        -e HF_ENDPOINT="https://hf-mirror.com" \
        -v gpustack-data:/var/lib/gpustack \
        -v /home/my_agent_proj/models:/app/models \
        gpustack/gpustack:latest
    
    if [ $? -ne 0 ]; then
        log_error "Failed to start gpustack container"
        exit 1
    fi
}

# 获取gpustack token
get_token() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local token_script="${script_dir}/gpustack/get_gpustack_token.py"
    local venv_dir="${script_dir}/.venv"
    local python_cmd="${venv_dir}/bin/python"
    
    if [ ! -f "$token_script" ]; then
        log_error "Token script not found: $token_script"
        exit 1
    fi
    
    log_info "Getting gpustack token..."
    
    if [ ! -f "$python_cmd" ]; then
        log_error "Virtual environment Python not found: $python_cmd"
        exit 1
    fi
    
    local token
    token=$("$python_cmd" "$token_script" 2>&1)
    
    if [ $? -ne 0 ] || [ -z "$token" ]; then
        log_error "Failed to get token from Python script"
        exit 1
    fi
    
    echo "$token"
}

# 启动worker容器
start_worker() {
    local token=$1
    local ip=$2
    
    log_info "Starting gstack-worker with IP: $ip"
    
    docker run -d \
        --name gstack-worker \
        --restart=unless-stopped \
        --privileged \
        --network=host \
        --gpus all \
        --volume /var/run/docker.sock:/var/run/docker.sock \
        --volume /home/my_agent_proj/models:/app/models \
        --volume gpustack-data-worker:/var/lib/gpustack \
        --runtime nvidia \
        -e GPUSTACK_RUNTIME_DEPLOY_MIRRORED_NAME=gstack-worker \
        quay.io/gpustack/gpustack:latest \
        --server-url "http://$ip" \
        --token "$token" \
        --advertise-address "$ip"
    
    if [ $? -ne 0 ]; then
        log_error "Failed to start gstack-worker container"
        exit 1
    fi
    
    log_info "Worker container started successfully"
}

# 检测Python命令
get_python_cmd() {
    if command -v python3 &> /dev/null; then
        echo "python3"
    elif command -v python &> /dev/null; then
        echo "python"
    else
        log_error "Python is not installed. Please install Python first."
        exit 1
    fi
}

# 检测pip命令
get_pip_cmd() {
    if command -v pip3 &> /dev/null; then
        echo "pip3"
    elif command -v pip &> /dev/null; then
        echo "pip"
    else
        log_error "pip is not installed. Please install pip first."
        exit 1
    fi
}

# 设置虚拟环境
setup_venv() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local venv_dir="${script_dir}/.venv"
    
    local python_cmd
    python_cmd=$(get_python_cmd)
    
    # 检查虚拟环境是否已存在
    if [ -d "$venv_dir" ]; then
        log_info "Virtual environment already exists at $venv_dir"
    else
        log_info "Creating virtual environment at $venv_dir..."
        "$python_cmd" -m venv "$venv_dir"
        
        if [ $? -ne 0 ]; then
            log_error "Failed to create virtual environment"
            exit 1
        fi
        
        log_info "Virtual environment created successfully"
    fi
    
    # 返回虚拟环境的Python和pip路径
    echo "$venv_dir"
}

# 安装Python依赖
install_python_deps() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local requirements_file="${script_dir}/requirements.txt"
    
    if [ ! -f "$requirements_file" ]; then
        log_warn "Requirements file not found: $requirements_file"
        return 1
    fi
    
    # 设置虚拟环境
    local venv_dir
    venv_dir=$(setup_venv)
    
    local pip_cmd="${venv_dir}/bin/pip"
    
    log_info "Installing Python dependencies from requirements.txt..."
    
    "$pip_cmd" install -r "$requirements_file"
    
    if [ $? -ne 0 ]; then
        log_error "Failed to install Python dependencies"
        exit 1
    fi
    
    log_info "Python dependencies installed successfully"
}

# 下载并创建模型
download_and_create_models() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local models_script="${script_dir}/gpustack/download_and_create_models.py"
    
    if [ ! -f "$models_script" ]; then
        log_warn "Models script not found: $models_script"
        return 1
    fi
    
    log_info "Starting download and create models process..."
    
    # 使用虚拟环境的Python
    local venv_dir="${script_dir}/.venv"
    local python_cmd="${venv_dir}/bin/python"
    
    if [ ! -f "$python_cmd" ]; then
        log_error "Virtual environment Python not found: $python_cmd"
        exit 1
    fi
    
    # 执行脚本并实时显示日志
    "$python_cmd" "$models_script"
    
    if [ $? -ne 0 ]; then
        log_error "Failed to download and create models"
        return 1
    fi
    
    log_info "Models download and creation completed successfully"
}

# 主函数
main() {
    log_info "=== Starting gpustack deployment script ==="
    
    # 安装Python依赖
    install_python_deps
    
    # 检查docker
    check_docker
    
    # 获取本机IP
    local ip
    ip=$(get_local_ip)
    log_info "Local IP address: $ip"
    
    # 清理旧容器
    cleanup_old_containers
    
    # 启动gpustack服务
    start_gpustack
    
    # 等待gpustack服务启动完成
    if ! wait_for_container "gpustack" "$TIMEOUT"; then
        log_error "Failed to start gpustack service within timeout"
        exit 1
    fi
    
    # 额外等待服务完全就绪
    log_info "Waiting for gpustack service to be fully ready..."
    sleep 10
    
    # 获取token
    local token
    token=$(get_token)
    log_info "Token obtained successfully"
    
    # 启动worker
    start_worker "$token" "$ip"
    
    # 等待worker启动
    if ! wait_for_container "gstack-worker" 300; then
        log_warn "Worker container may not be fully ready yet"
    fi
    
    log_info "=== Deployment completed successfully ==="
    log_info "gpustack service is running"
    log_info "gstack-worker is running"
    log_info "Access gpustack at: http://$ip"

    # 下载并创建模型
    download_and_create_models
}

# 执行主函数
main
