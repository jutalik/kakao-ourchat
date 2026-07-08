<script>
  import { onMount } from 'svelte'
  import { Network, Users, Hash, LayoutDashboard, MessageSquare, Heart,
           TrendingUp, Trophy, Swords, Sparkles, Search, CalendarDays } from 'lucide-svelte'
  import ForceGraph from './lib/ForceGraph.svelte'
  import Spark from './lib/Spark.svelte'
  import { ARCH, archColor } from './lib/archetypes.js'
  let D = $state({})
  let rooms = $state([])
  let slug = $state('demo')
  let ready = $state(false)
  let liveFlash = $state(false)
  const NAMES = ['meta','graph','rankings','personas','timeline','topics',
                 'topics_named','narrative','characters','summaries','daily']
  async function loadAll() {
    const res = await Promise.all(NAMES.map(load))
    const obj = {}; NAMES.forEach((n, i) => obj[n] = res[i]); return obj
  }
  let tab = $state('overview')
  let selChar = $state(null)
  let minW = $state(2)
  let focusName = $state(null)
  let query = $state('')
  let pquery = $state('')
  let psort = $state('msgs')
  let pfilter = $state('')
  let selDay = $state(null)

  const SORTS = [{ k: 'msgs', l: '발언순' }, { k: 'react_in', l: '공감순' }, { k: 'degree', l: '관계순' }]
  const roster = () => {
    const all = Object.values(D.summaries ?? {})
    const q = pquery.trim()
    let r = q ? all.filter(x => x.name.includes(q)) : all
    if (pfilter) r = r.filter(x => x.archetype === pfilter)
    r = r.slice().sort((a, b) => (b[psort] || 0) - (a[psort] || 0))
    return r.slice(0, (q || pfilter) ? 400 : 90)
  }
  const topDegree = () => Object.values(D.personas?.people ?? {})
    .filter(p => (p.text || 0) >= 10).sort((a, b) => (b.degree || 0) - (a.degree || 0)).slice(0, 10)
  const dayInfo = () => (D.daily?.days ?? []).find(d => d.date === selDay)
  const dayNarr = () => (D.daily_narrative ?? {})[selDay]
  const allNames = () => {
    const s = new Set()
    for (const k in (D.personas?.people ?? {})) s.add(D.personas.people[k].name)
    return [...s].sort()
  }
  function doSearch(name) {
    const nm = (name ?? query).trim()
    if (!nm) { focusName = null; return }
    const names = allNames()
    const hit = names.find(n => n === nm) || names.find(n => n.includes(nm))
    if (hit) { tab = 'graph'; query = hit; openPerson(hit) }
  }

  // multi-room: data lives under data/rooms/<slug>/. index.json lists rooms.
  const load = (n) => fetch(`${import.meta.env.BASE_URL}data/rooms/${slug}/${n}.json`)
    .then(r => r.ok ? r.json() : null).catch(() => null)
  async function switchRoom(s) {
    if (s === slug) return
    slug = s; ready = false
    D = await loadAll()
    selDay = D.daily?.days?.[0]?.date ?? null
    ready = true; tab = 'overview'
    try { history.replaceState(null, '', `?room=${s}`) } catch {}
  }

  onMount(async () => {
    // load the room index; pick ?room= or the biggest room
    const idx = await fetch(`${import.meta.env.BASE_URL}data/index.json`)
      .then(r => r.ok ? r.json() : null).catch(() => null)
    rooms = idx?.rooms ?? []
    const want = new URLSearchParams(location.search).get('room')
    slug = (want && rooms.some(r => r.slug === want)) ? want : (rooms[0]?.slug ?? 'demo')
    D = await loadAll()
    selDay = D.daily?.days?.[0]?.date ?? null
    ready = true
    // live refresh: poll meta every 40s; if new messages arrived, swap in fresh data
    // (no page reload — reactive state update). The 10-min updater regenerates JSON.
    setInterval(async () => {
      try {
        const m = await (await fetch(`${import.meta.env.BASE_URL}data/rooms/${slug}/meta.json`, { cache: 'no-store' })).json()
        if (m && D.meta && m.messages !== D.meta.messages) {
          const fresh = await loadAll()
          const keepDay = fresh.daily?.days?.some(d => d.date === selDay)
          D = fresh
          if (!keepDay) selDay = fresh.daily?.days?.[0]?.date ?? selDay
          liveFlash = true; setTimeout(() => liveFlash = false, 3000)
        }
      } catch {}
    }, 40000)
  })

  function openPerson(name) {
    const c = D.characters?.characters?.find(x => x.name === name)
    let p = null
    const pp = D.personas?.people ?? {}
    for (const k in pp) { if (pp[k].name === name) { p = pp[k]; break } }
    const sm = D.summaries?.[name]
    const base = c || { name, archetype: p?.archetype || sm?.archetype || '',
                        title: sm?.title || '', summary: sm?.summary || '' }
    selChar = { ...base, _conn: p?.connections ?? [], _p: p }
    focusName = name
  }

  const tabs = [
    { id: 'overview', label: '개요', icon: LayoutDashboard },
    { id: 'daily', label: '일일요약', icon: CalendarDays },
    { id: 'graph', label: '관계도', icon: Network },
    { id: 'people', label: '인물', icon: Users },
    { id: 'topics', label: '토픽', icon: Hash },
  ]
  const fmt = (n) => (n ?? 0).toLocaleString()
</script>

{#if !ready}
  <div class="loading"><Sparkles size={18}/> 데이터 불러오는 중…</div>
{:else}
{#snippet nlink(name)}<button class="nlink" onclick={() => openPerson(name)} title="프로필 보기">{name}</button>{/snippet}
<div class="app">
  <header>
    <div class="brand">
      <MessageSquare size={20} color="#7C6BF5"/>
      <div>
        <h1>{D.meta?.room ?? '카카오톡 방 분석'}
          <span class="livebadge" title="새로고침 없이 자동 갱신"><i></i>실시간</span>
          {#if liveFlash}<span class="liveflash">새 메시지 반영됨</span>{/if}
        </h1>
        {#if rooms.length > 1}
          <select class="roomsel" value={slug} onchange={(e) => switchRoom(e.target.value)}>
            {#each rooms as r}<option value={r.slug}>{r.room} · {fmt(r.messages)}</option>{/each}
          </select>
        {/if}
        <div class="muted sub">
          {fmt(D.meta?.messages)} 메시지 · {fmt(D.meta?.participants)} 참여자 ·
          {D.meta?.date_span?.[0]} – {D.meta?.date_span?.[1]}
        </div>
      </div>
    </div>
    <nav>
      {#each tabs as t}
        <button class:active={tab === t.id} onclick={() => tab = t.id}>
          <t.icon size={15}/> {t.label}
        </button>
      {/each}
    </nav>
  </header>

  {#if tab === 'overview'}
    <section class="grid">
      <div class="card span2">
        <h3><TrendingUp size={16}/> 커뮤니티 서사</h3>
        <p class="arc">{D.narrative?.arc}</p>
        <div class="months">
          {#each D.narrative?.months ?? [] as m}
            {@const vol = D.timeline?.month?.find(x => x.key === m.key)?.n ?? 0}
            <div class="mrow">
              <div class="mk">{m.key}</div>
              <div class="mbar"><span style="width:{Math.min(100, vol/250)}%"></span></div>
              <div class="mtext"><b>{m.headline}</b><div class="muted">{m.summary}</div></div>
            </div>
          {/each}
        </div>
      </div>

      <div class="card">
        <h3><Trophy size={16}/> 활동 랭킹</h3>
        <ol class="rank">
          {#each D.rankings?.most_active?.slice(0,10) ?? [] as [name, msgs]}
            <li>{@render nlink(name)}<b>{fmt(msgs)}</b></li>
          {/each}
        </ol>
      </div>

      {#if D.meta?.has_reactions}
        <div class="card">
          <h3><Heart size={16}/> 가장 공감받은 사람</h3>
          <ol class="rank">
            {#each D.rankings?.most_reacted?.slice(0,10) ?? [] as [name, rc]}
              <li>{@render nlink(name)}<b>{fmt(rc)}</b></li>
            {/each}
          </ol>
          <div class="note muted">메시지당 공감률 1위: {D.rankings?.best_ratio_reacted?.[0]?.[0]}
            ({D.rankings?.best_ratio_reacted?.[0]?.[1]}/msg)</div>
        </div>
      {:else}
        <div class="card">
          <h3><Network size={16}/> 관계 넓은 사람</h3>
          <ol class="rank">
            {#each topDegree() as p}
              <li>{@render nlink(p.name)}<b>{fmt(p.degree)}</b></li>
            {/each}
          </ol>
          <div class="note muted">가장 많은 사람과 대화한 순 (내보내기엔 공감 데이터가 없어요)</div>
        </div>
      {/if}
    </section>
  {/if}

  {#if tab === 'daily'}
    {@const di = dayInfo()}
    {@const dn = dayNarr()}
    <section class="daily">
      <aside class="daylist scroll">
        {#each D.daily?.days ?? [] as d}
          <button class:active={d.date === selDay} onclick={() => selDay = d.date}>
            <span class="dd">{d.date.slice(5)}</span>
            <span class="dn muted">{d.n}건</span>
            <span class="dbar"><i style="width:{Math.min(100, d.n / 9)}%"></i></span>
          </button>
        {/each}
      </aside>
      <div class="daydetail">
        {#if di}
          <div class="dhead">
            <h2>{di.date} <span class="muted wd">{['일','월','화','수','목','금','토'][new Date(di.date).getDay()]}요일</span></h2>
            <div class="dstats">
              <span class="chip"><MessageSquare size={13}/> {di.n.toLocaleString()}건</span>
              <span class="chip"><Users size={13}/> {di.users}명</span>
              {#if di.peak_hour != null}<span class="chip">피크 {di.peak_hour}시</span>{/if}
              {#if di.media}<span class="chip">미디어 {di.media}</span>{/if}
            </div>
          </div>
          <div class="card dsum">
            <h3><Sparkles size={15}/> 오늘의 대화 요약</h3>
            {#if dn?.summary}
              <p class="dnarr">{dn.headline ? dn.headline + ' — ' : ''}{dn.summary}</p>
            {/if}
            <p class="muted dauto">{di.auto}</p>
            <div class="dkw">{#each di.keywords.slice(0,10) as k}<span class="chip">{k}</span>{/each}</div>
          </div>
          <div class="dcols">
            <div class="card">
              <h3><Trophy size={15}/> 그날의 참여자</h3>
              <ol class="rank drank">
                {#each di.top_authors as [name, n], i}
                  {@const mx = di.top_authors[0][1]}
                  <li class="drow">
                    <span class="davatar" style="background:{archColor(D.summaries?.[name]?.archetype)}">{name.slice(0,1)}</span>
                    {@render nlink(name)}
                    <span class="dcbar"><i style="width:{Math.max(8, n / mx * 100)}%"></i></span>
                    <b>{fmt(n)}</b>
                  </li>
                {/each}
              </ol>
            </div>
            <div class="card">
              <h3><Heart size={15}/> 하이라이트</h3>
              <div class="hl">
                {#each di.highlights as h}
                  <div class="hlcard">
                    <div class="hlmeta">
                      <span class="hlav" style="background:{archColor(D.summaries?.[h.author]?.archetype)}">{h.author.slice(0,1)}</span>
                      {@render nlink(h.author)}
                      {#if h.react}<span class="hlreact"><Heart size={11}/> {h.react}</span>{/if}
                    </div>
                    <div class="hltext">{h.text}</div>
                  </div>
                {/each}
                {#if !di.highlights?.length}<div class="muted small">이 날은 공감받은 글이 없어요</div>{/if}
              </div>
            </div>
          </div>
        {/if}
      </div>
    </section>
  {/if}

  {#if tab === 'graph'}
    <section>
      <div class="gcontrols">
        <div class="search">
          <Search size={15}/>
          <input list="names" placeholder="인물 검색 (이름 입력)" bind:value={query}
            onchange={() => doSearch()} onkeydown={(e) => e.key === 'Enter' && doSearch()} />
          <datalist id="names">{#each allNames() as n}<option value={n}></option>{/each}</datalist>
        </div>
        {#if focusName}
          <button class="chip focus" onclick={() => { focusName = null; query = '' }}>
            {focusName} 관계망 · 전체보기로 ×</button>
        {:else}
          <label class="slider">강도 {minW}+
            <input type="range" min="2" max="20" bind:value={minW} /></label>
        {/if}
      </div>
      <div class="legend">
        {#each Object.entries(ARCH) as [k, v]}
          <span class="chip" style="border-color:{v.color}55">
            <i style="background:{v.color}"></i>{k}</span>
        {/each}
      </div>
      {#if D.graph}<ForceGraph graph={D.graph} onselect={openPerson} minWeight={minW} focus={focusName} />{/if}
      <p class="muted hint">원 크기 = 발언량 · 색 = 원형 · 선 = 대화 인접 강도.
        <b>검색하거나 노드를 클릭하면 그 사람의 모든 관계</b>가 펼쳐지고, 노드 클릭 시 상세 프로필이 열립니다.
        전체 {D.graph?.total_participants}명 중 관계를 맺은 {D.graph?.nodes?.length}명 · 슬라이더로 밀도 조절.</p>
    </section>
  {/if}

  {#if tab === 'people'}
    <section class="people">
      <div class="gcontrols">
        <div class="search">
          <Search size={15}/>
          <input placeholder="인물 검색 (대화이력 있는 {Object.keys(D.summaries ?? {}).length}명 전체)" bind:value={pquery} />
        </div>
        <span class="muted small">클릭하면 상세 프로필이 열립니다</span>
      </div>
      <div class="pfilters">
        {#each SORTS as s}
          <button class="fchip" class:on={psort === s.k} onclick={() => psort = s.k}>{s.l}</button>
        {/each}
        <span class="fsep"></span>
        <button class="fchip" class:on={pfilter === ''} onclick={() => pfilter = ''}>전체</button>
        {#each Object.keys(ARCH) as a}
          <button class="fchip" class:on={pfilter === a} onclick={() => pfilter = a}
            style={pfilter === a ? `border-color:${archColor(a)};color:${archColor(a)}` : ''}>{a}</button>
        {/each}
      </div>
      <div class="pcards">
        {#each roster() as pr}
          <button class="pcard" onclick={() => openPerson(pr.name)}
            style="border-color:{archColor(pr.archetype)}44">
            <div class="phead">
              <span class="pav" style="background:{archColor(pr.archetype)}">{pr.name.slice(0,1)}</span>
              <div>
                <div class="pname">{pr.name}</div>
                <div class="ptitle" style="color:{archColor(pr.archetype)}">{pr.title}</div>
              </div>
            </div>
            <div class="muted pstat">발언 {fmt(pr.msgs)}{#if D.meta?.has_reactions} · 공감 {fmt(pr.react_in)}{/if} · 관계 {pr.degree ?? 0}</div>
          </button>
        {/each}
      </div>

      <div class="card" style="margin-top:16px">
        <h3><Users size={16}/> 원형별 대표 인물</h3>
        <div class="arch-grid">
          {#each Object.entries(D.rankings?.personas ?? {}) as [label, people]}
            <div class="arch">
              <div class="atitle" style="color:{archColor(label)}">{label}</div>
              <div class="atop">
                {#each people.slice(0,5) as [name]}{@render nlink(name)}{/each}
              </div>
            </div>
          {/each}
        </div>
      </div>
    </section>
  {/if}

  {#if tab === 'topics'}
    <section class="topics">
      {#each (D.topics_named?.topics ?? D.topics?.topics ?? []) as t}
        {@const raw = D.topics?.topics?.find(x => x.id === t.id) ?? t}
        {@const weeks = Object.keys(raw.weekly ?? {}).sort()}
        <div class="card topic">
          <div class="thead">
            <div>
              <div class="tname">{t.name ?? t.label}</div>
              {#if t.category}<span class="chip">{t.category}</span>{/if}
            </div>
            <div class="tsize muted">{fmt(raw.size)}건 · 피크 {raw.peak_week}</div>
          </div>
          {#if t.summary}<p class="tsum">{t.summary}</p>{/if}
          <Spark data={weeks.map(w => raw.weekly[w])} color="#7C6BF5" w={260} h={38}/>
          <div class="tauthors">
            {#each (raw.authors ?? []).slice(0,5) as a}{@render nlink(a[0])}{/each}
          </div>
        </div>
      {/each}
    </section>
  {/if}


</div>

{#if selChar}
  <div class="modal" onclick={() => selChar = null} role="button" tabindex="-1">
    <div class="sheet" onclick={(e) => e.stopPropagation()} role="dialog">
      <div class="phead big">
        <span class="pav" style="background:{archColor(selChar.archetype)}">{selChar.name.slice(0,1)}</span>
        <div>
          <div class="pname">{selChar.name}</div>
          <div class="ptitle" style="color:{archColor(selChar.archetype)}">{selChar.title || selChar.archetype}</div>
        </div>
        <span class="chip" style="margin-left:auto">{selChar.archetype}</span>
      </div>

      {#if selChar.summary && !selChar.personality}
        <p class="psummary">{selChar.summary}</p>
      {/if}
      <dl>
        {#if selChar.personality}<dt>성격</dt><dd>{selChar.personality}</dd>{/if}
        {#if selChar.style}<dt>말투</dt><dd>{selChar.style}</dd>{/if}
        {#if selChar.role}<dt>역할</dt><dd>{selChar.role}</dd>{/if}
        {#if selChar.signature_quote}<dt>한마디</dt><dd class="quote">“{selChar.signature_quote}”</dd>{/if}
        {#if selChar.stat_highlight}<dt>특이수치</dt><dd>{selChar.stat_highlight}</dd>{/if}
        {#if selChar._p}
          <dt>지표</dt><dd class="muted">메시지 {(selChar._p.msgs).toLocaleString()} ·
            공감 {selChar._p.react_in} ({selChar._p.react_per_msg}/msg) ·
            연결 {selChar._p.degree}명 · 대화상대 {selChar._p.partners}</dd>
        {/if}
      </dl>
      {#if selChar._p}
        {@const p = selChar._p}
        {@const traits = [
          { k: '질문', v: p.q_ratio, c: '#7ee0c0' },
          { k: '유머', v: p.laugh_ratio, c: '#f0d066' },
          { k: '논쟁', v: p.argue_ratio, c: '#ef6f6f' },
          { k: '코드·기술', v: p.code_ratio, c: '#7C6BF5' },
          { k: '미디어', v: p.media_ratio, c: '#6ec6f0' },
          { k: '새벽활동', v: p.night_ratio, c: '#8b95cf' },
          { k: '공감유발', v: Math.min(1, (p.react_per_msg ?? 0)), c: '#f0b866' },
        ]}
        <div class="traits">
          <div class="clabel"><Sparkles size={13}/> 성향 지표 (데이터 기반)</div>
          {#each traits as t}
            <div class="trow">
              <span class="tk">{t.k}</span>
              <span class="tbar"><i style="width:{Math.min(100, t.v * 100 / 0.6 * (t.k==='공감유발'?0.6:1))}%;background:{t.c}"></i></span>
              <span class="tv">{(t.v ?? 0).toFixed(2)}</span>
            </div>
          {/each}
        </div>
      {/if}
      {#if (selChar._conn ?? []).length}
        {@const maxw = Math.max(...selChar._conn.map(c => c.weight))}
        <div class="conn">
          <div class="clabel"><Network size={14}/> 실제 연결 · 전체 {selChar._conn.length}명 (대화 인접 강도)</div>
          <div class="clist scroll">
            {#each selChar._conn as c}
              <button class="crow" onclick={() => openPerson(c.name)}>
                <span class="cn">{c.name}</span>
                <span class="cbar"><i style="width:{Math.max(6, c.weight / maxw * 100)}%"></i></span>
                <span class="cw">{c.weight}</span>
              </button>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}
{/if}

<style>
  .loading { display:flex; gap:8px; align-items:center; justify-content:center;
    height:100vh; color:var(--muted); }
  .app { max-width: 1120px; margin: 0 auto; padding: 22px 20px 60px; }
  header { display:flex; justify-content:space-between; align-items:flex-end;
    gap:16px; flex-wrap:wrap; margin-bottom:20px; }
  .brand { display:flex; gap:12px; align-items:center; }
  h1 { font-size: 19px; }
  .livebadge { display:inline-flex; align-items:center; gap:5px; font-size:11px; font-family:var(--mono);
    color:var(--live); border:1px solid rgba(124,107,245,.35); border-radius:999px; padding:1px 8px;
    margin-left:8px; vertical-align:middle; font-weight:400; letter-spacing:.02em; }
  .livebadge i { width:6px; height:6px; border-radius:50%; background:var(--live);
    box-shadow:0 0 7px var(--live); animation:lpulse 1.6s infinite; }
  @keyframes lpulse { 0%,100%{opacity:.5} 50%{opacity:1} }
  .roomsel { margin-top:4px; background:var(--panel2); color:var(--fg); border:1px solid var(--hair);
    border-radius:6px; padding:3px 8px; font-family:var(--sans); font-size:12px; max-width:280px; }
  .liveflash { font-size:11px; font-family:var(--mono); color:var(--live); margin-left:8px;
    animation:fadein .3s; } @keyframes fadein { from{opacity:0} to{opacity:1} }
  .sub { font-size: 12.5px; margin-top:2px; }
  nav { display:flex; gap:4px; background:var(--panel); border:1px solid var(--line);
    border-radius:10px; padding:4px; }
  nav button { display:flex; gap:6px; align-items:center; background:transparent;
    border:0; color:var(--muted); padding:7px 13px; border-radius:7px; cursor:pointer;
    font-size:13px; font-family:inherit; }
  nav button.active { background:var(--panel2); color:var(--fg); }
  .grid { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
  .span2 { grid-column: 1 / -1; }
  h3 { display:flex; gap:7px; align-items:center; font-size:14px; margin-bottom:12px; }
  .arc { font-size:14.5px; line-height:1.7; margin:0 0 16px; }
  .months { display:flex; flex-direction:column; gap:10px; }
  .mrow { display:grid; grid-template-columns:64px 90px 1fr; gap:12px; align-items:start; }
  .mk { font-variant-numeric:tabular-nums; color:var(--muted); font-size:12.5px; padding-top:2px; }
  .mbar { height:7px; background:var(--panel2); border-radius:5px; margin-top:6px; overflow:hidden; }
  .mbar span { display:block; height:100%; background:linear-gradient(90deg,#7C6BF5,#6355d6); }
  .mtext b { font-size:13.5px; }
  .rank { list-style:none; margin:0; padding:0; counter-reset:r; }
  .rank li { display:flex; justify-content:space-between; padding:5px 0;
    border-bottom:1px solid var(--line); counter-increment:r; font-size:13.5px; }
  .rank li::before { content:counter(r); color:var(--muted); width:20px; display:inline-block; }
  .rank li span { flex:1; }
  .rank b { font-variant-numeric:tabular-nums; }
  .note { margin-top:10px; font-size:12px; }
  .legend { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:12px; }
  .legend i { width:9px; height:9px; border-radius:50%; display:inline-block; }
  .hint { font-size:12.5px; margin-top:10px; }
  .pfilters { display:flex; flex-wrap:wrap; gap:6px; margin-bottom:14px; align-items:center; }
  .fchip { background:transparent; border:1px solid var(--hair); color:var(--mid); border-radius:999px;
    padding:4px 11px; font-size:12px; font-family:var(--sans); cursor:pointer; }
  .fchip.on { background:rgba(255,255,255,.06); color:var(--fg); border-color:var(--fg); }
  .fsep { width:1px; height:16px; background:var(--hair); margin:0 4px; }
  .people .pcards { display:grid; grid-template-columns:repeat(auto-fill,minmax(215px,1fr)); gap:12px; }
  .pcard { text-align:left; background:var(--panel); border:1px solid var(--line);
    border-radius:12px; padding:14px; cursor:pointer; font-family:inherit; color:var(--fg); }
  .pcard:hover { background:var(--panel2); }
  .phead { display:flex; gap:11px; align-items:center; }
  .phead.big { margin-bottom:14px; }
  .pav { width:38px; height:38px; border-radius:10px; display:flex; align-items:center;
    justify-content:center; font-weight:700; color:#050505; font-size:16px; }
  .pname { font-weight:650; font-size:14.5px; }
  .ptitle { font-size:12.5px; margin-top:1px; }
  .pstat { margin-top:10px; font-size:12px; }
  .arch-grid { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:12px; }
  .atitle { font-weight:650; } .small { font-size:12px; }
  .atop { font-size:12.5px; margin-top:4px; }
  .topics { display:grid; grid-template-columns:repeat(auto-fill,minmax(300px,1fr)); gap:14px; }
  .thead { display:flex; justify-content:space-between; align-items:flex-start; gap:8px; }
  .tname { font-weight:650; font-size:14.5px; margin-bottom:5px; }
  .tsize { font-size:12px; white-space:nowrap; }
  .tsum { font-size:13px; color:#c9c7c1; margin:10px 0; }
  .tauthors { margin-top:6px; }
  .modal { position:fixed; inset:0; background:rgba(3,3,3,.86); backdrop-filter:blur(3px);
    display:flex; align-items:center; justify-content:center; padding:20px; z-index:50; }
  .sheet { background:#0d0d0d; border:1px solid var(--hair); border-radius:14px;
    padding:22px; max-width:520px; width:100%; max-height:88vh; overflow-y:auto;
    box-shadow:0 24px 70px rgba(0,0,0,.7); }
  dl { display:grid; grid-template-columns:84px 1fr; gap:9px 14px; margin:0; }
  dt { color:var(--muted); font-size:12.5px; } dd { margin:0; font-size:13.5px; }
  .quote { color:var(--accent2); }
  .psummary { font-size:14px; line-height:1.65; margin:0 0 14px; color:#c9c7c1; }
  .gcontrols { display:flex; gap:12px; align-items:center; margin-bottom:12px; flex-wrap:wrap; }
  .search { display:flex; align-items:center; gap:8px; background:var(--panel);
    border:1px solid var(--line); border-radius:9px; padding:7px 12px; min-width:260px; }
  .search input { background:transparent; border:0; color:var(--fg); outline:none;
    font-family:inherit; font-size:13.5px; width:100%; }
  .slider { display:flex; align-items:center; gap:8px; color:var(--muted); font-size:12.5px; }
  .focus { cursor:pointer; color:var(--accent); border-color:#7C6BF555; }
  .clist { max-height:210px; overflow-y:auto; padding-right:4px; }
  .traits { margin-top:16px; border-top:1px solid var(--line); padding-top:14px; }
  .trow { display:grid; grid-template-columns:70px 1fr 34px; gap:10px; align-items:center; padding:2px 0; }
  .tk { font-size:12.5px; color:var(--muted); }
  .tbar { height:7px; background:var(--panel2); border-radius:5px; overflow:hidden; }
  .tbar i { display:block; height:100%; border-radius:5px; }
  .tv { font-size:11.5px; color:var(--muted); text-align:right; font-variant-numeric:tabular-nums; }
  .conn { margin-top:16px; border-top:1px solid var(--line); padding-top:14px; }
  .clabel { display:flex; gap:6px; align-items:center; font-size:12.5px;
    color:var(--muted); margin-bottom:10px; }
  .crow { display:grid; grid-template-columns:96px 1fr 34px; gap:10px; align-items:center;
    width:100%; background:transparent; border:0; color:var(--fg); font-family:inherit;
    padding:3px 0; cursor:pointer; }
  .crow:hover .cn { color:var(--accent); }
  .cn { font-size:13px; text-align:left; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .cbar { height:7px; background:var(--panel2); border-radius:5px; overflow:hidden; }
  .cbar i { display:block; height:100%; background:linear-gradient(90deg,#7C6BF5,#6355d6); }
  .cw { font-size:12px; color:var(--muted); text-align:right; font-variant-numeric:tabular-nums; }
  .daily { display:grid; grid-template-columns:150px 1fr; gap:16px; align-items:start; }
  .daylist { max-height:640px; overflow-y:auto; display:flex; flex-direction:column; gap:3px;
    border:1px solid var(--line); border-radius:12px; padding:8px; background:var(--panel); }
  .daylist button { display:grid; grid-template-columns:44px 1fr; gap:6px; align-items:center;
    background:transparent; border:0; color:var(--fg); font-family:inherit; cursor:pointer;
    padding:6px 8px; border-radius:7px; text-align:left; position:relative; }
  .daylist button.active { background:var(--panel2); }
  .daylist .dd { font-size:12px; font-variant-numeric:tabular-nums; }
  .daylist .dn { font-size:11px; }
  .daylist .dbar { grid-column:1 / -1; height:3px; background:#1c2333; border-radius:3px; overflow:hidden; }
  .daylist .dbar i { display:block; height:100%; background:#7C6BF5; }
  .dhead { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:14px; flex-wrap:wrap; gap:8px; }
  .dhead h2 { font-size:20px; } .wd { font-size:13px; font-weight:400; margin-left:6px; }
  .dstats { display:flex; gap:6px; flex-wrap:wrap; }
  .dstats .chip, .dkw .chip { display:inline-flex; gap:4px; align-items:center; }
  .dsum { margin-bottom:14px; }
  .dnarr { font-size:15px; line-height:1.7; margin:0 0 10px; }
  .dauto { font-size:12.5px; margin:0 0 12px; }
  .dkw { display:flex; gap:6px; flex-wrap:wrap; }
  .dcols { display:grid; grid-template-columns:1fr 1.4fr; gap:14px; }
  /* clickable name link — used everywhere a nickname appears */
  .nlink { background:transparent; border:0; color:var(--fg); font-family:inherit; font-size:inherit;
    cursor:pointer; padding:0; text-align:left; border-bottom:1px dotted transparent; }
  .nlink:hover { color:var(--live); border-bottom-color:var(--live); }
  /* daily — participants */
  .drank .drow { display:grid; grid-template-columns:24px auto 1fr auto; gap:9px; align-items:center;
    padding:5px 0; border-bottom:1px solid var(--hair2); }
  .drank .drow::before { content:none; }
  .davatar { width:24px; height:24px; border-radius:7px; display:flex; align-items:center;
    justify-content:center; font-size:11px; font-weight:700; color:#050505; }
  .dcbar { height:5px; background:var(--panel2); border-radius:4px; overflow:hidden; }
  .dcbar i { display:block; height:100%; background:linear-gradient(90deg,#7C6BF5,#6355d6); }
  /* daily — highlights */
  .hl { display:flex; flex-direction:column; gap:10px; }
  .hlcard { background:var(--panel); border:1px solid var(--hair2); border-radius:8px; padding:11px 13px; }
  .hlmeta { display:flex; gap:8px; align-items:center; margin-bottom:6px; font-size:13px; }
  .hlav { width:22px; height:22px; border-radius:6px; display:flex; align-items:center; justify-content:center;
    font-size:11px; font-weight:700; color:#050505; }
  .hlreact { margin-left:auto; display:inline-flex; align-items:center; gap:3px; font-family:var(--mono);
    font-size:11px; color:var(--live); }
  .hltext { font-size:13px; line-height:1.6; color:#c9c7c1; white-space:pre-wrap; }
  .tauthors { display:flex; flex-wrap:wrap; gap:5px 12px; margin-top:8px; font-size:12.5px; }
  .small { font-size:12px; }
  @media (max-width:720px){ .grid,.dcols{grid-template-columns:1fr;} .daily{grid-template-columns:1fr;} }
  @media (max-width:640px){
    .app { padding: 14px 12px 80px; }
    header { align-items: flex-start; gap: 10px; margin-bottom: 14px; }
    h1 { font-size: 16px; }
    nav { width: 100%; overflow-x: auto; flex-wrap: nowrap; -webkit-overflow-scrolling: touch; }
    nav::-webkit-scrollbar { display: none; }
    nav button { flex: 0 0 auto; padding: 8px 11px; }
    .gcontrols { flex-direction: column; align-items: stretch; }
    .search { min-width: 0; }
    .pcards { grid-template-columns: repeat(auto-fill,minmax(150px,1fr)); gap: 9px; }
    .daily { gap: 10px; }
    .daylist { flex-direction: row; max-height: none; overflow-x: auto; overflow-y: hidden; }
    .daylist button { flex: 0 0 auto; width: 74px; }
    .daylist .dbar { display: none; }
    .dhead h2 { font-size: 17px; }
    .arch-grid, .pcards { grid-template-columns: repeat(auto-fill,minmax(140px,1fr)); }
    .sheet { padding: 16px; border-radius: 12px; }
  }
</style>
