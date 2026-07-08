<script>
  let { data = [], color = '#6ea8fe', w = 160, h = 34 } = $props()
  // data: array of numbers
  const pts = $derived.by(() => {
    if (!data.length) return ''
    const max = Math.max(...data, 1)
    return data.map((v, i) =>
      `${(i / Math.max(1, data.length - 1)) * w},${h - (v / max) * (h - 4) - 2}`).join(' ')
  })
</script>
<svg width={w} height={h} class="spark">
  <polyline points={pts} fill="none" stroke={color} stroke-width="1.6"
    stroke-linejoin="round" stroke-linecap="round" />
</svg>
<style>.spark { display: block; }</style>
