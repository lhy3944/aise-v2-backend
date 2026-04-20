# AISE 2.0 - 吏꾪뻾 ?곹솴 (PROGRESS)

> 媛??먯씠?꾪듃???묒뾽 ?쒖옉/?꾨즺 ?????뚯씪???낅뜲?댄듃??寃?
> ?묒뾽 怨꾪쉷? PLAN.md 李몄“.

## ?꾩옱 ?곹깭

| ?곸뿭 | ?곹깭 | 鍮꾧퀬 |
|------|------|------|
| Backend 蹂댁씪?ы뵆?덉씠??| Done | FastAPI + Loguru + CORS + 誘몃뱾?⑥뼱 + ?덉쇅泥섎━ |
| Frontend | Done | Next.js 16 + ?꾨줈?앺듃/?붽뎄?ы빆/Glossary/Assist ?섏씠吏 援ы쁽 |
| DB | Done | PostgreSQL 16 + SQLAlchemy + asyncpg + Alembic |
| ?꾨줈?앺듃 CRUD | Done | Project CRUD + Settings API 援ы쁽 ?꾨즺 |
| ?붽뎄?ы빆 CRUD | Done | Requirement CRUD + ?쇨큵 ?좏깮/?댁젣 + 踰꾩쟾 ???+ ?섎쾭留?FR-001) + ?쒖꽌 蹂寃?+ ?뚯씠釉?酉?|
| Glossary CRUD | Done | Glossary CRUD + LLM ?먮룞 ?앹꽦 API 援ы쁽 ?꾨즺 |
| AI ?댁떆?ㅽ듃 | Done | refine + suggest + chat(?먯뿰?ㅻ윭????붿껜 + ?붿껌 ??異붿텧 + 泥댄겕諛뺤뒪 諛섏쁺) |
| ?뚯뒪???명봽??| Done | pytest 86媛?(83 passed, 3 skipped: Session ?뚯씠釉?誘멸뎄異??섍꼍) |
| ?붽뎄?ы빆 Review | Done | Review API + ?꾨＼?꾪듃 + ?뚯뒪??6媛?援ы쁽 ?꾨즺 |
| ?붽뎄?ы빆 ?뱀뀡(洹몃９?? | Done | Section CRUD API + ?꾨줎??UI (?묎린/?쇱튂湲? ?쒕옒洹? ?뱀뀡 媛??대룞) |
| Knowledge Repository | Done | Backend: pgvector + MinIO + RAG Chat API. Frontend: API ?곕룞 ?꾨즺 (?낅줈???좉?/誘몃━蹂닿린/?ъ쿂由? |
| Frontend 援ъ“ ?ъ꽕怨?| Done | /chat??agent, ArtifactPanel ?고뙣?? Records ??쑝濡??꾪솚 |
| Phase 2 ?꾨줈?앺듃 湲곕컲 | Done | 吏????μ냼 媛뺥솕 + ?⑹뼱 ?ъ쟾 ?뺤옣 + ?뱀뀡 愿由??ъ꽕怨?+ ?꾨줈?앺듃 以鍮꾨룄 |
| Phase 3 Agent 肄붿뼱 | Done | Record 紐⑤뜽/CRUD/異붿텧 API + Agent ?덉씠?꾩썐 + ?≪뀡 移대뱶 + Function Calling |
| Phase 4 SRS ?앹꽦 | In Progress | SRS 紐⑤뜽/API/?꾨＼?꾪듃 ?꾨즺, ?꾨줎??SRS ??UI 誘멸뎄??|
| LLM Provider | Done | LLM_PROVIDER ?섍꼍蹂?섎줈 OpenAI/Azure ?먮룞 ?꾪솚 |
| 梨꾪똿 UI | Done | Message 而댄룷?뚰듃 ?ъ꽕怨? Tool Call UI, Function Calling ?곕룞 |
| ?ㅼ쨷 ?몄뀡 + URL ?쇱슦??| Done | Session/Message DB 紐⑤뜽, CRUD API, /agent/[sessionId] ?쇱슦?? ?몄뀡蹂??낅┰ ?ㅽ듃由щ컢 |
| 諛깆뿏???덉쭏 由ы뙥?좊쭅 | Done | Record/Agent ?낅젰 寃利?媛뺥솕, Record ?뱀씤 ?깅뒫 理쒖쟻?? ?뚯뒪??蹂닿컯 |

## ?묒뾽 濡쒓렇

### 2026-04-16 (諛깆뿏??由ы뙥?좊쭅 2李? Requirement/Section ????덉젙??
- **Requirement/Section API ?낅젰 ????뺣━**:
  - `RequirementSelectionUpdate.requirement_ids`, `RequirementReorderRequest.ordered_ids`瑜?UUID 諛곗뿴濡?蹂寃?
  - `SectionReorderRequest.ordered_ids`瑜?UUID 諛곗뿴濡?蹂寃?
  - ?섎せ??ID ?낅젰???쒕퉬???덈꺼 500???꾨땲???붿껌 寃利??④퀎(422)?먯꽌 李⑤떒?섎룄濡??뺣━
- **Requirement `section_id` ?섏쐞 ?명솚 ?좎?**:
  - `RequirementCreate/RequirementUpdate.section_id`瑜?UUID ??낆쑝濡?蹂寃?
  - ?꾨줎?몄뿉??蹂대궡??`section_id: ""`瑜?`None`?쇰줈 ?뺢퇋?뷀븯??validator 異붽?
- **?쒕퉬??由ы뙥?좊쭅**:
  - `requirement_svc`, `section_svc`?먯꽌 ?섎룞 `uuid.UUID(...)` 蹂???쒓굅
  - reorder/selection 濡쒖쭅??UUID ???湲곕컲?쇰줈 ?⑥닚??
- **?뚯뒪??蹂닿컯**:
  - 湲곗〈 `tests/test_requirement.py`??3媛?耳?댁뒪 異붽?
    - `section_id=''` ?낅뜲?댄듃 ?명솚
    - selection invalid UUID 422
    - reorder invalid UUID 422
  - ?좉퇋 `tests/test_section.py` 異붽? (湲곕낯 ?뱀뀡 ?먮룞 ?앹꽦, reorder invalid UUID 422)
  - 寃利?寃곌낵: `uv run pytest tests/` ??**72 passed**

### 2026-04-16 (諛깆뿏??由ы뙥?좊쭅 3李? reorder ?쇨???+ Record 李몄“ 臾닿껐??
- **reorder 怨듯넻 ?덉젙??*:
  - `src/utils/reorder.py` 異붽? (`build_reordered_ids`)濡?遺遺?reorder瑜??꾩껜 ?쒖꽌濡??덉쟾 ?뺤옣
  - `requirement_svc`, `section_svc`, `record_svc`??reorder瑜?怨듯넻 洹쒖튃?쇰줈 ?뺣━
  - ?④낵: 遺遺?reorder媛 ?욌?遺꾩씠 ?꾨땲?대룄 `order_index` 異⑸룎 ?놁씠 0..N-1 ?곗냽??蹂댁옣
- **Record 李몄“ 臾닿껐??媛뺥솕**:
  - `record_svc`??source document ?꾨줈?앺듃 ?뚯냽 寃利?異붽?
  - create/approve?먯꽌 援먯감 ?꾨줈?앺듃 `source_document_id` 李몄“瑜?400?쇰줈 李⑤떒
- **Record ?쇱슦??踰꾧렇 ?섏젙**:
  - `/records/reorder`媛 `/{record_id}`??媛?ㅼ졇 422媛 諛쒖깮?섎뜕 寃쎈줈 留ㅼ묶 臾몄젣 ?섏젙
  - ?뺤쟻 寃쎈줈(`/reorder`)瑜??숈쟻 寃쎈줈(`/{record_id}`)蹂대떎 癒쇱? ?좎뼵
- **?뚯뒪??蹂닿컯**:
  - `tests/test_requirement.py`: 遺遺?reorder 鍮꾩꽑??耳?댁뒪 異붽?
  - `tests/test_section.py`: 遺遺?reorder 鍮꾩꽑??耳?댁뒪 異붽?
  - `tests/test_record.py`: 遺遺?reorder 鍮꾩꽑??invalid UUID/create쨌approve 援먯감 ?꾨줈?앺듃 source document 李⑤떒 耳?댁뒪 異붽?
  - 寃利?寃곌낵: `uv run pytest tests/` ??**78 passed**

### 2026-04-16 (諛깆뿏??由ы뙥?좊쭅 4李? 湲곕낯 ?뱀뀡 蹂듦뎄 ?덉젙??
- **湲곕낯 ?뱀뀡 蹂댁옣 濡쒖쭅 媛쒖꽑**:
  - `section_svc._ensure_default_sections()`瑜?"湲곕낯 ?뱀뀡 議댁옱 ?щ?(count>0)" 湲곗??먯꽌
    "湲곕낯 ?뱀뀡 ??낅퀎 ?꾨씫 ?щ?" 湲곗??쇰줈 蹂寃?
  - 遺遺??좎떎 ?곹깭(?? 湲곕낯 5醫?以??쇰? ??젣)?먯꽌???꾨씫??湲곕낯 ?뱀뀡留??먮룞 蹂닿컯
  - 諛섎났 議고쉶 ??以묐났 ?앹꽦 ?놁씠 ?덉젙?곸쑝濡??좎?
- **?뚯뒪??蹂닿컯**:
  - `tests/test_section.py`
    - 湲곕낯 ?뱀뀡 以묐났 ?앹꽦 諛⑹?(諛섎났 議고쉶) 寃利?
    - 湲곕낯 ?뱀뀡 ?쇰? ??젣 ???먮룞 蹂듦뎄 寃利?
  - 寃利?寃곌낵: `uv run pytest tests/` ??**80 passed**

### 2026-04-16 (諛깆뿏??由ы뙥?좊쭅 5李? UUID ?쇨???+ Glossary/Session 臾닿껐??
- **Assist/Review ?낅젰 寃利??쇱썝??*:
  - `SuggestRequest.requirement_ids`, `ReviewRequest.requirement_ids`瑜?UUID 諛곗뿴濡?蹂寃?
  - ?쒕퉬?ㅼ쓽 ?섎룞 UUID ?뚯떛 ?쒓굅
  - invalid UUID??400(鍮꾩쫰?덉뒪 ?먮윭) ???422(?붿껌 寃利??먮윭)濡??쇨? 泥섎━
- **Glossary 李몄“ 臾닿껐??媛뺥솕**:
  - `GlossaryCreate.source_document_id`瑜?UUID ??낆쑝濡?蹂寃?
  - create/approve?먯꽌 source document???꾨줈?앺듃 ?뚯냽 寃利?異붽? (援먯감 ?꾨줈?앺듃 李몄“ 李⑤떒)
- **Session ?앹꽦 ?덉젙??媛뺥솕**:
  - `SessionCreate.project_id`瑜?UUID ??낆쑝濡?蹂寃?
  - ?몄뀡 ?앹꽦 ???꾨줈?앺듃 議댁옱 ?щ? 寃利?異붽?(?놁쑝硫?404)
- **?뚯뒪??蹂닿컯**:
  - `tests/test_assist.py`: suggest invalid UUID 422 耳?댁뒪 異붽?
  - `tests/test_review.py`: invalid UUID 湲곕?媛?422濡??뺣젹
  - `tests/test_glossary.py`: create/approve 援먯감 ?꾨줈?앺듃 source document 李⑤떒 耳?댁뒪 異붽?
  - ?좉퇋 `tests/test_session.py` 異붽? (?몄뀡 ?앹꽦/寃利??쒕굹由ъ삤)
    - ?꾩옱 ?뚯뒪??DB??sessions ?뚯씠釉붿씠 ?녿뒗 ?섍꼍??怨좊젮???대떦 寃쎌슦 skip 泥섎━
  - 寃利?寃곌낵: `uv run pytest tests/` ??**83 passed, 3 skipped**

### 2026-04-16 (諛깆뿏??由ы뙥?좊쭅: Record/Agent ?덉젙??+ ?뚯뒪??蹂닿컯)
- **Record API/?ㅽ궎留?????뺣━**:
  - `RecordCreate/RecordUpdate/RecordReorderRequest`??ID ?꾨뱶瑜?UUID ??낆쑝濡?蹂寃?
  - `/records` 議고쉶/異붿텧??`section_id` 荑쇰━瑜?UUID濡?蹂寃쏀븯???섎せ???낅젰??422濡?議곌린 李⑤떒
- **Record ?쒕퉬??由ы뙥?좊쭅**:
  - ?뱀뀡 寃利??ы띁 異붽?: ?ㅻⅨ ?꾨줈?앺듃 ?뱀뀡 ID 李몄“ ??400?쇰줈 紐낇솗???ㅽ뙣
  - `approve_records()` 理쒖쟻?? ??ぉ蹂?諛섎났 議고쉶 ?쒓굅, display_id/order_index瑜?諛곗튂 怨꾩궛
  - display_id ?묐몢???쒗??怨꾩궛 濡쒖쭅???ы띁 ?⑥닔濡?遺꾨━??以묐났 異뺤냼
- **Agent/Knowledge ?ㅽ궎留??덉젙??*:
  - `AgentChatRequest.session_id`瑜?UUID ??낆쑝濡?蹂寃? ?쇱슦???섎룞 UUID ?뚯떛 ?쒓굅
  - `AgentChatRequest.attachments`, `KnowledgeChatRequest.history`??`default_factory` ?곸슜 (mutable 湲곕낯媛??쒓굅)
- **?뚯뒪??蹂닿컯**:
  - ?좉퇋: `tests/test_record.py` (UUID 寃利? 援먯감 ?꾨줈?앺듃 ?뱀뀡 李⑤떒, ?뱀씤 梨꾨쾲 ?곗냽??
  - ?좉퇋: `tests/test_agent.py` (?섎せ??session_id 422)
  - `tests/conftest.py` cleanup 媛쒖꽑: ?ㅼ젣 議댁옱?섎뒗 ?뚯씠釉붾쭔 ??젣?섎룄濡?蹂寃?
  - 寃利?寃곌낵: `uv run pytest tests/` ??**67 passed**

### 2026-04-07 (?ㅼ쨷 ?몄뀡 + URL ?쇱슦??
- **Backend ?몄뀡 紐⑤뜽**:
  - Session, SessionMessage DB 紐⑤뜽 (UUID PK, project FK, JSONB tool_calls/tool_data)
  - Alembic 留덉씠洹몃젅?댁뀡 (sessions, session_messages ?뚯씠釉?+ ?몃뜳??
  - Session CRUD ?쒕퉬??+ ?쇱슦??(POST/GET/PATCH/DELETE /api/v1/sessions)
- **Agent Chat session_id 湲곕컲 ?꾪솚**:
  - ?붿껌?먯꽌 history[] ?쒓굅 ??session_id留??꾨떖
  - 諛깆뿏?쒓? DB?먯꽌 理쒓렐 50媛?硫붿떆吏 濡쒕뱶?섏뿬 history濡??ъ슜
  - user 硫붿떆吏: ?ㅽ듃由щ컢 ????? assistant 硫붿떆吏: ?ㅽ듃由щ컢 ?꾨즺 ?????
  - 泥?硫붿떆吏 ???몄뀡 ?쒕ぉ ?먮룞 ?ㅼ젙 (泥?40??
- **Frontend URL ?쇱슦??*:
  - `/agent` (?????empty state), `/agent/[sessionId]` (?뱀젙 ?몄뀡)
  - 泥?硫붿떆吏 ?꾩넚 ??POST /sessions ??UUID 諛쒓툒 ??router.replace濡?URL 蹂寃?
  - session-service.ts: ?몄뀡 CRUD API ?대씪?댁뼵??
- **Chat Store 由ы뙥?곕쭅**:
  - Thread 湲곕컲 ??Session 湲곕컲 (sessionMessages Record, streamingSessionIds Set)
  - localStorage persist ?쒓굅 (?쒕쾭媛 source of truth)
  - ?몄뀡蹂??낅┰ ?ㅽ듃由щ컢 ?곹깭 (?ㅼ쨷 ?몄뀡 ?숈떆 吏??
- **而댄룷?뚰듃 ?낅뜲?댄듃**:
  - ChatArea: sessionId props, ?쒕쾭 硫붿떆吏 濡쒕뱶, ?몄뀡 ?앹꽦 + URL 蹂寃?
  - SessionList/SessionItem: ?쒕쾭 湲곕컲 ?몄뀡 紐⑸줉 (ThreadList/ThreadItem ?泥?
  - LeftSidebar, MobileBottomDrawer: SessionList ?ъ슜

### 2026-04-05~06 (Phase 2~4 援ы쁽)
- **Phase 2.1 吏????μ냼 媛뺥솕**:
  - KnowledgeDocument: is_active ?꾨뱶, ?곹깭媛??뺣━ (pending/processing/completed/failed)
  - ??API: ?좉?, 誘몃━蹂닿린, 以묐났媛먯?(409+overwrite), ?ъ쿂由?
  - document_processor: ?낅┰ DB ?몄뀡 (BackgroundTask ?몄뀡 ?ロ옒 踰꾧렇 ?섏젙)
  - Frontend: ProjectKnowledgeTab API ?곕룞, KnowledgePreviewModal (MD ?뚮뜑留??먮Ц Tabs)
- **Phase 2.2 ?⑹뼱 ?ъ쟾 ?뺤옣**:
  - GlossaryItem: synonyms, abbreviations, section_tags, source_document_id, is_approved
  - ??API: POST /glossary/extract (吏??臾몄꽌 湲곕컲), POST /glossary/approve
- **Phase 2.3 ?뱀뀡 愿由??ъ꽕怨?*:
  - RequirementSection: description, output_format_hint, is_required, is_default, is_active
  - ?꾨줈?앺듃 ?앹꽦 ??湲곕낯 5醫??뱀뀡 ?먮룞 ?앹꽦 (lazy init ?ы븿)
  - 湲곕낯 ?뱀뀡 ??젣 蹂댄샇, ?좉?, AI 異붿텧 API
  - ?꾨줈?앺듃 ?곸꽭??"?뱀뀡" ??異붽?
- **Phase 2.4 ?꾨줈?앺듃 以鍮꾨룄**:
  - GET /projects/{id}/readiness 吏묎퀎 API
  - ?꾨줈?앺듃 紐⑸줉 移대뱶??以鍮꾨룄 ?몃뵒耳?댄꽣 (?꾩씠肄??レ옄+?좏샇??
  - Zustand readiness-store + invalidate() ?⑦꽩 (?ㅼ떆媛?諛섏쁺)
  - Agent 醫뚰뙣?먯뿉 ReadinessMiniView
- **Phase 3.1-3.2 Record 紐⑤뜽 + 異붿텧**:
  - Record 紐⑤뜽: content, display_id, section_id, source, confidence_score, status
  - CRUD API + 異붿텧 API (extract, extract-section, approve)
  - 異붿텧 ?꾨＼?꾪듃: 吏?앸Ц??+ ?뱀뀡 + ?⑹뼱 ???뱀뀡蹂??덉퐫??+ ?좊ː??
- **Phase 3.3 Agent ?덉씠?꾩썐**:
  - ?고뙣?? ArtifactPanel Requirements?뭃ecords ???꾪솚, RecordsArtifact (?뱀뀡 洹몃９?? ?꾪꽣, ?곹깭 ?꾪솚)
  - 醫뚰뙣?? ReadinessMiniView
  - RightPanel??ArtifactPanel ?곌껐 (鍮?div ?섏젙)
- **Phase 3.4 ?≪뀡 移대뱶 + 梨꾪똿 ?곕룞**:
  - ActionCards: 4醫??뚰겕?뚮줈??移대뱶 (以鍮꾨룄 湲곕컲 ?쒖꽦/鍮꾪솢??
  - 移대뱶 ?대┃ ??extract API 吏곸젒 ?몄텧 ??Records ???꾨낫 ?쒖떆 ???뱀씤
- **Function Calling ?꾪솚**:
  - agent_svc: tools ?뺤쓽 (extract_records, generate_srs)
  - SSE tool_call ?대깽???꾩넚, ?꾨줎?몄뿉??援ъ“?붾맂 泥섎━
  - tool-call.tsx: Collapsible Tool Call UI (?곹깭 諭껋?, Input/Output)
  - ChatArea: onToolCall ??executeToolCall ?붿뒪?⑥쿂 ???곹깭 ?낅뜲?댄듃
- **Phase 4.1 SRS ?앹꽦 (諛깆뿏??**:
  - SrsDocument/SrsSection DB 紐⑤뜽 + Alembic 留덉씠洹몃젅?댁뀡
  - API: generate, list, get, section edit, regenerate
  - ?꾨＼?꾪듃: IEEE 830 湲곕컲, ?뱀뀡蹂??덉퐫?쒋넂臾몄꽌 梨뺥꽣, Traceability [FR-001]
- **梨꾪똿 UI ?ъ꽕怨?*:
  - message.tsx: Message/MessageAvatar/MessageContent/MessageResponse/MessageBubble/MessageActions
  - MessageRenderer ?ъ꽕怨?(留덊겕?ㅼ슫 ?뚮뜑留? Tool Call UI ?듯빀)
  - 梨꾪똿 ?덉씠?꾩썐: ?섎떒 40vh ?щ갚 (??硫붿떆吏媛 ?곷떒???꾩튂)
  - Agent ?꾨＼?꾪듃: tool call ???덈궡 硫붿떆吏 異쒕젰 洹쒖튃
- **LLM Provider ?꾪솚**:
  - llm_svc: LLM_PROVIDER ?섍꼍蹂??(openai/azure), get_client() ?먮룞 ?꾪솚
  - embedding_svc: provider蹂?紐⑤뜽 ?먮룞 ?좏깮
- **?덉씠?꾩썐 ?섏젙**:
  - Agent layout: h-[calc(100dvh-3.75rem)] ?믪씠 怨좎젙
  - ?⑤꼸 ?좉? ?곗륫 ?뺣젹, 紐⑤컮??諛섏쓳??(??異뺤빟 ?쇰꺼, 以鍮꾨룄 諛뷀??쒗듃)

### 2026-04-02 (Knowledge Repository + Frontend 援ъ“ ?ъ꽕怨?
- **?명봽??*:
  - `docker-compose.yml`: postgres ??`pgvector/pgvector:pg16` ?대?吏 蹂寃?+ MinIO ?쒕퉬??異붽?
  - `pyproject.toml`: pgvector, minio, pymupdf, python-docx, python-pptx, openpyxl, tiktoken 異붽?
  - Alembic 留덉씠洹몃젅?댁뀡: `CREATE EXTENSION vector` + knowledge_documents/knowledge_chunks ?뚯씠釉?+ HNSW ?몃뜳??
- **諛깆뿏??Knowledge API**:
  - `models/knowledge.py`: KnowledgeDocument, KnowledgeChunk (Vector(3072))
  - `schemas/api/knowledge.py`: Document/Chat ?붿껌/?묐떟 ?ㅽ궎留?
  - `services/storage_svc.py`: MinIO ?섑띁 (upload/download/delete)
  - `services/embedding_svc.py`: Azure OpenAI text-embedding-3-large 諛곗튂 ?꾨쿋??
  - `utils/text_chunker.py`: tiktoken 湲곕컲 ?ш? 臾몄옄 遺꾪븷 (500?좏겙, 50 overlap)
  - `services/document_processor.py`: ?뚯떛(PDF/DOCX/PPTX/XLSX/TXT)?믪껌?밟넂?꾨쿋?⒱넂????뚯씠?꾨씪??
  - `services/knowledge_svc.py`: 臾몄꽌 CRUD + BackgroundTasks 鍮꾨룞湲?泥섎━
  - `services/rag_svc.py`: pgvector cosine distance 寃??+ Glossary 而⑦뀓?ㅽ듃 + LLM ?묐떟
  - `prompts/knowledge/chat.py`: RAG ?꾨＼?꾪듃 (異쒖쿂 ?몄슜 洹쒖튃)
  - `routers/knowledge.py`: 5媛??붾뱶?ъ씤??(?낅줈??紐⑸줉/?곸꽭/??젣/RAG chat)
- **?꾨줎?몄뿏??援ъ“ ?ъ꽕怨?*:
  - `/chat` ??`/agent` ?쇱슦??蹂寃?+ `middleware.ts` redirect
  - `config/navigation.ts` ?낅뜲?댄듃
  - `stores/artifact-store.ts`: ArtifactType ???곹깭 愿由?
  - `components/artifacts/ArtifactPanel.tsx`: ?고뙣??硫붿씤 (Requirements|SRS|Design|TC ??
  - `components/artifacts/RequirementsArtifact.tsx`: requirements/page.tsx?먯꽌 異붿텧 (projectId prop 諛⑹떇)
  - `components/artifacts/{Srs,Design,TestCase}Artifact.tsx`: placeholder 而댄룷?뚰듃
  - `components/layout/RightPanel.tsx`: ArtifactPanel ?뚮뜑
  - `components/layout/MobileRightDrawer.tsx`: ??댄? ?낅뜲?댄듃
  - `app/(main)/projects/[id]/layout.tsx`: 湲곕낯 ??overview ??knowledge
  - `next.config.ts`: turbopack.root ?ㅼ젙 異붽?
  - TypeScript ??낆껜???듦낵

### 2026-03-30 (?붽뎄?ы빆 ?뱀뀡/洹몃９??湲곕뒫 ??FR-RQ-01-23~30)
- **?붽뎄?ы빆 臾몄꽌 ?낅뜲?댄듃**: FR-RQ-01-23~30 異붽? (?뱀뀡 CRUD, ?쒕옒洹? ?묎린/?쇱튂湲? SRS 諛섏쁺, Import ?곕룞)
- **DB 紐⑤뜽**: `RequirementSection` ?뚯씠釉??앹꽦 (project_id, type, name, order_index) + `Requirement.section_id` FK 異붽? (SET NULL)
- **留덉씠洹몃젅?댁뀡**: `cef0a99d1daf_add_requirement_sections`
- **諛깆뿏??API**:
  - `section_svc.py` ???뱀뀡 CRUD + ?쒖꽌 蹂寃?
  - `requirement_svc.py` ??section_id 吏??(?묐떟, ?앹꽦, ?섏젙, ?ㅻ깄??
  - `/api/v1/projects/{id}/requirement-sections` ??GET/POST/PUT/DELETE + reorder
- **?꾨줎?몄뿏??*:
  - `Section` ???+ `section-service.ts` API ?대씪?댁뼵??
  - `RequirementTable.tsx` 媛쒗렪 ???뱀뀡 ?ㅻ뜑(?묎린/?쇱튂湲?, ?뱀뀡 ??媛??쒕옒洹? 誘몃텇瑜??곸뿭, ?몃씪???뱀뀡 CRUD
  - `page.tsx` ???뱀뀡 ?곗씠??fetch, CRUD ?몃뱾?? ?뱀뀡 ?대룞 ?몃뱾???듯빀
- **?뚯뒪??*: 56 passed (湲곗〈 ?뚯뒪???꾩껜 ?듦낵)

### 2026-03-29 (???紐⑤뱶 媛쒖꽑 ???먯뿰?ㅻ윭?????+ 泥댄겕諛뺤뒪 異붿텧)
- **???紐⑤뱶 ?꾨＼?꾪듃 ?꾨㈃ ?ъ옉??(FR-RQ-01-04~06)**
  - ?먯뿰?ㅻ윭????붿껜 ??(?뺥삎?붾맂 吏덈Ц ?섏뿴 ???먯뿰?ㅻ윭?????
  - 異붿텧 ??대컢: 留??묐떟 ?먮룞 ???ъ슜??紐낆떆???붿껌 ?쒖뿉留?('?뺣━?댁쨾', '?붽뎄?ы빆 戮묒븘以? ??
  - 紐낇솗???낅젰? 利됱떆 ?뺤젣 ?쒖븞, 紐⑦샇???낅젰? ??붾줈 援ъ껜??
  - 湲곗〈 ?붽뎄?ы빆??諛곌꼍 而⑦뀓?ㅽ듃濡쒕쭔 ?쒖슜 (display_id ?ы븿, 紐낆떆???섏뿴 X)
  - ?????refine 吏??('?ㅻ벉?댁쨾' ???뺤젣 寃곌낵 ?먯뿰?ㅻ읇寃??쒖븞)
- **泥댄겕諛뺤뒪 紐⑸줉 UI (ExtractedRequirementList.tsx)**
  - 異붿텧???붽뎄?ы빆????낅퀎(FR/QA/Constraints) 洹몃９?뷀븯??泥댄겕諛뺤뒪 紐⑸줉?쇰줈 ?쒖떆
  - 湲곕낯 誘몄꽑???곹깭, ?ъ슜?먭? ?뺤씤 ???먰븯??寃껊쭔 泥댄겕
  - '諛섏쁺' 踰꾪듉 ???뺤씤 ?ㅼ씠?쇰줈洹????섎떒 ?뚯씠釉붿뿉 異붽?
- **???紐⑤뱶 ?섎떒 ?붽뎄?ы빆 ?뚯씠釉??꾪솴 ?쒖떆** (FR/QA/CON ?? RequirementTable ?ъ궗??
- **?붽뎄?ы빆 Description truncate ?쒓굅** ???띿뒪???꾩껜 ?쒖떆 (whitespace-pre-wrap)
- ?붽뎄?ы빆 臾몄꽌 FR-RQ-01-04~06 ?낅뜲?댄듃 + FR-RQ-01-05-01~03 ?좉퇋 異붽?
- ?뚯뒪??56媛??꾩껜 ?듦낵 + Next.js 鍮뚮뱶 ?듦낵

### 2026-03-29 (?붽뎄?ы빆 ?섎쾭留?+ ?뚯씠釉?酉?
- **?붽뎄?ы빆 ?먮룞 ?섎쾭留?援ы쁽 (FR-RQ-01-20)**
  - DB: `display_id` (String, ?? FR-001, QA-001, CON-001) + `order_index` (Integer) ?꾨뱶 異붽?
  - Alembic 留덉씠洹몃젅?댁뀡 ?앹꽦 諛??곸슜
  - ?앹꽦 ????낅퀎 ?먮룞 ?섎쾭留?(FR-001, FR-002, ...), ??젣 ??踰덊샇 ?ъ궗??????
- **?붽뎄?ы빆 ?쒖꽌 蹂寃?API 援ы쁽 (FR-RQ-01-21)**
  - `PUT /api/v1/projects/{id}/requirements/reorder` ???쒕옒洹????쒕∼ ?쒖꽌 蹂寃?
  - `RequirementReorderRequest` ?ㅽ궎留?(ordered_ids 諛곗뿴)
  - 紐⑸줉 議고쉶 ??`order_index` 湲곗? ?뺣젹, 踰꾩쟾 ??μ뿉 display_id/order_index ?ы븿
- **AUTOSAD ?ㅽ????뚯씠釉?酉?(FR-RQ-01-22)**
  - `RequirementTable.tsx`: ?뚯씠釉??뺥깭 (No./Description/Include/Actions)
  - ?쒕옒洹????쒕∼?쇰줈 ???쒖꽌 蹂寃?(HTML5 Drag API)
  - ?몃씪???몄쭛 (Edit 踰꾪듉 ??Textarea ??Cmd+Enter/???
  - 湲곗〈 移대뱶??`RequirementItem` ???뚯씠釉?酉곕줈 援먯껜
- ?붽뎄?ы빆 臾몄꽌 FR-RQ-01-20~22, interface.md, PLAN.md ?낅뜲?댄듃
- ?뚯뒪??54媛??꾩껜 ?듦낵 + Next.js 鍮뚮뱶 ?듦낵

### 2026-03-29 (Phase 1.5 ???紐⑤뱶 Chat Frontend UI 援ы쁽)
- **???紐⑤뱶(Chat) ?꾨줎?몄뿏??UI 援ы쁽 (FR-RQ-01-04~07)**
  - `types/project.ts`: ChatMessage, ExtractedRequirement, ChatRequest, ChatResponse ???異붽?
  - `services/assist-service.ts`: `chat()` 硫붿꽌??異붽?
  - `components/projects/ChatPanel.tsx`: ???梨꾪똿 ?⑤꼸 (硫붿떆吏 紐⑸줉, ?낅젰, ?꾩넚, 濡쒕뵫, 異붿텧???붽뎄?ы빆 ?쒖떆)
  - `components/projects/ExtractedRequirementCard.tsx`: 異붿텧???붽뎄?ы빆 移대뱶 (???諭껋?, ?섏젙 媛??textarea, ?섎씫/嫄곗젅)
  - `app/(main)/projects/[id]/requirements/page.tsx`: 援ъ“??紐⑤뱶 / ???紐⑤뱶 ?꾪솚 ?좉? 異붽?
  - other ????섎씫 ??fr濡?fallback 泥섎━
  - ?섎씫???붽뎄?ы빆? requirementService.create瑜??듯빐 DB ???+ ?붽뎄?ы빆 紐⑸줉??諛섏쁺
  - Next.js 鍮뚮뱶 ?듦낵 ?뺤씤

### 2026-03-29 (Phase 2.1 ?붽뎄?ы빆 Review API 援ы쁽)
- **?붽뎄?ы빆 Review API 援ы쁽 (FR-RQ-02)**
  - `POST /api/v1/projects/{id}/review/requirements` -- ?붽뎄?ы빆 異⑸룎/以묐났/紐⑦샇??寃異?
  - `schemas/api/review.py`: ReviewRequest, ReviewIssue, ReviewSuggestion, ReviewSummary, ReviewResponse ?ㅽ궎留?(Literal ????곸슜)
  - `prompts/review/requirements.py`: Review ?꾨＼?꾪듃 (異⑸룎/以묐났/紐⑦샇??寃異?+ ?섏젙 ?쒖븞, ?낅젰 ?몄뼱 ?숈씪 ?묐떟)
  - `services/review_svc.py`: `review_requirements()` -- UUID 蹂??+ DB 議고쉶 + ?꾨＼?꾪듃 援ъ꽦 + LLM ?몄텧 + JSON ?뚯떛
  - `routers/review.py`: POST `/requirements` ?붾뱶?ъ씤??
  - `main.py`??review_router ?깅줉
  - ?뚯뒪??6媛?異붽? (?뺤긽 由щ럭, 議댁옱?섏? ?딅뒗 ID 404, LLM ?먮윭 500, 鍮꾩젙??JSON 502, ?댁뒋 ?놁쓬 + ready_for_next=true, 臾댄슚 UUID 400)

### 2026-03-29 (Phase 1.5 ???紐⑤뱶 + 紐⑤뱢 ?뺤옣 + CORS ?섏젙)
- **AI ?댁떆?ㅽ듃 ???紐⑤뱶(Chat) API 援ы쁽**
  - `POST /api/v1/projects/{id}/assist/chat` ???먯쑀 ??붾? ?듯븳 ?붽뎄?ы빆 ?먯깋???뺤쓽
  - `prompts/assist/chat.py`: ???紐⑤뱶 ?꾨＼?꾪듃 (???+ 湲곗〈 ?붽뎄?ы빆 而⑦뀓?ㅽ듃 ???붽뎄?ы빆 異붿텧)
  - `services/assist_svc.py`: `chat_assist()` ??湲곗〈 ?붽뎄?ы빆 DB 議고쉶 + LLM ???+ ?붽뎄?ы빆 異붿텧
  - `schemas/api/assist.py`: ChatMessage, ChatRequest, ChatResponse, ExtractedRequirement ?ㅽ궎留?
  - `routers/assist.py`: `/chat` ?붾뱶?ъ씤??異붽?
  - role Literal["user","assistant"] 寃利앹쑝濡??꾨＼?꾪듃 ?몄젥??李⑤떒
  - ?뚯뒪??6媛?異붽? (chat, chat_with_history, chat_no_extraction, chat_llm_error, chat_invalid_json, chat_invalid_role)
- **?꾨줈?앺듃 紐⑤뱢 ?좏깮 5媛吏濡??뺤옣 (FR-PF-02-03)**
  - 湲곗〈 3媛吏(All/Req+Design/TC) ??5媛吏(All/Req Only/Req+Design/Req+TC/TC Only)
  - `schemas/api/project.py`: ?좏슚 紐⑤뱢 議고빀 寃利?(`VALID_MODULE_SETS` + `model_validator`)
  - SRS ?붽뎄?ы빆, interface.md, CLAUDE.md, UC-02 臾몄꽌 ?낅뜲?댄듃
  - ?뚯뒪??7媛?異붽? (?좏슚 5議고빀 + 臾댄슚 2議고빀)
- **CORS 踰꾧렇 ?섏젙**
  - `allow_origin_regex` 異붽?: ?대? IP(10.x, 172.x)?먯꽌 ?묒냽 ??OPTIONS 400 ?닿껐
  - `max_age` -1 ??600?쇰줈 蹂寃?(?꾨━?뚮씪?댄듃 罹먯떛 ?쒖꽦??
- ?꾩껜 42媛??뚯뒪???듦낵

### 2026-03-29 (?붽뎄?ы빆 由щ럭 諛섏쁺)
- **?붽뎄?ы빆 臾몄꽌 ???由щ럭 諛??낅뜲?댄듃**
  - FR-RQ-06 Classification: Other 遺꾨쪟 異붽?, 2-pass 泥?궧 ?꾨왂, ?좊ː??以묐났?먯? ?붽뎄?ы빆 異붽?
  - FR-RQ-07 (?좉퇋): SRS 臾몄꽌 ?앹꽦 ???쒗뵆由?湲곕컲 議고빀 湲곕뒫
  - FR-RQ-08 (?좉퇋): SRS Review ??AI Review (?꾩쟾???쇨???紐낇솗??
  - FR-RQ-09 (援?07): 踰꾩쟾愿由? FR-RQ-10 (援?08): 異붿쟻????踰덊샇 ?쒗봽??
  - FR-RQ-01: 援ъ“??紐⑤뱶 + ???紐⑤뱶 2媛吏 ?낅젰 諛⑹떇 異붽? (01-04~07 ?좉퇋)
  - FR-PF-03: 硫ㅻ쾭 沅뚰븳 Owner/Editor/Viewer濡??뺣━ (Reviewer???ν썑 ?뺤옣)
  - FR-PF-05: 臾몄꽌 ?뚯떛/誘몃━蹂닿린 ?붽뎄?ы빆 異붽?
  - interface.md: parse/classify(SSE)/srs-review API 異붽?, Other ???諛섏쁺
- **Use Case 臾몄꽌 ?좉퇋 ?묒꽦**
  - UC-01: PRD Import ??Classification ??SRS ?앹꽦 ?뚮줈??
  - UC-02: ?먯뿰??吏곸젒 ?낅젰 ??SRS ?앹꽦 ?뚮줈??
- **PLAN.md ?낅뜲?댄듃**: ???紐⑤뱶(1.5), SRS Review(2.3), Classification 2-pass(2.4) ??諛섏쁺
- **諛깆뿏??肄붾뱶 ?섏젙**: RequirementType??OTHER 異붽?, MemberRole?먯꽌 REVIEWER ?쒓굅, ?꾨＼?꾪듃/?ㅽ궎留?other 諛섏쁺

### 2026-03-28 (由ы뙥?좊쭅)
- **W-01: glossary ?꾨＼?꾪듃瑜?prompts/ ?붾젆?좊━濡?遺꾨━**
  - `src/prompts/glossary/__init__.py`: `build_glossary_generate_prompt` export
  - `src/prompts/glossary/generate.py`: ?꾨＼?꾪듃 鍮뚮뜑 ?⑥닔 (湲곗〈 glossary_svc.py?먯꽌 ?대룞)
  - `src/services/glossary_svc.py`: ?섎뱶肄붾뵫???꾨＼?꾪듃 ?쒓굅, `build_glossary_generate_prompt` import ?ъ슜
- **W-02: model-to-response 蹂???꾩튂瑜??쒕퉬???덉씠?대줈 ?듭씪**
  - `src/services/project_svc.py`: `_to_project_response()`, `_to_settings_response()` 異붽?, 紐⑤뱺 ?쒕퉬???⑥닔媛 ?묐떟 ?ㅽ궎留?吏곸젒 諛섑솚
  - `src/routers/project.py`: 蹂???⑥닔 ?쒓굅, ?쇱슦?곕? ?뉕쾶 ?좎? (?쒕퉬??寃곌낵瑜?洹몃?濡?諛섑솚)
  - 湲곗〈 ?⑦꽩怨??쇨????뺣낫: requirement_svc, glossary_svc? ?숈씪?섍쾶 ?쒕퉬???덉씠?댁뿉??蹂??
- ?꾩껜 29媛??뚯뒪???듦낵 ?뺤씤

### 2026-03-28
- **pytest conftest.py + Project/Settings ?뚯뒪???묒꽦**
  - `tests/conftest.py`: ?뚯뒪??怨듯넻 fixture (NullPool + per-request ?몄뀡 + DELETE 湲곕컲 ?곗씠???뺣━)
  - `tests/test_project.py`: Project CRUD 8媛??뚯뒪??(create, list, get, get_not_found, update, delete, get_settings, update_settings)
  - `pyproject.toml`??`[tool.pytest.ini_options]` 異붽? (asyncio_mode=auto, pythonpath)
  - 湲곗〈 ?뚯뒪??assist, glossary, requirement) ?ы븿 ?꾩껜 29媛??뚯뒪???듦낵
- **AI Assist 占쏙옙?ㅽ듃 肄붾뱶 ?묒꽦 (LLM mock)**
  - `tests/test_assist.py`: 7媛??뚯뒪??耳?댁뒪 (refine 3媛? suggest 4媛?
    - `test_refine`: ?뺤긽 ?뺤젣 ?붿껌 寃利?
    - `test_refine_llm_error`: LLM ?몄텧 ?덉쇅 ??500 ?묐떟 寃利?
    - `test_refine_invalid_json`: LLM 鍮꾩젙??JSON 諛섑솚 ??502 ?묐떟 寃利?
    - `test_suggest`: ?뺤긽 ?쒖븞 ?붿껌 寃利?
    - `test_suggest_no_requirements`: 議댁옱?섏? ?딅뒗 requirement_id ??404 寃利?
    - `test_suggest_llm_error`: suggest ??LLM ?덉쇅 500 寃利?
    - `test_suggest_invalid_json`: suggest ??鍮꾩젙??JSON 502 寃利?
  - `src/services/assist_svc.chat_completion`??monkeypatch(patch)濡?mock 泥섎━
  - `tests/conftest.py` 媛쒖꽑: NullPool + ?붿껌蹂??몄뀡 ?앹꽦?쇰줈 ?먮윭 寃⑸━
  - `src/middleware/logging_middleware.py` 媛쒖꽑: BaseHTTPMiddleware?먯꽌 ?덉쇅 諛쒖깮 ??吏곸젒 500/AppException ?묐떟 諛섑솚 (湲곗〈?먮뒗 re-raise?섏뿬 ASGI ?덈꺼源뚯? ?꾪뙆?섎뒗 踰꾧렇 ?섏젙)
- **Phase 1 MVP ?꾩껜 援ы쁽 ?꾨즺**
- DB ?명봽??援ъ텞
  - `core/database.py`: AsyncSession + async_sessionmaker + get_db dependency
  - Alembic ?ㅼ젙 諛?珥덇린 留덉씠洹몃젅?댁뀡 (projects, project_settings, requirements, requirement_versions, glossary_items)
  - `services/llm_svc.py`: Azure OpenAI 鍮꾨룞湲??대씪?댁뼵??(SRS/TC ?댁쨷 ?대씪?댁뼵??
  - DB 紐⑤뜽: Project, ProjectSettings, Requirement, RequirementVersion, GlossaryItem
- Frontend MVP ?섏씠吏 援ы쁽 (濡쒖뺄 ?뺤씤?? commit ????꾨떂)
  - ?꾨줈?앺듃 紐⑸줉/?앹꽦/?섏젙/??젣 ?섏씠吏
  - ?붽뎄?ы빆 愿由?(FR/QA/Constraints ?? CRUD, ?쇨큵 ?좏깮, 踰꾩쟾 ???
  - AI ?댁떆?ㅽ듃 (?뺤젣 鍮꾧탳 UI, ?쒖븞 ?섎씫/嫄곗젅)
  - Glossary 愿由?(CRUD, ?먮룞 ?앹꽦)
- AI Assist API 援ы쁽 ?꾨즺 (refine + suggest)
  - `prompts/assist/refine.py`: ?먯뿰??-> ?붽뎄?ы빆 ?뺤젣 ?꾨＼?꾪듃 (IEEE 29148 湲곕컲, FR/QA/Constraints蹂?媛?대뱶)
  - `prompts/assist/suggest.py`: 湲곗〈 ?붽뎄?ы빆 湲곕컲 ?꾨씫 ?붽뎄?ы빆 蹂댁셿 ?쒖븞 ?꾨＼?꾪듃
  - `prompts/assist/__init__.py`, `prompts/__init__.py`: ?⑦궎吏 珥덇린??
  - `services/assist_svc.py`: refine_requirement + suggest_requirements 鍮꾩쫰?덉뒪 濡쒖쭅 (LLM ?몄텧 + JSON ?뚯떛)
  - `routers/assist.py`: POST /assist/refine, POST /assist/suggest ?붾뱶?ъ씤??
  - `main.py`??assist_router ?깅줉
  - suggest??requirement_ids濡?DB 議고쉶 ???뺤젣???띿뒪???곗꽑 ?ъ슜?섏뿬 LLM???꾨떖
- Glossary CRUD API 援ы쁽 ?꾨즺
  - `services/glossary_svc.py`: ?⑹뼱 CRUD + LLM 湲곕컲 ?먮룞 ?앹꽦 鍮꾩쫰?덉뒪 濡쒖쭅
  - `routers/glossary.py`: 5媛??붾뱶?ъ씤??(紐⑸줉/異붽?/?섏젙/??젣 + ?먮룞 ?앹꽦)
  - generate ?붾뱶?ъ씤?? ?꾨줈?앺듃 ?붽뎄?ы빆?먯꽌 ?꾨찓???⑹뼱 異붿텧 (DB ????놁씠 珥덉븞 諛섑솚)
  - `main.py`??glossary_router ?깅줉
- Requirement CRUD API 援ы쁽 ?꾨즺
  - `services/requirement_svc.py`: ?붽뎄?ы빆 CRUD + ?쇨큵 ?좏깮/?댁젣 + 踰꾩쟾 ???鍮꾩쫰?덉뒪 濡쒖쭅
  - `routers/requirement.py`: 6媛??붾뱶?ъ씤??(紐⑸줉/?앹꽦/?섏젙/??젣 + ?쇨큵?좏깮 + 踰꾩쟾???
  - `main.py`??requirement_router ?깅줉
  - 湲곗〈 ?ㅽ궎留?`schemas/api/requirement.py`) 諛?紐⑤뜽(`models/requirement.py`) ?쒖슜
- Project CRUD API 援ы쁽 ?꾨즺
  - `services/project_svc.py`: ?꾨줈?앺듃 諛??ㅼ젙 CRUD 鍮꾩쫰?덉뒪 濡쒖쭅 (async ?⑥닔, AsyncSession 二쇱엯)
  - `routers/project.py`: 7媛??붾뱶?ъ씤??(紐⑸줉/?앹꽦/議고쉶/?섏젙/??젣 + ?ㅼ젙 議고쉶/?섏젙)
  - `main.py`??project_router ?깅줉
  - `models/project.py`: ProjectSettings.project_id??ForeignKey ?꾨씫 ?섏젙
  - 紐⑤뱢 ?좏깮? ProjectCreate.modules ?꾨뱶濡?泥섎━ (ProjectModule enum)
  - member_count??MVP?먯꽌 0 怨좎젙 (Phase 6?먯꽌 援ы쁽)
- PLAN.md Phase 1.2 ??ぉ 4媛??꾨즺 泥댄겕

### 2026-03-27
- LangChain Deep Agents 議곗궗 ?꾨즺 (`references/2026-03-27_langchain-deepagent.md`)
  - Deep Agents 媛쒖슂: LangChain/LangGraph 湲곕컲 ?먯씠?꾪듃 ?섎꽕??(怨꾪쉷, ?뚯씪?쒖뒪?? ?쒕툕?먯씠?꾪듃)
  - ?꾪궎?띿쿂: 誘몃뱾?⑥뼱 ?ㅽ깮, ?뚮윭洹?媛??諛깆뿏?? 而⑦뀓?ㅽ듃 ?먮룞 愿由?
  - v0.4遺??OpenAI Responses API 湲곕낯 吏?? ?뚮뱶諛뺤뒪 ?듯빀
  - Azure OpenAI ?ъ슜 媛??(init_chat_model ?먮뒗 AzureChatOpenAI)
  - AISE 2.0 ?곸슜 媛?μ꽦: SRS ?앹꽦??Deep Agents ?쒖슜 沅뚯옣 (?듭뀡 B: ?좏깮??梨꾪깮)
- Azure OpenAI Responses API 議곗궗 ?꾨즺 (`references/2026-03-27_azure-openai-responses-api.md`)
  - Responses API vs Chat Completions API 李⑥씠???뺣━
  - 硫?고꽩 ???泥섎━ 諛⑹떇 (previous_response_id, Conversations API, ?섎룞 愿由?
  - ?뚯씪 ?낅젰 吏??(PDF, ?대?吏, Base64/URL/File ID)
  - Python SDK ?ъ슜踰?(Azure OpenAI ?ы븿)
  - Azure OpenAI 吏??紐⑤뜽/由ъ쟾 ?꾪솴
  - GPT-5.2 紐⑤뜽 ?뺣낫 (400K 而⑦뀓?ㅽ듃, $1.75/1M ?낅젰 ?좏겙)
  - AISE 2.0 ?꾨줈?앺듃 ?곸슜 ?쒖궗???꾩텧

### 2026-03-25
- CLAUDE.md ?묒꽦 (MVP 踰붿쐞, ?곗씠??紐⑤뜽, ?붾젆?좊━ 援ъ“ ?뺤쓽)
- PLAN.md / PROGRESS.md ?앹꽦
- Backend 蹂댁씪?ы뵆?덉씠???뺤씤 ?꾨즺 (Python 3.14, FastAPI)

### 2026-04-17 (Frontend streaming hotfix)
- Fixed root cause of stream rendering artifacts in agent chat.
- `MessageResponse` now always uses `Streamdown` during streaming with `mode="streaming"` and `parseIncompleteMarkdown` enabled, so incomplete markdown is rendered progressively.
- Removed block-level animation (`animated=false`) while keeping stream state (`isAnimating`) to avoid visual reflow that looked like parallel/reverse rendering.
- `useChatStream` now buffers incoming token chunks per session and flushes them in requestAnimationFrame order, then flushes remaining buffer on done/error/stop/unmount for deterministic append order.
- Verified with `npm run build` in `frontend` (success).
- Improved code block scrollbar UX: horizontal scrollbar in markdown code blocks is now hidden by default and shown only on hover/focus (`markdown-body` + `source-markdown` pre blocks).
- Refined code block scrollbar UX to fixed-height style: scrollbar track space stays stable while thumb appears with smooth color transition on hover/focus.
- Added markdown theme presets in `markdown.css` (docs/github/dense), with richer heading/link/blockquote/inline-code/codeblock/table styles based on docs + GitHub references.
- Applied `markdown-theme-docs` as default class in chat `MessageResponse` and `SourceViewerPanel` markdown rendering roots.
- Verified with `npm run build` in `frontend`.
- Implemented persisted markdown theme preferences via Zustand (`aise-ui-preferences`) and wired them into chat/source markdown renderers.
- Added settings UI for selecting markdown preset (`Docs`, `GitHub`, `Dense`) in Settings > General.
- Refined code block styling so inner code rendering area background is transparent while shell/header remains visually structured.
- Verified with `npm run build` in `frontend`.
- Adjusted markdown preset card layout in settings (`px-4` alignment, selected state uses inset ring) to prevent side clipping.
- Updated code-block styles: removed innermost border and aligned language header with action buttons on a single baseline row.
- Verified with `npm run build` in `frontend`.
- Added bottom separator line for code block header and aligned language/actions to a shared 2rem header row.
- Removed outer code-block shell shadow (`box-shadow: none`).
- Updated Markdown preset cards to match theme card visual system (rounded-lg + ring-2 selected state, no mismatched border thickness).
- Verified with `npm run build` in `frontend`.

- Added chat font-size setting in Settings > General and wired persisted preference to chat message rendering (user, assistant, and shimmer loading text).
- Updated markdown code-block header styling to render a full-width header separator line and align language/actions vertically with larger Y padding.
- Verified with frontend production build: npm run build (success).

- Replaced assistant pending-state spinner with Wave Dots in chat renderer for softer loading motion.
- Unified markdown shell borders for code blocks, tables, and mermaid blocks using the same border color/radius tokens.
- Implemented chat font-size proportional scaling for assistant markdown (base text and heading hierarchy scale together via CSS variable multiplier).
- Verified with frontend production build: npm run build (success).

- Removed markdown table wrapper-level border/box-shadow (table-wrapper + table-block/container/shell selectors) to avoid double-outline appearance.
- Verified with frontend production build: npm run build (success).

- Disabled Streamdown built-in streaming caret (isAnimating=false) and rendered custom Wave Dots at assistant message right edge (text-fg-muted).
- Reordered style imports so custom markdown CSS loads after Streamdown defaults; strengthened table wrapper shell reset (border/outline/shadow/padding: none) to remove double border.
- Fixed chat viewport behavior regression by skipping bottom auto-scroll during current turn (latest user+assistant pair), restoring user-question top anchoring.
- Verified with frontend production build: npm run build (success).




- Adjusted markdown code-block header layout so language label and action buttons share one horizontal row; overrode Streamdown sticky/negative-margin action wrapper behavior with explicit top-row positioning.
- Verified with frontend production build: npm run build (success).

### 2026-04-18 (Mobile streaming UX hotfix)
- Fixed first-turn mobile streaming visibility during new-session creation by introducing an optimistic `pendingSessionId` in `useChatStream`.
- Updated chat state selectors (`messages`, `isStreaming`) to use `activeSessionId = sessionId ?? pendingSessionId`, so tokens continue rendering while route transition is in progress.
- Cleared `isCreatingSession` immediately after session creation succeeds, preventing loading spinner lock on slower mobile navigation.
- Added loading-state fallback release: when cached/streamed messages arrive while `isLoadingMessages` is true, loading mode exits immediately.
- Updated `ChatArea` loading condition to show full-screen spinner only when there are no messages and no active stream.
- Reworked token append pipeline from single `requestAnimationFrame` flush to time-sliced drain with small append chunks (`scheduleTokenDrain` + `requestFinishAfterDrain`), so mobile/coalesced SSE payloads still render progressively.
- Updated stream completion semantics to finish only after buffered text drains, preventing end-of-stream jumps.
- Fixed desktop scroll-follow regression by limiting "current turn top anchoring" behavior to mobile only in `useChatScroll`.
- Tuned mobile scroll behavior to conditionally follow streaming when the user is near bottom (`shouldPinCurrentTurn = isMobile && hasCurrentTurn && !isAtBottom`).
- Verified with `npm run build` in `frontend` (success).

### 2026-04-18 (백엔드 전수 분석 + 리팩토링 리뷰 문서화)
- `backend/src` 전체 파일/함수 인벤토리 재분석 완료 (엔트리/모델/라우터/서비스/프롬프트/유틸).
- 핵심 서비스(`agent_svc`, `record_svc`, `requirement_svc`, `rag_svc`, `llm_svc`, `srs_svc`) 라인 단위 리스크 점검.
- 테스트 재실행: `cd backend && uv run pytest tests/` -> `93 passed, 3 skipped` 확인.
- `REFECTORING.md`를 최신 분석 기준으로 확장 업데이트:
  - 백엔드 구조/기능 맵
  - P0/P1 리팩토링 이슈(근거 라인 포함)
  - Agent Harness/Structured Output/Tool Gateway 설계안
  - 다음 세션 TODO 순서/실행 커맨드/시작 프롬프트
- 외부 리서치 근거 링크(공식 문서 위주) 최신화.
