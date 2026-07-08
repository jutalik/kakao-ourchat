# KakaoTalk export formats (what `parse_export.py` handles)

All input is produced by the **official in-app** `대화 내용 내보내기` / *Export Chat*.
No decryption. `parse_export.py` auto-detects CSV vs TXT and normalizes everything
into `corpus.jsonl` (see [AGENTS.md](../AGENTS.md) → data contract).

## 1. macOS / iOS — `.csv`  (verified, most robust)

UTF-8 **with BOM**, standard CSV:

```
Date,User,Message
2026-02-06 00:00:58,"카드이야기","클로드를 끌고 오셔야되는데"
2026-02-06 00:01:20,"로앤하이","아 끌고 오는 개념이 아니예요"
```

- `Date` = `YYYY-MM-DD HH:MM:SS` (24h). `User`, `Message` quoted; embedded newlines
  and commas handled by the CSV reader (multi-line messages just work).
- No reactions, no userId (by design — the export doesn't include them).

## 2. PC / Windows — `.txt`

```
홍길동님과 카카오톡 대화
저장한 날짜 : 2024-01-01 15:20:41

--------------- 2024년 1월 1일 월요일 ---------------
[홍길동] [오후 3:20] 안녕하세요
[김철수] [오전 11:05] 여러 줄
이어지는 메시지
```

- Message head: `^\[(sender)\] \[(오전|오후|AM|PM) h:mm\] body$`
- Day separator: `--------------- YYYY년 M월 D일 요일 ---------------` sets the running date.
- A line that doesn't match the head (or the separator) is a **continuation** of the
  previous message body.

## 3. mac / Android / iOS — `.txt` (comma/inline)

```
우리방님과 카카오톡 대화
저장한 날짜 : 2024-01-01 15:20:41

2024년 1월 1일 오후 3:20, 홍길동 : 안녕하세요
2024. 1. 2. 오전 9:00, 홍길동 : (dot-date variant)
2024년 1월 1일 오후 3:22, 김철수님이 들어왔습니다.
```

- Head: `^YYYY년 M월 D일 (오전|오후|AM|PM) h:mm, sender : body$` (and the `YYYY. M. D.` dot
  variant; English `AM`/`PM` locale exports parse too).
- Lines with a leading date-time but **no `" : "`** (join/leave, day markers) are treated
  as system **boundaries**, not message bodies (prevents swallowing the next message).
- Multi-line continuation same as PC.
- Sender/body split is on the **first** `" : "`. A nickname that itself contains `" : "`
  can't be split unambiguously in `.txt` — **prefer the `.csv` export** (unambiguous
  columns) whenever it's available; `.txt` sender-splitting is best-effort.

## Non-text handling (all formats)

The export renders media/system as fixed strings, mapped to message types:

| body | type |
|------|------|
| `사진`, `사진 N장` | photo |
| `동영상` | video · `이모티콘` sticker · `음성메시지` voice · `파일: …` file |
| `보이스룸`, `라이브톡` | call (kept as participant activity, **not** system) |
| `(삭제된 메시지입니다.)` | deleted (system) |
| `…님이 들어왔습니다./나갔습니다.` etc. | system |
| `샵검색: …`, `위치: …`, `연락처: …` | special |

## Adding a new platform (Discord/WhatsApp/Slack)

Write a new reader that yields `(ts, author, message)` and emits the same
`corpus.jsonl` contract — nothing downstream changes.
