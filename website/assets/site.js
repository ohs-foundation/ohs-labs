/* OHS Labs site: filters, overlays and charts. Data comes from build.py. */
(() => {
  const DATA = JSON.parse(document.getElementById('labs-data').textContent);
  const EXPS = DATA.experiments;
  const STAGE = Object.fromEntries(DATA.stages.map(s => [s.id, s]));
  const C = { ink: '#162325', muted: '#4D5B5E', faint: '#8a9799', tealDeep: '#07585C', purple: '#4F3F83' };
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  /* ---------- hero mosaic ---------- */
  const palette = ['#7262B7', '#0C87A7', '#7666b2', '#4F3F83', '#07858A', '#9fe7e3'];
  const m = document.getElementById('mosaic');
  for (let i = 0; i < 36; i++) {
    const s = document.createElement('span');
    s.style.background = palette[(i * 7 + (i >> 2)) % palette.length];
    s.style.animationDelay = ((i % 6) * 0.35 + Math.floor(i / 6) * 0.22).toFixed(2) + 's';
    m.appendChild(s);
  }

  /* ---------- stage filters ---------- */
  const grid = document.getElementById('cards');
  const empty = document.createElement('div');
  empty.className = 'empty';
  document.querySelectorAll('.chip').forEach(ch => ch.addEventListener('click', () => {
    document.querySelectorAll('.chip').forEach(c => c.classList.toggle('active', c === ch));
    const f = ch.dataset.f;
    let shown = 0;
    grid.querySelectorAll('.card').forEach(c => { const on = f === 'all' || c.dataset.s === f; c.style.display = on ? '' : 'none'; shown += on; });
    if (!shown) {
      empty.innerHTML = `<b>Nothing is ${esc(STAGE[f].label.toLowerCase())} yet.</b><br/>${esc(STAGE[f].desc)}`;
      grid.appendChild(empty);
    } else empty.remove();
  }));

  /* ---------- overlay ---------- */
  const ov = document.getElementById('overlay'), panel = document.getElementById('panel');
  let lastFocus = null;

  function open(slug) {
    const e = EXPS.find(x => x.slug === slug);
    if (!e) return close(true);
    lastFocus = document.activeElement;
    const card = grid.querySelector(`.card[data-id="${slug}"] .card-art`);
    const art = card ? [...card.children].filter(n => !n.classList.contains('stat')).map(n => n.outerHTML).join('') : '';
    const inv = e.involve || {};
    const proposal = e.stage === 'proposal';
    panel.innerHTML = `
      <div class="panel-hero">${art}
        <div class="panel-top"><span class="badge st-${e.stage}">${esc(STAGE[e.stage].label)}</span><button class="x" data-close aria-label="Close">×</button></div>
        <h2 id="ov-title">${esc(e.title)}</h2>
        <p>${esc(e.summary)}</p>
        ${e.byline ? `<div class="byline">${esc(e.byline)}</div>` : ''}
      </div>
      <div class="panel-body">
        <div class="linkbar">${(e.links || []).map(l => `<a class="btn ${l.primary ? 'btn-primary' : 'btn-outline'}" href="${esc(l.url)}" target="_blank" rel="noopener">${esc(l.label)} ↗</a>`).join('')}</div>
        ${document.getElementById('body-' + slug).innerHTML}
        <div class="cta-block">
          <div><h3>${esc(inv.title || (proposal ? 'Want to run this one?' : 'Rerun it, extend it, argue with it'))}</h3><p>${esc(inv.text || (proposal ? "Tell us on Discord or open an issue in ohs-labs. We'll help you set it up." : 'Try a new model or condition, or bring a related question to the next community call.'))}</p></div>
          <div style="display:flex;gap:10px;flex-wrap:wrap"><a class="btn btn-primary" href="https://discord.gg/sfgUU7AHZT" target="_blank" rel="noopener">Join Discord ↗</a><a class="btn btn-outline" href="https://github.com/ohs-foundation/ohs-labs" target="_blank" rel="noopener">ohs-labs repo ↗</a></div>
        </div>
      </div>`;
    panel.querySelector('.panel-hero svg')?.classList.add('bg');
    ov.classList.add('open');
    document.body.style.overflow = 'hidden';
    requestAnimationFrame(() => { ov.classList.add('show'); panel.scrollTop = 0; panel.querySelector('.x').focus(); });
    const charts = Object.fromEntries((e.charts || []).map(c => [c.id, c]));
    panel.querySelectorAll('[data-chart]').forEach(el => drawChart(el, charts[el.dataset.chart], charts));
    document.title = `${e.title} — OHS Labs`;
  }

  function close(silent) {
    ov.classList.remove('show');
    document.body.style.overflow = '';
    document.title = 'OHS Labs — Open Health Stack Software Foundation';
    setTimeout(() => ov.classList.remove('open'), 300);
    if (!silent && location.hash.startsWith('#/')) history.pushState('', document.title, location.pathname + location.search);
    if (lastFocus) lastFocus.focus();
  }
  ov.addEventListener('click', ev => { if (ev.target.closest('[data-close]')) close(); });
  document.addEventListener('keydown', ev => { if (ev.key === 'Escape' && ov.classList.contains('open')) close(); });
  const route = () => { const h = location.hash; if (h.startsWith('#/')) open(decodeURIComponent(h.slice(2))); else if (ov.classList.contains('open')) close(true); };
  window.addEventListener('hashchange', route);

  /* ---------- charts ---------- */
  // format: "{v}" raw, "{v1}" one decimal, "{v2}" two decimals; other text is kept.
  const fmt = (f, v) => (f || '{v}').replace(/\{v(\d?)\}/g, (_, d) => d ? Number(v).toFixed(+d) : String(v));
  const note = c => c.note ? `<p class="note">${c.note}</p>` : '';
  const legend = items => `<div class="legend">${items.map(([n, col]) => `<span><i style="background:${esc(col)}"></i>${esc(n)}</span>`).join('')}</div>`;

  function drawChart(el, c, all) {
    if (!c) { el.textContent = 'Chart not found.'; return; }
    if (c.type === 'grouped-bars') groupedBars(el, c);
    else if (c.type === 'columns') columns(el, c);
    else if (c.type === 'race') race(el, c, all[c.from]);
  }

  function groupedBars(el, c) {
    const metrics = c.metrics || [];
    el.innerHTML = (metrics.length > 1 ? `<div class="chart-ctl"><div class="seg">${metrics.map((mt, i) => `<button class="${i ? '' : 'on'}" data-m="${i}">${esc(mt.label)}</button>`).join('')}</div></div>` : '') +
      '<div class="plot"></div>' + legend(c.series.map(s => [s.name, s.color])) + note(c);
    const plot = el.querySelector('.plot');
    const draw = mi => {
      const mt = metrics[mi], groups = c.groups, n = c.series.length;
      const W = 820, barH = 16, gap = 4, rowH = n * (barH + gap) + 12, top = 10, left = 150, right = 70;
      const max = mt.max || Math.max(...mt.values.flat()) * 1.1;
      const H = top + groups.length * rowH + 14, span = W - left - right;
      let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(mt.label)}">`;
      for (let k = 0; k <= 5; k++) { const t = max * k / 5, x = left + span * k / 5; s += `<line x1="${x}" x2="${x}" y1="${top}" y2="${H - 16}" stroke="#EEF2F3"/><text x="${x}" y="${H - 2}" font-size="10.5" fill="${C.faint}" text-anchor="middle">${+t.toFixed(2)}</text>`; }
      groups.forEach((g, i) => {
        const y0 = top + i * rowH + 4;
        s += `<text x="0" y="${y0 + (n * (barH + gap)) / 2 + 4}" font-size="13" font-weight="600" fill="${C.ink}">${esc(g)}</text>`;
        mt.values[i].forEach((v, j) => {
          const w = Math.max(2, span * v / max), y = y0 + j * (barH + gap), hi = mt.highlight !== undefined && v === mt.highlight;
          s += `<rect class="bar" x="${left}" y="${y}" height="${barH}" rx="4" width="${w}" style="animation-delay:${(i * n + j) * 0.03}s" fill="${esc(c.series[j].color)}"/>`;
          s += `<text x="${left + w + 6}" y="${y + 12}" font-size="11" fill="${C.muted}" font-weight="${hi ? 700 : 500}">${esc(fmt(mt.format, v))}${hi ? ' ✓' : ''}</text>`;
        });
      });
      plot.innerHTML = s + '</svg>';
    };
    draw(0);
    el.querySelectorAll('.seg button').forEach(b => b.addEventListener('click', () => {
      el.querySelectorAll('.seg button').forEach(x => x.classList.toggle('on', x === b)); draw(+b.dataset.m);
    }));
  }

  function columns(el, c) {
    const cats = c.categories, ser = c.series, W = 820, H = 300, left = 70, right = 20, top = 20, bottom = 40;
    const vals = ser.flatMap(s => s.values).concat(c.line ? [c.line.value] : []);
    const lo = c.log ? Math.pow(10, Math.floor(Math.log10(Math.min(...vals)))) : 0;
    const hi = c.log ? Math.pow(10, Math.ceil(Math.log10(Math.max(...vals) * 1.3))) : Math.max(...vals) * 1.15;
    const y = v => c.log
      ? top + (H - top - bottom) * (1 - (Math.log10(v) - Math.log10(lo)) / (Math.log10(hi) - Math.log10(lo)))
      : top + (H - top - bottom) * (1 - v / hi);
    const gw = (W - left - right) / cats.length, bw = Math.min(56, (gw - 30) / ser.length - 6);
    let s = `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img">`;
    const ticks = c.log ? Array.from({ length: Math.round(Math.log10(hi / lo)) }, (_, k) => lo * Math.pow(10, k)) : [0, .25, .5, .75, 1].map(f => Math.round(hi * f));
    ticks.forEach(t => s += `<line x1="${left}" x2="${W - right}" y1="${y(t)}" y2="${y(t)}" stroke="#EEF2F3"/><text x="${left - 8}" y="${y(t) + 4}" font-size="11" fill="${C.faint}" text-anchor="end">${t.toLocaleString('en-US')}</text>`);
    cats.forEach((cat, i) => {
      const cx = left + gw * i + gw / 2, x0 = cx - (ser.length * (bw + 8) - 8) / 2;
      ser.forEach((se, j) => {
        const v = se.values[i], yy = y(v), x = x0 + j * (bw + 8);
        s += `<rect class="sbar" x="${x}" y="${yy}" width="${bw}" height="${H - bottom - yy}" rx="6" style="animation-delay:${(i * ser.length + j) * 0.09}s" fill="${esc(se.color)}"/>`;
        s += `<text x="${x + bw / 2}" y="${yy - 6}" font-size="11.5" font-weight="700" fill="${C.ink}" text-anchor="middle">${v.toLocaleString('en-US')}</text>`;
      });
      s += `<text x="${cx}" y="${H - bottom + 18}" font-size="12.5" font-weight="600" fill="${C.ink}" text-anchor="middle">${esc(cat.label)}</text>`;
      if (cat.sub) s += `<text x="${cx}" y="${H - bottom + 33}" font-size="11" fill="${C.faint}" text-anchor="middle">${esc(cat.sub)}</text>`;
    });
    const items = ser.map(se => [se.name, se.color]);
    if (c.line) {
      const col = c.line.color || C.purple;
      s += `<line x1="${left}" x2="${W - right}" y1="${y(c.line.value)}" y2="${y(c.line.value)}" stroke="${esc(col)}" stroke-dasharray="6 5" stroke-width="2"/><text x="${left + 6}" y="${y(c.line.value) - 6}" font-size="11" font-weight="700" fill="${esc(col)}">${esc(c.line.label || '')}</text>`;
      items.push([c.line.legend || c.line.label, col]);
    }
    el.innerHTML = s + '</svg>' + legend(items) + note(c);
  }

  function race(el, c, src) {
    const gi = src.groups.indexOf(c.group), M = id => src.metrics.find(mt => mt.id === id);
    const time = M(c.time).values[gi], ticks = c.ticks ? M(c.ticks) : null, extra = c.extra ? M(c.extra) : null;
    const tmax = Math.max(...time), nTicks = ticks ? (ticks.max || 10) : 0;
    el.innerHTML = (c.note ? `<p style="margin-top:0">${c.note}</p>` : '') + '<div class="replay">' + src.series.map((se, j) =>
      `<div class="lane"><span><b>${esc(se.name)}</b></span><div class="track"><div class="fill" style="background:${esc(se.color)}"></div></div><div class="checks">${'<span></span>'.repeat(nTicks)}</div></div>`).join('') +
      `<div class="note">Scroll here to start the replay.</div></div><div style="margin-top:14px"><button class="btn btn-outline">↻ Replay</button></div>`;
    const fills = el.querySelectorAll('.fill'), checks = el.querySelectorAll('.checks'), msg = el.querySelector('.replay .note');
    function run() {
      fills.forEach(f => { f.style.width = '0'; f.textContent = ''; });
      checks.forEach(k => k.querySelectorAll('span').forEach(s => s.style.background = ''));
      msg.textContent = 'Building…';
      const t0 = performance.now(), dur = matchMedia('(prefers-reduced-motion: reduce)').matches ? 0 : 4200;
      const frame = t => {
        const p = dur ? Math.min(1, Math.max(0, (t - t0) / dur)) : 1;
        src.series.forEach((se, j) => {
          const lp = Math.min(1, p * tmax / time[j]);
          fills[j].style.width = (lp * time[j] / tmax * 100) + '%';
          fills[j].textContent = lp > 0.25 ? (lp * time[j]).toFixed(1) + 'm' : '';
          if (lp >= 1 && ticks) {
            const sc = ticks.values[gi][j];
            checks[j].querySelectorAll('span').forEach((k, i) => { if (i < sc) k.style.background = sc === nTicks ? C.tealDeep : (se.color === '#B7C2C4' ? C.faint : se.color); });
          }
        });
        if (p < 1) requestAnimationFrame(frame);
        else msg.innerHTML = extra ? `Done. ${esc(extra.label)}: ${src.series.map((se, j) => `${esc(se.name)} <b>${esc(fmt(extra.format, extra.values[gi][j]))}</b>`).join(' · ')}.` : 'Done.';
      };
      requestAnimationFrame(frame);
    }
    el.querySelector('button').addEventListener('click', run);
    const io = new IntersectionObserver(es => { if (es.some(x => x.isIntersecting)) { io.disconnect(); run(); } }, { root: panel, threshold: 0.4 });
    io.observe(el);
  }

  route();
})();
