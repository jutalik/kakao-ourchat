# Exporting your KakaoTalk chat (do this yourself, once)

OurChat only reads a file **you** export from KakaoTalk — it never touches the app's
database. Open the chat room, export it, then point OurChat at the file. (UI wording
varies a little by version; look for **대화 내용 내보내기 / Export Chat**.)

## macOS  → `.csv` / `.txt`  (best; richest & most reliable)
1. Open the chat room → **채팅방 설정** (top-right gear/menu).
2. **대화 내용 관리** → under **대화 내용 저장**, click **텍스트 파일로 저장**.
3. Choose where to save → you get a file (recent Mac versions save `Date,User,Message`
   as `.csv`; either `.csv` or `.txt` is fine — OurChat auto-detects).

<img src="img/export-mac.png" alt="채팅방 설정 → 대화 내용 관리 → 대화 내용 저장 → 텍스트 파일로 저장" width="460"/>

## Windows / PC  → `.txt`
1. Open the chat room → top-right **menu (≡)** → **대화내용** → **대화 내용 내보내기**.
2. Choose **텍스트만** (text only) unless you want media too → saves a `.txt`.

## iPhone / iOS  → `.txt`
1. Open the chat → top-right **≡** → **설정(gear)** → **대화 내용 관리** → **대화 내보내기**.
2. Save the `.txt` to Files / send it to yourself (email, AirDrop), then move it to your computer.

## Android  → `.txt`
1. Open the chat → **≡** menu → **대화 내용** (or 설정) → **대화 내용 내보내기**.
2. Save/email the `.txt`, then move it to your computer.

> **What's in it:** every message currently synced to that device (text + placeholders
> like `사진`, `이모티콘`). **Not** included: reactions(공감), read counts, media files
> themselves. That's expected — OurChat analyzes structure, timing, and text.

## Run it

```bash
python -m ourchat analyze /path/to/export.csv --room "우리 단톡방"
python -m ourchat serve      # → http://localhost:4173
```

## Keeping it up to date (incremental)

KakaoTalk exports the **whole visible history each time**, and old messages eventually
roll off the device. So to keep your dashboard current — **and to preserve history a
newer export may have dropped** — just export again later and add it with `--append`:

```bash
# a month later, export again, then:
python -m ourchat analyze /path/to/export_july.csv --room "우리 단톡방" --append
```

OurChat **merges** the new file with what it already has, **de-duplicates**, and
continues from the last point — so you can drop in exports over time and the room only
grows. (Same `--room`/slug = same accumulating dataset.)
