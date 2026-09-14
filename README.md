# SAMDI_FASTAPI — 진상 캐릭터 챗봇 (RAG)

RAG로 검색한 "진상 손님 사례"를 근거로 LLM이 진상 손님을 연기하는 대화 API.
사용자는 매장 직원 입장에서 응대하고, 캐릭터는 사례의 말투·행동 패턴을 흉내 낸다.

## 왜 RAG인가

캐릭터 챗봇은 보통 프롬프트만으로 만들지만, 그러면 말투가 금방 단조로워진다.
사례를 벡터 DB에 넣어두고 **매 턴 상황에 맞는 사례를 검색해 프롬프트에 주입**하면,

- 장소·상황이 바뀔 때마다 다른 트집과 다른 말투가 나오고
- 캐릭터를 늘리고 싶을 때 **코드가 아니라 JSONL 한 줄만 추가**하면 되고
- 답변이 어떤 사례를 근거로 나왔는지 `sources`로 추적된다.

## 동작 흐름

```
사용자 발화 ──► 질의 생성(직전 맥락 + 이번 발화 + 장소)
                 │
                 ▼
          ChromaDB 유사도 검색 ──► 상위 K개 사례
                 │
                 ▼
     시스템 프롬프트 = 연기 규칙 + 가드레일 + 난이도 + 검색된 사례
                 │
                 ▼
             LLM 호출 ──► 진상 캐릭터 답변 + sources
```

## 구조

```
app/
├── config.py           # .env 기반 설정
├── schemas.py          # 요청/응답 모델
├── main.py             # FastAPI 엔드포인트
├── rag/
│   ├── embeddings.py   # OpenAI / 로컬 임베딩 provider
│   └── store.py        # ChromaDB 적재·검색
└── chat/
    ├── persona.py      # 페르소나 프롬프트 + 안전 가드레일
    └── engine.py       # 검색 → 프롬프트 → LLM, 세션 관리
data/jinsang_cases.jsonl  # 지식베이스 (진상 사례 20건)
scripts/build_index.py    # 인덱스 빌드
scripts/smoke_test.py     # API 키 없이 파이프라인 검증
static/index.html         # 테스트용 채팅 화면
```

## 실행

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # OPENAI_API_KEY 채우기

python scripts/build_index.py          # 벡터 인덱스 생성 (데이터 바뀔 때마다)
uvicorn app.main:app --reload          # http://127.0.0.1:8000
```

브라우저에서 `http://127.0.0.1:8000` → 채팅 UI, `/docs` → Swagger.

API 키 없이 동작 확인:

```bash
python scripts/smoke_test.py
```

## API

| 메서드 | 경로 | 설명 |
|---|---|---|
| POST | `/chat` | 진상 캐릭터와 대화 (`session_id`, `message`, `scene`, `difficulty`) |
| POST | `/chat/reset` | 세션 히스토리 초기화 |
| GET | `/search` | 검색 결과만 확인 (디버그용) |
| GET | `/health` | 인덱스 건수·모델 확인 |
| POST | `/admin/reindex` | 데이터 재적재 |

```bash
curl -X POST localhost:8000/chat -H 'Content-Type: application/json' \
  -d '{"session_id":"t1","message":"고객님, 어떤 점이 불편하셨을까요?","scene":"카페","difficulty":"hard"}'
```

## 캐릭터/사례 추가하기

`data/jinsang_cases.jsonl`에 한 줄 추가하고 `python scripts/build_index.py` 재실행.

```json
{"id":"c021","type":"…형","place":"…","trigger":"…","behavior":"…",
 "lines":["…","…"],"escalation":"…","weakness":"…"}
```

`lines`(대표 대사)가 말투를 좌우하므로 실제 들릴 법한 구어체로 쓸 것.

## 안전장치

`app/chat/persona.py`의 `BASE_RULES`에 욕설·혐오 표현·위협·개인정보 요구 금지가 명시돼 있다.
불쾌함은 "무리한 요구와 태도"로만 표현하도록 제한했고, 사용자가 `그만/종료/나가기`를 입력하면 즉시 역할을 멈춘다.

## 남은 과제

- 세션 히스토리가 프로세스 메모리에 있음 → Redis/DB로 교체
- 응대 점수/피드백 기능 (연습 모드로 확장할 경우)
- 사례 데이터 확충 및 검색 품질 평가셋 구축
