<div align="center">

# OurChat · `kakao-ourchat`

**우리 단톡방을 지식그래프로 — 관계·인물·화제, 그리고 재미난 이벤트까지**

카카오톡 단톡방 하나를 인터랙티브 **지식그래프 대시보드**로 바꿔줍니다:
누가 누구와 얽혀 있는지(관계도), 활동·페르소나 랭킹, 인물별 프로필,
시간에 따른 화제(토픽), 그리고 일·주·월 대화 흐름 요약까지.

<br/>

[![Live demo](https://img.shields.io/badge/▶_라이브_데모-syde.moche.ai-7C6BF5.svg)](https://syde.moche.ai/)
![License: MIT](https://img.shields.io/badge/License-MIT-7C6BF5.svg)
![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB.svg)
![Built with Svelte](https://img.shields.io/badge/UI-Svelte-FF3E00.svg)
![Local-first](https://img.shields.io/badge/privacy-local--first-38C6C0.svg)

*로컬 우선 · 오프라인으로 동작 · LLM은 선택(내 키/로컬 모델) · 복호화 안 함*

**한국어** · **[English](README.en.md)**

<br/>

<a href="https://syde.moche.ai/"><img src="docs/img/dashboard-graph.png" alt="OurChat 관계도 대시보드 — 실제 약 8.3만 메시지 커뮤니티" width="880"/></a>

<sub>▶ <b><a href="https://syde.moche.ai/">라이브 데모</a></b> — 실제 약 8.3만(83,099)개 메시지 커뮤니티를 지식그래프로 그린 모습.</sub>

</div>

> **프라이버시 우선 · 합법적 설계.** OurChat은 누구나 만들 수 있는 **공식 카카오톡
> 내보내기 파일**(`대화 내용 내보내기` → `.csv`/`.txt`)만 읽습니다. 앱 DB를 복호화하거나
> 덤프하거나 역공학하지 **않습니다.** 기본값은 전부 **내 컴퓨터 안에서** 돌아갑니다.
> *카카오와 무관하며 공식 프로젝트가 아닙니다.*

---

## 빠른 시작

```bash
git clone https://github.com/jutalik/kakao-ourchat
cd kakao-ourchat
pip install -r requirements.txt          # 오프라인 모드는 numpy + scikit-learn 이게 전부

# 번들된 합성 샘플로 바로 체험 — 실데이터 0, 서버 0
python -m ourchat demo

# ...내 방으로 하려면 먼저 내보내기 (docs/EXPORTING.md 참고):
#   카카오톡 → 채팅방 설정 → 대화 내용 관리 → 대화 내용 저장 → 텍스트 파일로 저장
python -m ourchat analyze ~/Downloads/KakaoTalkChats.csv --room "우리 단톡방"

# 나중에 또 내보내서 최신 유지 (병합·중복제거, 마지막부터 이어받음):
python -m ourchat analyze ~/Downloads/KakaoTalkChats_7월.csv --room "우리 단톡방" --append

python -m ourchat serve                  # → http://localhost:4173  (Node.js 필요 — 첫 실행 시 대시보드 빌드)
```

**호스팅:** 로컬에서, 집 서버/VPS에서, 또는 인터넷에 공개(Cloudflare Tunnel, 리버스
프록시 + 비밀번호)까지 — [`docs/HOSTING.md`](docs/HOSTING.md) 참고.

## 두 가지 모드 (둘 다 무료·오픈)

| 모드 | 방법 | 얻는 것 |
|------|------|---------|
| **오프라인 (기본)** | `pip install`만, LLM·서버 불필요 | 행동 기반 범용 페르소나, 관계도, 랭킹, 토픽(TF-IDF), 결정적 요약 |
| **내 AI 붙이기** | `KAKAO_LLM_*` 설정 (OpenAI / Anthropic / Ollama / 로컬 모델) | **방별 맞춤** 페르소나·기준, AI 토픽명, 서사, 인물 프로필 — 정적 JSON으로 미리 생성 |

**LLM 없이도 완전히 쓸 만합니다.** LLM(내 키든 로컬 모델이든 — 선택)은 결과를 더 풍부하게
하고, 고정된 템플릿이 아니라 **그 방에 맞게** 분석을 적응시킵니다: 가족방·게임 클랜·스터디·
개발자 커뮤니티가 각자 다른 페르소나(원형)를 갖게 됩니다. *(선택: `OURCHAT_EMBED` 임베딩
엔드포인트로 토픽 클러스터 품질↑ — 이것도 내/로컬, 별도 서비스 불필요.)*

```bash
# 예: 내 OpenAI 키
export KAKAO_LLM_PROVIDER=openai KAKAO_LLM_MODEL=gpt-4o-mini KAKAO_LLM_API_KEY=sk-...
# 또는 Ollama로 완전 로컬
export KAKAO_LLM_PROVIDER=openai KAKAO_LLM_BASE_URL=http://localhost:11434/v1 KAKAO_LLM_MODEL=qwen2.5
python -m ourchat analyze chats.csv --room "우리방"
```

## 무엇을 계산하나

- **관계도** — 누가 누구와 대화하나(시간 인접 기반), 캔버스 그래프, 인물 중심(ego) 보기.
- **랭킹** — 발언량·관계 폭·페르소나별 순위.
- **페르소나** — 방에 맞게 적응하는 원형(수다왕/질문러/유머러/… 또는 LLM 맞춤).
- **시간별 토픽** — 주간 열기(hotness)와 그 화제를 이끈 사람.
- **일 / 주 / 월** 대화 흐름 요약.
- **인물별 프로필** — 데이터 근거의 캐릭터 분석(LLM 모드).

## 더 좋은 결과를 위한 팁 (에이전트가 대신 돌려도 이거 참고)

설정 없이도 돌아가지만, 넣는 만큼 품질이 올라갑니다. 영향 큰 순서:

1. **임베딩을 켜면 토픽 클러스터가 훨씬 좋아집니다.** 기본은 오프라인 TF-IDF(간편, 세팅 0).
   임베딩 모델은 메시지를 *의미*로 묶어줘서 토픽과 토픽 차트가 확 깔끔해집니다.
   ```bash
   # OpenAI 호환 (OpenAI / Ollama / vLLM / LM Studio):
   export OURCHAT_EMBED=api OURCHAT_EMBED_MODEL=text-embedding-3-large \
          OURCHAT_EMBED_URL=https://api.openai.com/v1/embeddings OURCHAT_EMBED_KEY=sk-...
   # 완전 로컬, 키 불필요:
   export OURCHAT_EMBED=api OURCHAT_EMBED_MODEL=nomic-embed-text \
          OURCHAT_EMBED_URL=http://localhost:11434/v1/embeddings
   ```
   **차원이 높을수록 차트가 잘 나옵니다.** 큰 모델(예: `text-embedding-3-large` 3072차원,
   또는 로컬 4096차원)이 작은 384/768차원보다 토픽을 더 또렷하게 분리해서 클러스터가
   촘촘하고 주간 토픽 곡선도 선명합니다. 토픽이 뭉개지면 더 큰 임베딩 모델을 쓰거나 `--k`를 올리세요.

2. **성능 좋은 LLM을 붙이면 방별 맞춤 분석**이 나옵니다. `KAKAO_LLM_*`를 설정하면 방마다 자기
   페르소나를 만들고, 토픽에 이름을 붙이고, 서사와 인물 프로필까지 씁니다. 작고 약한 로컬
   모델은 범용 페르소나로 **자연스럽게 폴백**(에러 아님)합니다 — `gpt-4o-mini`, `claude-haiku-4-5`
   급 이상이면 방별 맞춤 결과가 온전히 나옵니다.

3. **데이터가 많을수록 풍부합니다.** 큰 내보내기 → 촘촘한 관계도, 안정적인 토픽. 나중에 또
   내보내 `--append` 하면 데이터가 계속 쌓입니다(카카오톡은 오래된 메시지를 지우므로 주기적
   내보내기가 곧 히스토리 보존).

4. **조절 노브:** `--k <n>` 토픽 개수(기본 20, 큰 방은 올리기), `OURCHAT_EMBED`(offline|api),
   `KAKAO_LLM_PROVIDER`(none|openai|anthropic).

## 어떻게 동작하나

```
export.csv/.txt ─▶ parse_export ─▶ characterize (방 기준 룰) ─▶ analyze ─▶ topics
                                                                    ├─▶ summarize
                                                                    └─▶ daily ─▶ 대시보드
                    (LLM은 선택) ────────────────────────────────▶ narrate
```

OSS 대시보드는 **백엔드 없는 정적 사이트**입니다 — 모든 AI 결과는 분석 시점에 JSON으로 미리
구워집니다(실행 중 서버 없음). 지원 포맷: **macOS/iOS `.csv`**, 그리고 **PC/macOS/Android/iOS**
의 `.txt` ([`docs/FORMATS.md`](docs/FORMATS.md)).

## 내보내는 법 (직접 해야 하는 한 번의 과정)

카카오톡에서 **채팅방 설정 → 대화 내용 관리 → 대화 내용 저장 → 텍스트 파일로 저장**을 누르면
됩니다(플랫폼별 상세는 [`docs/EXPORTING.md`](docs/EXPORTING.md)). OurChat은 이 파일만 읽고,
앱 DB는 절대 건드리지 않습니다.

<img src="docs/img/export-mac.png" alt="카카오톡 대화 내용 저장 → 텍스트 파일로 저장" width="460"/>

## 프라이버시 & 동의

단톡방에는 **다른 사람들의 메시지**가 들어 있습니다. [`PRIVACY.md`](PRIVACY.md)를 꼭 읽어주세요:
로컬로 두고, 대시보드를 공유하기 전엔 동의를 받고, 민감한 방은 오프라인 모드를 쓰세요. 내가 직접
LLM을 지정하지 않는 한, 아무것도 내 컴퓨터를 벗어나지 않습니다.

## 자주 묻는 질문

**카톡을 복호화하나요?** 아니요. 앱에서 내보낸 파일만 읽습니다. DB 접근·키 복구·역공학 없음 — 그게 핵심입니다.

**API 키가 필요한가요?** 아니요. 기본은 완전 오프라인(`numpy` + `scikit-learn`). LLM은 선택이고 로컬 모델(Ollama, vLLM)도 됩니다.

**카카오톡만 되나요?** 지금은 네. 다만 파이프라인이 단순한 [코퍼스 계약](AGENTS.md) 위에서 돌기 때문에 Discord/WhatsApp/Slack 임포터를 붙이는 건 작은 작업입니다.

**정확한가요?** 실제 8.3만 메시지 방으로 검증했고, ground-truth 실행과 결과가 일치합니다. 페르소나는 고정 템플릿이 아니라 *그 방* 기준의 상대평가입니다.

## 기여

PR 환영합니다 — [`CONTRIBUTING.md`](CONTRIBUTING.md)와 [`AGENTS.md`](AGENTS.md)(사람과 AI 에이전트 공용 정본 가이드)를 참고하세요.

## 라이선스

[MIT](LICENSE). 카카오와 무관합니다. "카카오톡/KakaoTalk"은 해당 소유자의 상표이며, 이 프로젝트는 사용자가 직접 내보낸 파일만 처리합니다.

<sub>Topics: kakaotalk · 카카오톡 분석 · chat analysis · group-chat analytics · knowledge graph ·
social network analysis · conversation analysis · NLP · data visualization · privacy-first · svelte</sub>
