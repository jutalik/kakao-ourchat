<script>
  import { onMount } from 'svelte'
  import ForceGraph from 'force-graph'
  import { archColor } from './archetypes.js'
  import { Plus, Minus, Locate } from 'lucide-svelte'

  let { graph, onselect = () => {}, minWeight = 7, focus = null } = $props()
  let el, fg
  let settling = $state(true)
  let twoHop = $state(false)
  let counts = $state({ nodes: 0, links: 0 })
  let allNodes = new Map(), allLinks = [], maxMsg = 1, bigIds = new Set()
  let hoverNode = null, hoverNodes = new Set(), hoverLinks = new Set()
  const rOf = (n) => 3 + 16 * Math.sqrt(n.msgs / maxMsg)

  function buildBase() {
    allNodes = new Map(graph.nodes.map(n => [n.id, { ...n }]))
    allLinks = graph.edges
      .filter(e => allNodes.has(e.source) && allNodes.has(e.target))
      .map(e => ({ source: e.source, target: e.target, weight: e.weight }))
    maxMsg = Math.max(1, ...graph.nodes.map(n => n.msgs))
    // label only the ~34 biggest hubs by default (canvas text is the costly part)
    bigIds = new Set([...allNodes.values()].sort((a, b) => b.msgs - a.msgs).slice(0, 34).map(n => n.id))
  }

  onMount(() => {
    fg = ForceGraph()(el)
      .backgroundColor('rgba(0,0,0,0)')
      .nodeId('id')
      .nodeLabel(n => `${n.name} · ${n.archetype || ''} · 발언 ${n.msgs.toLocaleString()} · 관계 ${n.degree ?? 0}`)
      .nodeRelSize(1)
      .nodeCanvasObjectMode(() => 'replace')
      .nodeCanvasObject((n, ctx, scale) => {
        const r = rOf(n)
        const dim = hoverNode && !hoverNodes.has(n.id)
        ctx.beginPath(); ctx.arc(n.x, n.y, r, 0, 2 * Math.PI)
        ctx.fillStyle = dim ? 'rgba(90,100,120,0.3)' : archColor(n.archetype)
        ctx.fill()
        if (focus === n.name) { ctx.lineWidth = 2.5 / scale; ctx.strokeStyle = '#fff'; ctx.stroke() }
        if (bigIds.has(n.id) || (hoverNode && hoverNode.id === n.id) || focus === n.name) {
          ctx.font = `${12 / scale}px -apple-system, sans-serif`
          ctx.textAlign = 'center'; ctx.textBaseline = 'top'
          ctx.fillStyle = dim ? '#5a6478' : '#f2f1ee'
          ctx.fillText(n.name, n.x, n.y + r + 1.5 / scale)
        }
      })
      .nodePointerAreaPaint((n, color, ctx) => {
        ctx.fillStyle = color; ctx.beginPath(); ctx.arc(n.x, n.y, rOf(n) + 2, 0, 2 * Math.PI); ctx.fill()
      })
      .linkColor(l => hoverLinks.has(l) ? 'rgba(124,107,245,0.9)'
        : (hoverNode ? 'rgba(120,140,180,0.05)' : 'rgba(120,140,180,0.15)'))
      .linkWidth(l => hoverLinks.has(l) ? 2 : Math.min(2.5, 0.3 + l.weight / 25))
      .onNodeHover(n => { hoverNode = n; computeHover(n) })
      .onNodeClick(n => onselect(n.name))
      .onBackgroundClick(() => { hoverNode = null; hoverNodes = new Set(); hoverLinks = new Set() })
      .cooldownTicks(80)
      .d3AlphaDecay(0.045)
      .d3VelocityDecay(0.32)
      .onEngineStop(() => { settling = false })

    const size = () => { if (el.clientWidth) fg.width(el.clientWidth).height(el.clientHeight) }
    const ro = new ResizeObserver(size); ro.observe(el); size()
    return () => { ro.disconnect(); try { fg._destructor?.() } catch {} }
  })

  function computeHover(n) {
    const nb = new Set(), lk = new Set()
    if (n) {
      nb.add(n.id)
      for (const l of fg.graphData().links) {
        const s = l.source.id ?? l.source, t = l.target.id ?? l.target
        if (s === n.id || t === n.id) { lk.add(l); nb.add(s); nb.add(t) }
      }
    }
    hoverNodes = nb; hoverLinks = lk
  }

  // rebuild base structures when the graph prop changes (live data reload),
  // then re-apply the current view. Also re-applies on filter/focus/hop changes.
  let builtFor = null
  $effect(() => {
    graph; minWeight; focus; twoHop
    if (!fg) return
    const wasFirst = builtFor === null
    if (builtFor !== graph) { buildBase(); builtFor = graph }
    apply(wasFirst)
  })

  function apply(first = false) {
    settling = true
    const focusId = focus ? [...allNodes.values()].find(n => n.name === focus)?.id : null
    let vis
    if (focusId) {
      const nbrs = new Set([focusId])
      allLinks.forEach(l => { if (l.source === focusId) nbrs.add(l.target); if (l.target === focusId) nbrs.add(l.source) })
      vis = twoHop
        ? allLinks.filter(l => nbrs.has(l.source) && nbrs.has(l.target))   // ego cluster interconnections
        : allLinks.filter(l => l.source === focusId || l.target === focusId)
    } else {
      vis = allLinks.filter(l => l.weight >= minWeight)
    }
    const keep = new Set(); vis.forEach(l => { keep.add(l.source); keep.add(l.target) })
    if (focusId) keep.add(focusId)
    const nodes = [...keep].map(id => allNodes.get(id))
    const links = vis.map(l => ({ source: l.source, target: l.target, weight: l.weight }))
    counts = { nodes: nodes.length, links: links.length }
    fg.graphData({ nodes, links })
    fg.d3Force('charge').strength(focusId ? -260 : -95)
    fg.d3Force('link').distance(l => 40 + 30 / Math.sqrt(l.weight))
    // center/fit once it has laid out a little
    setTimeout(() => fg && fg.zoomToFit(500, 55), first ? 400 : 250)
  }

  const zoomBtn = (f) => fg && fg.zoom(fg.zoom() * f, 250)
  const center = () => fg && fg.zoomToFit(450, 55)
</script>

<div class="wrap">
  <div class="canvas" bind:this={el}></div>

  {#if settling}
    <div class="loadbar"><div class="fill"></div></div>
    <div class="settle">관계망 그리는 중…</div>
  {/if}

  <div class="ctrl">
    <button onclick={() => zoomBtn(1.3)} title="확대"><Plus size={16}/></button>
    <button onclick={() => zoomBtn(0.77)} title="축소"><Minus size={16}/></button>
    <button onclick={center} title="정중앙 정렬"><Locate size={16}/></button>
  </div>
  {#if focus}
    <button class="hopbtn" class:on={twoHop} onclick={() => twoHop = !twoHop}>
      {twoHop ? '주변 파벌 보는 중' : '주변 파벌 펼치기'}
    </button>
  {/if}
  <div class="meta">
    {#if focus}<span class="chip">{focus} 의 관계 {counts.links}개</span>
    {:else}<span class="chip">{counts.nodes}명 · {counts.links}개 관계 (강도 {minWeight}+)</span>{/if}
  </div>
</div>

<style>
  .wrap { position: relative; width: 100%; height: 640px;
    border: 1px solid var(--line); border-radius: 12px; overflow: hidden;
    background: radial-gradient(1200px 600px at 50% 40%, #0b0b0b 0%, #050505 70%); }
  @media (max-width: 640px) { .wrap { height: 440px; } }
  .canvas { position: absolute; inset: 0; }
  .ctrl { position: absolute; top: 12px; right: 12px; display: flex; flex-direction: column; gap: 6px; }
  .ctrl button { width: 32px; height: 32px; display: flex; align-items: center;
    justify-content: center; background: #0e131dcc; color: var(--fg);
    border: 1px solid var(--line); border-radius: 8px; cursor: pointer; }
  .ctrl button:hover { background: var(--panel2); }
  .meta { position: absolute; bottom: 12px; right: 12px; }
  .hopbtn { position: absolute; bottom: 12px; left: 12px; background: #0e131dcc; color: var(--fg);
    border: 1px solid var(--hair); border-radius: 8px; padding: 6px 12px; font-size: 12px;
    font-family: var(--sans); cursor: pointer; }
  .hopbtn.on { background: var(--live); color: #052012; border-color: var(--live); }
  .settle { position: absolute; top: 12px; left: 12px; color: var(--muted); font-size: 12.5px;
    background: #0e131dcc; border: 1px solid var(--line); border-radius: 8px; padding: 6px 11px; }
  .loadbar { position: absolute; top: 0; left: 0; right: 0; height: 3px; background: #1c2333; overflow: hidden; }
  .loadbar .fill { height: 100%; width: 40%; background: linear-gradient(90deg,#7C6BF5,#6355d6);
    animation: slide 1s ease-in-out infinite; }
  @keyframes slide { 0% { margin-left: -40%; } 100% { margin-left: 100%; } }
</style>
