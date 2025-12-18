#!/bin/bash

# RAG Management System - Ubuntu Offline Package Preparation
# 인터넷이 연결된 Ubuntu 환경에서 실행하여 패키지를 준비합니다.

set -e

echo "==========================================="
echo "RAG Management System"
echo "Ubuntu Offline Package Preparation"
echo "==========================================="
echo ""

# 현재 디렉토리 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/packages"

echo "Package directory: $PACKAGE_DIR"
echo ""

# 패키지 디렉토리 생성
mkdir -p "$PACKAGE_DIR/python"
mkdir -p "$PACKAGE_DIR/nodejs"
mkdir -p "$PACKAGE_DIR/docker"
mkdir -p "$PACKAGE_DIR/system"

echo "Step 1: Downloading Python packages..."
echo "-----------------------------------"

# Python 패키지 다운로드 (wheel 형태)
cd "$PACKAGE_DIR/python"

pip3 download -r ../../../backend/requirements.txt \
    --only-binary=:all: \
    --python-version=3.11 \
    --platform=manylinux2014_x86_64 \
    --platform=linux_x86_64 \
    --abi=cp311 \
    2>&1 | tee download.log

# Universal 패키지도 다운로드 (pure Python)
pip3 download -r ../../../backend/requirements.txt \
    --only-binary=:all: \
    --python-version=3.11 \
    --platform=any \
    2>&1 | tee -a download.log

echo ""
echo "Python packages downloaded: $(ls -1 *.whl 2>/dev/null | wc -l) wheel files"
echo ""

echo "Step 2: Downloading Node.js packages..."
echo "-----------------------------------"

cd "$PACKAGE_DIR/nodejs"

# package.json 복사
cp ../../../frontend/package.json .
cp ../../../frontend/package-lock.json .

# npm 패키지 다운로드
npm ci --production=false

# node_modules를 tar로 압축 (빠른 transfer를 위해)
echo "Compressing node_modules..."
tar -czf node_modules.tar.gz node_modules/
rm -rf node_modules

echo ""
echo "Node.js packages compressed: node_modules.tar.gz"
echo ""

echo "Step 3: Downloading Docker images for Milvus/Fuseki..."
echo "-----------------------------------"

cd "$PACKAGE_DIR/docker"

# Milvus/Fuseki 관련 이미지만
IMAGES=(
    "milvusdb/milvus:v2.3.3"
    "quay.io/coreos/etcd:v3.5.5"
    "minio/minio:RELEASE.2023-03-20T20-16-18Z"
    "stain/jena-fuseki:latest"
)

for image in "${IMAGES[@]}"; do
    echo "Saving $image..."
    filename=$(echo "$image" | sed 's/:/_/g' | sed 's/\//_/g')
    docker pull "$image"
    docker save -o "${filename}.tar" "$image"
    echo "  ✓ Saved: ${filename}.tar"
done

echo ""
echo "Docker images saved: $(ls -1 *.tar 2>/dev/null | wc -l) files"
echo ""

echo "Step 4: Downloading system dependencies info..."
echo "-----------------------------------"

cd "$PACKAGE_DIR/system"

# 필요한 시스템 패키지 목록 생성
cat > apt-packages.txt << 'EOF'
# Python 빌드 도구
python3.11
python3.11-venv
python3.11-dev
python3-pip
build-essential
gcc
g++
make

# Node.js (18.x)
# Note: Ubuntu에 Node.js 18이 없으면 직접 다운로드 필요
# https://nodejs.org/dist/v18.17.0/node-v18.17.0-linux-x64.tar.xz

# Docker (이미 설치되어 있다고 가정)
# docker.io
# docker-compose

# 기타 유틸리티
git
curl
wget
vim
net-tools
EOF

echo "System package list created: apt-packages.txt"
echo ""

echo "Step 5: Creating deployment structure..."
echo "-----------------------------------"

cd "$SCRIPT_DIR"

# 소스 코드 복사
echo "Copying source code..."
rsync -av --exclude='venv' --exclude='node_modules' --exclude='dist' \
    --exclude='__pycache__' --exclude='.pytest_cache' \
    --exclude='data' --exclude='volumes' \
    ../backend ./
    
rsync -av --exclude='node_modules' --exclude='dist' \
    ../frontend ./

# 설정 파일 복사
cp ../docker-compose.yml ./docker-compose-infra.yml
cp ../.env.example ./.env.example
cp ../README.md ./
cp ../SETUP.md ./

echo ""
echo "Step 6: Creating archive..."
echo "-----------------------------------"

cd "$SCRIPT_DIR/.."
ARCHIVE_NAME="ragaas-ubuntu-offline-$(date +%Y%m%d-%H%M%S).tar.gz"

echo "Creating archive: $ARCHIVE_NAME"
tar -czf "$ARCHIVE_NAME" ubuntu_deploy/

ARCHIVE_SIZE=$(du -sh "$ARCHIVE_NAME" | cut -f1)

echo ""
echo "==========================================="
echo "✓ Preparation Complete!"
echo "==========================================="
echo ""
echo "Archive: $ARCHIVE_NAME"
echo "Size: $ARCHIVE_SIZE"
echo ""
echo "Package contents:"
echo "  - Backend source code"
echo "  - Frontend source code"
echo "  - Python packages (wheel files)"
echo "  - Node.js packages (node_modules.tar.gz)"
echo "  - Docker images (Milvus/Fuseki only)"
echo "  - Installation scripts"
echo ""
echo "Next steps:"
echo "1. Transfer $ARCHIVE_NAME to Ubuntu server"
echo "2. Extract: tar -xzf $ARCHIVE_NAME"
echo "3. Run: cd ubuntu_deploy && ./install.sh"
echo ""
