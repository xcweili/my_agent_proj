#!/bin/bash

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# 检查docker compose是否可用
check_docker_compose() {
    if ! command -v docker &> /dev/null; then
        log_error "docker is not installed. Please install docker first."
        exit 1
    fi
    log_info "docker compose is available."
}

# 主函数
main() {
    log_info "=== Starting dify deployment script ==="
    
    # 检查docker和docker-compose
    check_docker
    check_docker_compose
    
    # 进入/home目录
    log_info "Changing to /home directory..."
    cd /home
    
    # Step 1: 克隆dify仓库
    log_info "Step 1: Cloning dify repository..."
    if [ -d "dify" ]; then
        log_warn "dify directory already exists, removing it..."
        rm -rf dify
    fi
    
    git clone https://github.com/langgenius/dify.git --depth=1
    if [ $? -ne 0 ]; then
        log_error "Failed to clone dify repository"
        exit 1
    fi
    
    # Step 2: 复制.env.example为.env
    log_info "Step 2: Copying .env.example to .env..."
    cd dify
    cp .env.example .env
    
    # Step 3: 进入docker目录，修改.env文件
    log_info "Step 3: Modifying .env file in docker directory..."
    cd docker
    
    # 修改端口为8083
    log_info "  - Changing NGINX_PORT and EXPOSE_NGINX_PORT to 8083..."
    sed -i 's|NGINX_PORT=80|NGINX_PORT=8083|g' .env
    sed -i 's|EXPOSE_NGINX_PORT=80|EXPOSE_NGINX_PORT=8083|g' .env
    
    # 设置api服务的最大连接数
    log_info "  - Setting SERVER_WORKER_CONNECTIONS to 30..."
    sed -i 's|SERVER_WORKER_CONNECTIONS=10|SERVER_WORKER_CONNECTIONS=30|g' .env
    
    # Step 4: 执行docker compose up -d
    log_info "Step 4: Starting dify services..."
    docker compose up -d
    
    if [ $? -ne 0 ]; then
        log_error "Failed to start dify services"
        exit 1
    fi
    
    log_info "=== Dify deployment completed successfully ==="
    log_info "Dify service is running on port 8083"
    log_info "Access dify at: http://localhost:8083"
}

# 执行主函数
main
