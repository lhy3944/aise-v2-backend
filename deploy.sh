#!/bin/bash
set -e

HOST_IP=$(grep HOST_IP .env 2>/dev/null | cut -d= -f2)

# .env 파일 확인
if [ ! -f .env ]; then
  echo ".env 파일이 없습니다. .env.example을 복사하여 설정하세요."
  echo "  cp .env.example .env && vi .env"
  exit 1
fi

# 사용법: ./deploy.sh [서비스명]
# 서비스명 생략 시 전체 배포, 지정 시 해당 서비스만 재시작
SERVICE=$1

if [ -z "$SERVICE" ]; then
  echo "=== 전체 배포 시작 ==="
  docker compose down
  docker compose build --no-cache
  docker compose up -d
else
  echo "=== ${SERVICE} 서비스 재시작 ==="
  docker compose up -d --build "$SERVICE"
fi

echo ""
echo "=== 완료 ==="
echo "Frontend: http://${HOST_IP:-localhost}:4000"
echo "Backend:  http://${HOST_IP:-localhost}:8081"
docker compose ps

