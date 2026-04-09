#!/bin/bash
set -e

echo "================================"
echo "  MindSteps Server Setup"
echo "================================"

# OS тодорхойлох
. /etc/os-release
OS_ID=$ID
echo "  Илэрсэн OS: $PRETTY_NAME"

# 1. System update
echo ""
echo "[ 1/7 ] System update..."
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# 2. Суурь хэрэгслүүд
echo ""
echo "[ 2/7 ] Суурь хэрэгслүүд суулгаж байна..."
sudo apt-get install -y -qq \
  git curl wget nano htop \
  ca-certificates gnupg \
  python3 python3-pip python3-venv \
  build-essential

# 3. Docker
echo ""
echo "[ 3/7 ] Docker суулгаж байна..."
sudo install -m 0755 -d /etc/apt/keyrings

# Ubuntu эсвэл Debian гэж OS-г ялгана
if [ "$OS_ID" = "ubuntu" ]; then
  DOCKER_DISTRO="ubuntu"
else
  DOCKER_DISTRO="debian"
fi

curl -fsSL https://download.docker.com/linux/${DOCKER_DISTRO}/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/${DOCKER_DISTRO} ${VERSION_CODENAME} stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -qq
sudo apt-get install -y -qq \
  docker-ce docker-ce-cli \
  containerd.io docker-compose-plugin

# Docker-г sudo-гүй ашиглах
sudo usermod -aG docker $USER

# Docker autostart
sudo systemctl enable docker
sudo systemctl start docker

echo "  Docker $(docker --version)"

# 4. Keepalive
echo ""
echo "[ 4/7 ] Keepalive тохируулж байна..."
sudo sysctl vm.overcommit_memory=1
echo 'vm.overcommit_memory = 1' | sudo tee -a /etc/sysctl.conf

(crontab -l 2>/dev/null; echo "*/5 * * * * curl -s http://localhost:8000/health > /dev/null 2>&1") | crontab -
(crontab -l 2>/dev/null; echo "*/3 * * * * ping -c 1 8.8.8.8 > /dev/null 2>&1") | crontab -
echo "  Keepalive cron бэлэн"

# 5. Repo clone
echo ""
echo "[ 5/7 ] MindSteps repo татаж байна..."
cd ~
if [ -d "MindSteps" ]; then
  echo "  Repo байна, pull хийж байна..."
  cd MindSteps && git pull
else
  git clone https://github.com/munkhjargal333/MindSteps.git
  cd MindSteps
fi

# 6. .env үүсгэх
echo ""
echo "[ 6/7 ] .env тохиргоо..."
cd ~/MindSteps/v2back
if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "  .env үүсгэгдлээ — nano .env-ээр утгуудаа оруул"
  else
    touch .env
    echo "  Хоосон .env үүсгэгдлээ — nano .env-ээр утгуудаа оруул"
  fi
else
  echo "  .env аль хэдийн байна"
fi

# 7. Docker image татах
echo ""
echo "[ 7/7 ] Docker image татаж байна..."
cd ~/MindSteps/v2back
docker compose pull 2>/dev/null || true
docker pull redis:7-alpine

echo ""
echo "================================"
echo "  Бүгд бэлэн болоо!"
echo "================================"
echo ""
echo "Дараагийн алхам:"
echo "  1. nano ~/MindSteps/v2back/.env   ← API key-уудаа оруул"
echo "  2. cd ~/MindSteps/v2back"
echo "  3. docker compose up --build -d"
echo "  4. docker compose logs -f"
echo ""
echo "  АНХААРУУЛГА: Docker-г sudo-гүй ашиглахын тулд"
echo "  нэг удаа logout хийж дахин орно уу!"
echo "================================"