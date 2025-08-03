# DY 골프 카트 관리 시스템

골프장 운영 효율성을 극대화하는 스마트 골프 카트 관제 및 관리 플랫폼

## 🎯 프로젝트 개요

DY 골프 카트는 골프장의 카트 운영을 디지털화하고 자동화하는 종합 관리 시스템입니다. 실시간 카트 모니터링, 안전 관리, 운영 최적화를 통해 골프장 운영자와 이용객 모두에게 향상된 경험을 제공합니다.

## 📋 주요 기능

### 1. 맵 에디터
- **지도 관리**
  - 골프장 지도 생성 및 커스터마이징
  - 18홀 코스 정보 관리
  - 위험 구역 및 공사 구역 표시
  - 최적 경로 설계 및 수정

### 2. 카트 관제 시스템
- **실시간 모니터링 및 제어**
  - GPS 기반 카트 위치 추적
  - 카트 상태 실시간 확인 (배터리, 속도, 이상 여부)
  - 경로 제어 및 자동 안내
  - 장애 발생 시 즉시 알림
  - 구역별 속도 및 접근 제한
  - 관제센터-카트 간 실시간 메시지 교환

- **안전 관리**
  - 타구 사고 방지 시스템
  - 동적 진입 제한 구역 설정
  - 긴급 상황 대응 프로토콜

### 3. 백오피스
- **골프장 관리**
  - 골프장 정보 등록 (명칭, 코스 정보, 운영 시간)
  - 다중 골프장 통합 관리
  - 관리자 계정 및 권한 관리

- **통계 및 리포트**
  - 운영 데이터 실시간 통계
  - 핵심 성과 지표(KPI) 대시보드
  - 데이터 시각화 및 인사이트 제공
  - 맞춤형 리포트 생성

- **회전율 관리**
  - 스마트 카트 배정 시스템
  - 팀별 진행 상황 모니터링
  - 티업 스케줄 자동 관리
  - 병목 구간 분석 및 최적화

## 🔐 사용자 권한 체계

### 권한 레벨
1. **마스터 관리자**: 전체 시스템 관리, 골프장 등록
2. **골프장 관리자**: 해당 골프장 전체 기능 관리
3. **골프장 서브 관리자**: 제한된 관리 기능
4. **관제 요원**: 카트 모니터링 및 제어
5. **일반 사용자**: 카트 예약 및 이용

### 계정 생성 플로우
- 골프장 관리자: 회원가입 → 마스터 승인 → 계정 활성화
- 서브 관리자: 회원가입 → 골프장 관리자 승인 → 계정 활성화

## 🛠 기술 스택

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL 14+
- **Authentication**: Keycloak
- **ORM**: SQLAlchemy
- **Real-time**: WebSocket

### Infrastructure
- **Container**: Docker & Docker Compose
- **Message Queue**: Redis/RabbitMQ
- **Monitoring**: Prometheus + Grafana

## 🚀 시작하기

### 사전 요구사항
- Docker & Docker Compose
- Python 3.11 이상
- PostgreSQL 14 이상
- Keycloak 인스턴스

### 설치 및 실행

1. **저장소 클론**
```bash
git clone https://github.com/viadevelopers/DY-golfcart-monolith.git
cd DY-golfcart-monolith
```

2. **환경 변수 설정**
```bash
cp .env.example .env
# .env 파일을 열어 필요한 값들을 설정
```

3. **Docker 서비스 시작**
```bash
docker-compose up -d
```

4. **데이터베이스 초기화**
```bash
./init-db.sh
```

5. **의존성 설치**
```bash
pip install -r requirements.txt
```

6. **애플리케이션 실행**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📚 API 문서

애플리케이션 실행 후 아래 주소에서 API 문서를 확인할 수 있습니다:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🏗 프로젝트 구조

```
DY-golfcart-monolith/
├── app/                    # 애플리케이션 코드
│   ├── main.py            # FastAPI 앱 진입점
│   ├── config.py          # 설정 관리
│   ├── database.py        # DB 연결 설정
│   ├── models/            # SQLAlchemy 모델
│   ├── schemas/           # Pydantic 스키마
│   ├── routers/           # API 라우트 핸들러
│   ├── services/          # 비즈니스 로직
│   └── middleware/        # 커스텀 미들웨어
├── docs/                  # 문서
├── keycloak-theme/        # Keycloak 커스텀 테마
├── tests/                 # 테스트 코드
├── scripts/               # 유틸리티 스크립트
├── docker-compose.yml     # Docker 서비스 정의
└── requirements.txt       # Python 의존성
```

## 🧪 개발

### 테스트 실행
```bash
pytest
```

### 코드 품질 관리
```bash
# 포맷팅
black app/
isort app/

# 린팅
flake8 app/

# 타입 체크
mypy app/
```

## 📈 로드맵

- [ ] 모바일 앱 연동
- [ ] AI 기반 경로 최적화
- [ ] 음성 안내 시스템
- [ ] 다국어 지원
- [ ] 클라우드 마이그레이션

## 🤝 기여하기

프로젝트 기여를 환영합니다! [기여 가이드라인](.github/CONTRIBUTING.md)을 참고해주세요.

## 📝 라이선스

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 💬 문의 및 지원

- 이슈 및 기능 요청: [GitHub Issues](https://github.com/viadevelopers/DY-golfcart-monolith/issues)
- 이메일: support@dygolf.com
- 문서: [프로젝트 위키](https://github.com/viadevelopers/DY-golfcart-monolith/wiki)