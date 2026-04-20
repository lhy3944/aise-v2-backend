#!/bin/bash
# Preview 배포 스크립트 (master 환경과 완전 분리)
# 사용법:
#   ./deploy/preview.sh                     # 현재 브랜치 배포
#   ./deploy/preview.sh feat/my-feature     # 특정 브랜치 배포
#   ./deploy/preview.sh --stop              # 프리뷰 중지
#
# master:  Frontend 4000, Backend 8081, DB 5432
# preview: Frontend 4100, Backend 8181, DB 5433

set -e

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[Preview]${NC} $1"; }
warn() { echo -e "${YELLOW}[Preview]${NC} $1"; }
err() { echo -e "${RED}[Preview]${NC} $1"; }

# Stop mode
if [ "$1" = "--stop" ]; then
    log "프리뷰 서버 중지 중..."
    docker compose -f docker-compose.preview.yml down
    log "프리뷰 서버 중지 완료"
    exit 0
fi

# Deploy mode
BRANCH="${1:-$(git branch --show-current)}"

log "브랜치: $BRANCH"

# Fetch and checkout
if [ -n "$1" ]; then
    log "브랜치 체크아웃 중..."
    git fetch origin "$BRANCH"
    git checkout "$BRANCH"
    git pull origin "$BRANCH"
fi

# Build and run
HOST_IP=$(hostname -I | awk '{print $1}')
export HOST_IP

log "Docker 이미지 빌드 및 실행 중..."
docker compose -f docker-compose.preview.yml up -d --build

log "========================================="
log "  Preview 배포 완료 (master와 분리)"
log "========================================="
log "  Frontend:   http://$HOST_IP:4100"
log "  Backend:    http://$HOST_IP:8181"
log "  Swagger:    http://$HOST_IP:8181/docs"
log "  DB:         $HOST_IP:5433"
log "  브랜치:     $BRANCH"
log "========================================="
log "  중지: ./deploy/preview.sh --stop"
