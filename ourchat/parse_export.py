#!/usr/bin/env python3
"""
parse_export.py — turn an OFFICIAL KakaoTalk chat export into the analysis corpus
(no decryption; works off 대화 내용 내보내기). Emits the same files extract-from-DB did,
so analyze.py / topics.py / summarize.py / daily.py run unchanged.

Handles every official export shape:
  • macOS/iOS  .csv   : Date,User,Message  (UTF-8 BOM)                      [verified]
  • PC/Windows .txt   : "[홍길동] [오후 3:20] msg"  + dashed date separators
  • mac/Android/iOS .txt : "2024년 1월 1일 오후 3:20, 홍길동 : msg" (and "2024. 1. 1. …")

Outputs into --outdir: corpus.jsonl, participants.json, meta.json, reactions.json({} — no reactions in exports)
"""
import argparse, json, os, sys, csv, re, datetime, hashlib, collections

MEDIA = {'사진': (2, 'photo'), '동영상': (3, 'video'), '이모티콘': (5, 'sticker'),
         '음성메시지': (4, 'voice'), '보이스룸': (7, 'voiceroom'), '라이브톡': (7, 'livetalk')}
SYS_SUFFIX = ('님이 들어왔습니다.', '님이 나갔습니다.', '님을 내보냈습니다.', '님이 들어왔습니다',
              '님이 나갔습니다', '님을 내보냈습니다', '채팅방을 개설했습니다.', '방장으로 지정되었습니다.')

def classify(msg):
    m = msg.strip()
    if m in MEDIA:
        t, lbl = MEDIA[m]; return t, lbl, (t in (2, 3, 4, 6)), (t == 0)
    if re.match(r'^사진 \d+장$', m): return 2, 'photo', True, False
    if m.startswith('파일:') or m.startswith('파일 :'): return 6, 'file', True, False
    if m in ('삭제된 메시지입니다.', '(삭제된 메시지입니다.)', '삭제된 메시지입니다'): return 0, 'deleted', False, True
    if any(m.endswith(s) for s in SYS_SUFFIX): return 0, 'system', False, True
    if m.startswith(('샵검색:', '지도:', '위치:', '연락처:', '일정:')): return 8, 'special', False, False
    return 1, 'text', False, False

def aid_of(name):
    return int(hashlib.sha1(name.encode('utf-8')).hexdigest()[:12], 16)

def to24(ampm, h):
    h = int(h)
    if ampm in ('오전', 'AM'):
        return 0 if h == 12 else h
    return 12 if h == 12 else h + 12   # 오후/PM

def parse_iso(s):
    for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try: return int(datetime.datetime.strptime(s.strip(), f).timestamp())
        except ValueError: pass
    return None

# ---- readers → yield (ts:int, author:str, message:str) ----
def read_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as fh:
        rd = csv.reader(fh); next(rd, None)
        for row in rd:
            if len(row) < 3: continue
            ts = parse_iso(row[0])
            if ts is not None and row[1]:
                yield ts, row[1], row[2]

HEAD_PC = re.compile(r'^\[(?P<sender>.+?)\] \[(?P<ampm>오전|오후|AM|PM) (?P<h>\d{1,2}):(?P<m>\d{2})\] (?P<body>.*)$')
DATESEP = re.compile(r'^-{5,}\s*(?P<y>\d{4})년\s*(?P<mo>\d{1,2})월\s*(?P<d>\d{1,2})일.*-{5,}$')
HEAD_KR = re.compile(r'^(?P<y>\d{4})년 (?P<mo>\d{1,2})월 (?P<d>\d{1,2})일 (?P<ampm>오전|오후|AM|PM) (?P<h>\d{1,2}):(?P<mi>\d{2}), (?P<sender>.+?) : (?P<body>.*)$')
HEAD_DOT = re.compile(r'^(?P<y>\d{4})\. (?P<mo>\d{1,2})\. (?P<d>\d{1,2})\. (?P<ampm>오전|오후|AM|PM) (?P<h>\d{1,2}):(?P<mi>\d{2}), (?P<sender>.+?) : (?P<body>.*)$')
# mobile/mac system+day lines: carry a leading datetime but NO ' : ' (join/leave, day
# markers). Matched only after HEAD_* fail — they are message BOUNDARIES, not bodies.
# The trailing comma is required so a bare timestamp PASTED inside a body isn't mistaken
# for a boundary (real join/leave lines are "…h:mm, 홍길동님이 …").
SYS_KR = re.compile(r'^\d{4}[년.] ?\d{1,2}[월.] ?\d{1,2}[일.]?\.? (오전|오후|AM|PM) \d{1,2}:\d{2},')

def read_txt(path, stats=None):
    cur = None            # [ts, sender, [body lines]]
    cur_date = None       # (y, mo, d) for PC dashed-separator style
    for raw in open(path, encoding='utf-8'):
        line = raw.rstrip('\n')
        m = DATESEP.match(line)
        if m:
            if cur: yield (cur[0], cur[1], "\n".join(cur[2]))
            cur = None; cur_date = (int(m['y']), int(m['mo']), int(m['d'])); continue
        m = HEAD_PC.match(line)
        if m:
            if cur: yield (cur[0], cur[1], "\n".join(cur[2]))
            cur = None
            if cur_date:
                y, mo, d = cur_date
                try:
                    ts = int(datetime.datetime(y, mo, d, to24(m['ampm'], m['h']), int(m['m'])).timestamp())
                    cur = [ts, m['sender'], [m['body']]]
                except ValueError:
                    if stats is not None: stats['skipped'] = stats.get('skipped', 0) + 1
            elif stats is not None:      # PC message before any date separator → can't date it
                stats['skipped'] = stats.get('skipped', 0) + 1
            continue
        m = HEAD_KR.match(line) or HEAD_DOT.match(line)
        if m:
            if cur: yield (cur[0], cur[1], "\n".join(cur[2]))
            try:
                ts = int(datetime.datetime(int(m['y']), int(m['mo']), int(m['d']),
                                           to24(m['ampm'], m['h']), int(m['mi'])).timestamp())
                cur = [ts, m['sender'], [m['body']]]
            except ValueError:
                cur = None
            continue
        if SYS_KR.match(line):        # join/leave/day-marker: a boundary, not a body
            if cur: yield (cur[0], cur[1], "\n".join(cur[2]))
            cur = None; continue
        if cur:
            # a bare join/leave/kick notice (no datetime prefix, PC style) would be glued
            # onto the previous message → treat it as a boundary, not a body line.
            if line.strip() and any(line.strip().endswith(s) for s in SYS_SUFFIX):
                yield (cur[0], cur[1], "\n".join(cur[2])); cur = None; continue
            cur[2].append(line)       # continuation line (multi-line message body)
    if cur: yield (cur[0], cur[1], "\n".join(cur[2]))

def detect(path):
    if path.lower().endswith('.csv'): return 'csv'
    with open(path, encoding='utf-8-sig') as fh:
        head = fh.read(4000)
    return 'csv' if head.lstrip().lower().startswith('date,user,message') else 'txt'

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', required=True)
    ap.add_argument('--outdir', required=True)
    ap.add_argument('--room', default='')
    a = ap.parse_args()
    os.makedirs(a.outdir, exist_ok=True)
    fmt = detect(a.input)
    stats = {}
    rows = read_csv(a.input) if fmt == 'csv' else read_txt(a.input, stats)

    part = collections.defaultdict(lambda: {'name': None, 'msgs': 0, 'text_msgs': 0,
        'media_msgs': 0, 'first_ts': None, 'last_ts': None, 'days': set(), 'react_in': 0})
    months = collections.Counter(); n = 0
    corpus = open(os.path.join(a.outdir, 'corpus.jsonl'), 'w', encoding='utf-8')
    for ts, user, msg in rows:
        if not user or not msg.strip(): continue   # skip empty-body lines (e.g. "홍길동 : ")
        typ, tlabel, media, system = classify(msg)
        aid = aid_of(user); text = msg if typ == 1 else ''
        date = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d')
        corpus.write(json.dumps({'logId': n + 1, 'ts': ts, 'date': date, 'aid': aid, 'author': user,
            'type': typ, 'tlabel': tlabel, 'text': text, 'media': media, 'system': system}, ensure_ascii=False) + '\n')
        n += 1
        months[datetime.datetime.fromtimestamp(ts).strftime('%Y-%m')] += 1
        p = part[aid]; p['name'] = user; p['msgs'] += 1
        if typ == 1: p['text_msgs'] += 1
        if media: p['media_msgs'] += 1
        p['first_ts'] = ts if p['first_ts'] is None else min(p['first_ts'], ts)
        p['last_ts'] = ts if p['last_ts'] is None else max(p['last_ts'], ts)
        p['days'].add(date)
    corpus.close()
    participants = {str(aid): {'name': p['name'], 'msgs': p['msgs'], 'text_msgs': p['text_msgs'],
        'media_msgs': p['media_msgs'], 'first_ts': p['first_ts'], 'last_ts': p['last_ts'],
        'active_days': len(p['days']), 'react_in': 0} for aid, p in part.items()}
    json.dump(participants, open(os.path.join(a.outdir, 'participants.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    json.dump({}, open(os.path.join(a.outdir, 'reactions.json'), 'w'))
    fts = [p['first_ts'] for p in participants.values() if p['first_ts']]
    lts = [p['last_ts'] for p in participants.values() if p['last_ts']]
    span = [datetime.datetime.fromtimestamp(min(fts)).strftime('%Y-%m-%d'),
            datetime.datetime.fromtimestamp(max(lts)).strftime('%Y-%m-%d')] if fts else [None, None]
    meta = {'room': a.room or 'KakaoTalk 내보내기', 'chatId': 0, 'messages': n, 'participants': len(participants),
            'date_span': span, 'months': dict(sorted(months.items())), 'source': f'export-{fmt}', 'has_reactions': False}
    json.dump(meta, open(os.path.join(a.outdir, 'meta.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    skipped = stats.get('skipped', 0)
    if skipped:
        sys.stderr.write(f"[parse_export] warning: skipped {skipped} .txt line(s) with no resolvable date "
                         f"(messages before the first date separator?) — not silently lost, counted here.\n")
    print(json.dumps({'ok': True, 'format': fmt, 'messages': n, 'participants': len(participants),
                      'span': span, 'skipped': skipped}, ensure_ascii=False))

if __name__ == '__main__':
    main()
