#!/bin/bash

# RAG Management System - Ubuntu Offline Installation
# 폐쇄망 Ubuntu 환경에서 실행하여 시스템을 설치합니다.

set -e

echo "==========================================="
echo "RAG Management System"
echo "Ubuntu Offline Installation"
echo "==========================================="
echo ""

# Root 권한 확인
if [ "$EUID" -ne 0 ]; then 
    echo "Error: This script must be run as root (use sudo)"
    exit 1
fi

INSTALL_DIR="/opt/ragaas"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PACKAGE_DIR="$SCRIPT_DIR/packages"

echo "Installation directory: $INSTALL_DIR"
echo "Package directory: $PACKAGE_DIR"
echo ""

# 사용자 확인
read -p "This will install RAG Management System to $INSTALL_DIR. Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 1
fi

echo ""
echo "Step 1: Checking system requirements..."
echo "-----------------------------------"

# Python 버전 확인
if ! command -v python3.11 &> /dev/null; then
    echo "Error: Python 3.11 is not installed!"
    echo "Please install Python 3.11 first:"
    echo "  sudo apt update"
    echo "  sudo apt install python3.11 python3.11-venv python3.11-dev python3-pip"
    exit 1
fi

echo "✓ Python 3.11 found: $(python3.11 --version)"

# Node.js 버전 확인
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed!"
    echo "Please install Node.js 18.x first"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "✓ Node.js found: $NODE_VERSION"

# Docker 확인
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed!"
    echo "Please install Docker first"
    exit 1
fi

echo "✓ Docker found: $(docker --version)"

# Docker Compose 확인
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Error: Docker Compose is not installed!"
    exit 1
fi

echo "✓ Docker Compose found"

echo ""
echo "Step 2: Creating installation directory..."
echo "-----------------------------------"

mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"

echo ""
echo "Step 3: Installing Python packages..."
echo "-----------------------------------"

# Backend 디렉토리 복사
cp -r "$SCRIPT_DIR/backend" ./
cd "$INSTALL_DIR/backend"

# Python 가상환경 생성
echo "Creating Python virtual environment..."
python3.11 -m venv venv

# 가상환경 활성화 및 패키지 설치
echo "Installing Python packages from offline cache..."
source venv/bin/activate

# wheel 파일들을 venv/lib로 복사하고 설치
if [ -d "$PACKAGE_DIR/python" ]; then
    pip install --no-index --find-links="$PACKAGE_DIR/python" -r requirements.txt
    echo "✓ Python packages installed"
else
    echo "Warning: No Python packages found in $PACKAGE_DIR/python"
    echo "Attempting online installation..."
    pip install -r requirements.txt
fi

deactivate

# 데이터 디렉토리 생성
mkdir -p data

echo ""
echo "Step 4: Installing Node.js packages..."
echo "-----------------------------------"

cd "$INSTALL_DIR"
cp -r "$SCRIPT_DIR/frontend" ./
cd "$INSTALL_DIR/frontend"

# Node modules 복원
if [ -f "$PACKAGE_DIR/nodejs/node_modules.tar.gz" ]; then
    echo "Extracting node_modules from offline cache..."
    tar -xzf "$PACKAGE_DIR/nodejs/node_modules.tar.gz"
    echo "✓ Node.js packages installed"
else
    echo "Warning: No Node.js packages found"
    echo "Attempting online installation..."
    npm ci
fi

# Frontend 빌드
echo "Building frontend..."
npm run build

echo "✓ Frontend built"

echo ""
echo "Step 5: Loading Docker images..."
echo "-----------------------------------"

if [ -d "$PACKAGE_DIR/docker" ]; then
    cd "$PACKAGE_DIR/docker"
    
    for image in *.tar; do
        if [ -f "$image" ]; then
            echo "Loading $image..."
            docker load -i "$image"
        fi
    done
    
    echo "✓ Docker images loaded"
else
    echo "Warning: No Docker images found"
    echo "You may need to pull images manually or use internet connection"
fi

echo ""
echo "Step 6: Setting up Docker Compose..."
echo "-----------------------------------"

cd "$INSTALL_DIR"

# Milvus/Fuseki용 docker-compose 파일 생성
cat > docker-compose.yml << 'EOF'
version: '3.5'

services:
  etcd:
    container_name: ragaas-etcd
    image: quay.io/coreos/etcd:v3.5.5
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ./volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://127.0.0.1:2379 -listen-client-urls=http://0.0.0.0:2379 --data-dir /etcd
    healthcheck:
      test: ["CMD", "etcdctl", "endpoint", "health"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

  minio:
    container_name: ragaas-minio
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - ./volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3
    restart: unless-stopped

  milvus:
    container_name: ragaas-milvus
    image: milvusdb/milvus:v2.3.3
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
      MINIO_ACCESS_KEY_ID: minioadmin
      MINIO_SECRET_KEY: minioadmin
    volumes:
      - ./volumes/milvus:/var/lib/milvus
    ports:
      - "19530:19530"
      - "9091:9091"
    depends_on:
      - etcd
      - minio
    restart: unless-stopped

  fuseki:
    container_name: ragaas-fuseki
    image: stain/jena-fuseki:4.7.0
    environment:
      - ADMIN_PASSWORD=admin
      - JVM_ARGS=-Xmx2g
    volumes:
      - ./volumes/fuseki:/fuseki
    ports:
      - "3030:3030"
    restart: unless-stopped

networks:
  default:
    name: ragaas-network
EOF

echo "✓ Docker Compose configuration created"

# 볼륨 디렉토리 생성
mkdir -p volumes/etcd volumes/minio volumes/milvus volumes/fuseki

echo ""
echo "Step 7: Creating environment configuration..."
echo "-----------------------------------"

# .env 파일 생성
if [ ! -f "$INSTALL_DIR/backend/.env" ]; then
    cp "$SCRIPT_DIR/.env.example" "$INSTALL_DIR/backend/.env"
    echo "✓ Environment file created at backend/.env"
    echo ""
    echo "⚠️  IMPORTANT: Edit backend/.env and set your OpenAI API key!"
else
    echo "✓ Environment file already exists"
fi

echo ""
echo "Step 8: Creating systemd services..."
echo "-----------------------------------"

# Backend systemd service
cat > /etc/systemd/system/ragaas-backend.service << EOF
[Unit]
Description=RAG Management System Backend
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/backend
Environment="PATH=$INSTALL_DIR/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=$INSTALL_DIR/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Frontend systemd service (using Python simple HTTP server for built files)
cat > /etc/systemd/system/ragaas-frontend.service << EOF
[Unit]
Description=RAG Management System Frontend
After=network.target ragaas-backend.service

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_DIR/frontend/dist
ExecStart=/usr/bin/python3 -m http.server 5173
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload

echo "✓ Systemd services created"

echo ""
echo "Step 9: Creating management scripts..."
echo "-----------------------------------"

# Start script
cat > "$INSTALL_DIR/start.sh" << 'EOFSTART'
#!/bin/bash
echo "Starting RAG Management System..."

# Start Docker infrastructure
cd /opt/ragaas
docker-compose up -d

# Wait for services
echo "Waiting for services to be ready..."
sleep 10

# Start backend
systemctl start ragaas-backend

# Start frontend  
systemctl start ragaas-frontend

echo "✓ All services started!"
echo ""
echo "Access the application:"
echo "  Frontend: http://$(hostname -I | awk '{print $1}'):5173"
echo "  Backend:  http://$(hostname -I | awk '{print $1}'):8000/docs"
EOFSTART

chmod +x "$INSTALL_DIR/start.sh"

# Stop script
cat > "$INSTALL_DIR/stop.sh" << 'EOFSTOP'
#!/bin/bash
echo "Stopping RAG Management System..."

systemctl stop ragaas-frontend
systemctl stop ragaas-backend

cd /opt/ragaas
docker-compose down

echo "✓ All services stopped"
EOFSTOP

chmod +x "$INSTALL_DIR/stop.sh"

# Status script
cat > "$INSTALL_DIR/status.sh" << 'EOFSTATUS'
#!/bin/bash
echo "RAG Management System Status"
echo "=============================="
echo ""

echo "Docker Services:"
cd /opt/ragaas
docker-compose ps

echo ""
echo "Backend Service:"
systemctl status ragaas-backend --no-pager | head -5

echo ""
echo "Frontend Service:"
systemctl status ragaas-frontend --no-pager | head -5
EOFSTATUS

chmod +x "$INSTALL_DIR/status.sh"

echo "✓ Management scripts created"

echo ""
echo "==========================================="
echo "✓ Installation Complete!"
echo "==========================================="
echo ""
echo "Installation directory: $INSTALL_DIR"
echo ""
echo "Next steps:"
echo "1. Edit configuration:"
echo "   sudo vi $INSTALL_DIR/backend/.env"
echo "   (Set OPENAI_API_KEY)"
echo ""
echo "2. Start services:"
echo "   sudo $INSTALL_DIR/start.sh"
echo ""
echo "3. Enable auto-start on boot:"
echo "   sudo systemctl enable ragaas-backend"
echo "   sudo systemctl enable ragaas-frontend"
echo ""
echo "Management commands:"
echo "  Start:  sudo $INSTALL_DIR/start.sh"
echo "  Stop:   sudo $INSTALL_DIR/stop.sh"
echo "  Status: sudo $INSTALL_DIR/status.sh"
echo ""
echo "Access URLs (after starting):"
echo "  Frontend: http://YOUR_SERVER_IP:5173"
echo "  Backend:  http://YOUR_SERVER_IP:8000/docs"
echo "  Fuseki:   http://YOUR_SERVER_IP:3030"
echo ""
