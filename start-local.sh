#!/bin/bash

# AISE 2.0 개발 서버 시작 스크립트
# 사용법: ./start-dev.sh

set -e

export PATH="$HOME/.local/bin:$PATH"

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_PORT=8082
FRONTEND_PORT=3009

# 색상
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log() { echo -e "${GREEN}[AISE]${NC} $1"; }
warn() { echo -e "${YELLOW}[AISE]${NC} $1"; }
err() { echo -e "${RED}[AISE]${NC} $1"; }

# --- 기존 프로세스 종료 ---
kill_port() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        warn "포트 $port 사용 중인 프로세스(PID: $pid) 종료"
        kill -9 $pid 2>/dev/null || true
        sleep 1
    fi
}

log "기존 프로세스 정리 중..."
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

# --- Backend ---
log "Backend 의존성 동기화 중..."
(cd "$ROOT_DIR/backend" && uv sync)
log "Backend 시작 중... (port: $BACKEND_PORT)"
(
    cd "$ROOT_DIR/backend"
    exec env PYTHONUNBUFFERED=1 uv run uvicorn src.main:app \
        --port=$BACKEND_PORT \
        --reload \
        --host 0.0.0.0 \
        --log-level debug
) 2>&1 &
BACKEND_PID=$!

# --- Frontend ---
log "Frontend 의존성 확인 중..."
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
    log "node_modules 없음 — npm install 실행"
    (cd "$ROOT_DIR/frontend" && npm install)
fi
log "Frontend 시작 중... (port: $FRONTEND_PORT, backend: $BACKEND_PORT)"
(
    cd "$ROOT_DIR/frontend"
    exec env BACKEND_URL="http://localhost:$BACKEND_PORT" \
        npx next dev --hostname 0.0.0.0 --port $FRONTEND_PORT
) 2>&1 &
FRONTEND_PID=$!
echo ""
log "========================================="
log "  AISE 2.0 개발 서버 시작 완료"
log "========================================="
SERVER_IP=$(hostname -I | awk '{print $1}')
log "  Backend:    http://$SERVER_IP:$BACKEND_PORT"
log "  Swagger:    http://$SERVER_IP:$BACKEND_PORT/docs"
log "  Frontend:   http://$SERVER_IP:$FRONTEND_PORT"
log "  PostgreSQL: $SERVER_IP:5432"
log "========================================="
log "  종료: Ctrl+C"
echo ""

# Ctrl+C로 전부 종료
cleanup() {
    echo ""
    log "서버 종료 중..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    log "서버 종료 완료 (PostgreSQL은 docker compose down으로 별도 종료)"
}

trap cleanup EXIT INT TERM
wait
