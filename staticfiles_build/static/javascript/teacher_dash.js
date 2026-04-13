document.addEventListener('DOMContentLoaded', function () {
  const root = document.documentElement;
  const btn = document.getElementById('themeToggle');

  const saved = localStorage.getItem('sd-theme');
  if (saved) root.setAttribute('data-theme', saved);

  if (btn) {
    btn.addEventListener('click', () => {
      const curr = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      root.setAttribute('data-theme', curr);
      localStorage.setItem('sd-theme', curr);
      btn.textContent = curr === 'dark' ? '☀️' : '🌙';
    });

    btn.textContent =
      root.getAttribute('data-theme') === 'dark' ? '☀️' : '🌙';
  }
});

// Today label
(function todayLabel() {
  const el = document.getElementById('todayLabel');
  if (!el) return;
  const d = new Date();
  const opt = { weekday: 'long', month: 'short', day: 'numeric' };
  el.textContent = d.toLocaleDateString(undefined, opt);
})();

// Simple activity chart (no external libs)
(function chart() {
  const c = document.getElementById('activityChart');
  if (!c) return;
  const ctx = c.getContext('2d');

  // Demo data; replace via context by data-* attributes if you wish
  const days = [...Array(7)].map((_, i) => {
    const d = new Date(); d.setDate(d.getDate() - (6 - i));
    return d.toLocaleDateString(undefined, { weekday: 'short' });
  });
  const values = [3, 5, 2, 7, 6, 4, 8];

  // Sizing
  const W = c.clientWidth || c.width;
  const H = c.height;
  c.width = W; // ensure crispness
  const pad = 28;
  const innerW = W - pad * 2;
  const innerH = H - pad * 2;
  const maxV = Math.max(...values, 10);

  // Clear
  ctx.clearRect(0,0,W,H);

  // Grid
  ctx.globalAlpha = 0.15;
  ctx.strokeStyle = '#888';
  for (let i=0; i<=5; i++) {
    const y = pad + (innerH * i/5);
    ctx.beginPath();
    ctx.moveTo(pad, y);
    ctx.lineTo(W-pad, y);
    ctx.stroke();
  }
  ctx.globalAlpha = 1;

  // Line
  ctx.beginPath();
  values.forEach((v, i) => {
    const x = pad + innerW * (i/(values.length-1));
    const y = pad + innerH * (1 - (v/maxV));
    if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
  });
  ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--brand') || '#5b7cfa';
  ctx.lineWidth = 2;
  ctx.stroke();

  // Points
  values.forEach((v, i) => {
    const x = pad + innerW * (i/(values.length-1));
    const y = pad + innerH * (1 - (v/maxV));
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI*2);
    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--brand-2') || '#a445b2';
    ctx.fill();
  });

  // Labels
  ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--muted') || '#6b7280';
  ctx.font = '12px system-ui, -apple-system, Segoe UI, Roboto, Poppins, sans-serif';
  days.forEach((d, i) => {
    const x = pad + innerW * (i/(days.length-1));
    ctx.textAlign = 'center';
    ctx.fillText(d, x, H - 6);
  });
})();

// Optional: wire up placeholders if backend not sending data
(function hydratePlaceholders() {
  // Example if you want to fetch JSON and populate dashboard dynamically.
  // Leave empty for now—dashboard renders fine with template data.
})();
