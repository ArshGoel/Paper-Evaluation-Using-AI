const loginText = document.querySelector(".title-text .login");
         const loginForm = document.querySelector("form.login");
         const loginBtn = document.querySelector("label.login");
         const signupBtn = document.querySelector("label.signup");
         const signupLink = document.querySelector("form .signup-link a");
         signupBtn.onclick = (()=>{
           loginForm.style.marginLeft = "-50%";
           loginText.style.marginLeft = "-50%";
         });
         loginBtn.onclick = (()=>{
           loginForm.style.marginLeft = "0%";
           loginText.style.marginLeft = "0%";
         });
         signupLink.onclick = (()=>{
           signupBtn.click();
           return false;
         });
         // static/your_app/galaxy.js
(function () {
  const container = document.querySelector('.galaxy-bg');
  if (!container) return;

  const canvas = document.createElement('canvas');
  canvas.className = 'galaxy-canvas';
  container.appendChild(canvas);

  const ctx = canvas.getContext('2d', { alpha: true });
  let w, h, stars = [], tick = 0;

  function resize() {
    w = canvas.width = container.clientWidth;
    h = canvas.height = container.clientHeight;
    // regenerate stars on resize
    stars = createStars();
  }

  function rand(min, max) { return Math.random() * (max - min) + min; }

  function createStars() {
    const base = Math.floor((w * h) / 2500); // density
    const list = [];
    for (let i = 0; i < base; i++) {
      const r = rand(0.2, 1.3);
      const orbit = rand(Math.min(w, h) * 0.1, Math.max(w, h) * 0.6);
      const speed = rand(0.0005, 0.0025) * (Math.random() < 0.5 ? -1 : 1);
      const hue = rand(210, 250);
      list.push({
        radius: r,
        orbit,
        angle: rand(0, Math.PI * 2),
        speed,
        twinkle: rand(0.5, 1),
        hue
      });
    }
    return list;
  }

  function draw() {
    ctx.clearRect(0, 0, w, h);

    // subtle nebula glow
    const g = ctx.createRadialGradient(w/2, h/2, Math.min(w,h)*0.1, w/2, h/2, Math.max(w,h)*0.7);
    g.addColorStop(0, 'rgba(90,110,180,0.10)');
    g.addColorStop(1, 'rgba(10,12,28,0)');
    ctx.fillStyle = g;
    ctx.fillRect(0, 0, w, h);

    const cx = w / 2 + Math.sin(tick * 0.0015) * (w * 0.05);
    const cy = h / 2 + Math.cos(tick * 0.001) * (h * 0.04);

    for (const s of stars) {
      s.angle += s.speed;

      const x = cx + Math.cos(s.angle) * s.orbit;
      const y = cy + Math.sin(s.angle) * (s.orbit * 0.6); // ellipse

      const tw = 0.6 + Math.sin((tick * 0.02) + s.orbit * 0.01) * 0.4 * s.twinkle;

      ctx.beginPath();
      ctx.arc(x, y, s.radius * tw, 0, Math.PI * 2);

      const grd = ctx.createRadialGradient(x, y, 0, x, y, s.radius * 3);
      grd.addColorStop(0, `hsla(${s.hue}, 90%, 85%, 0.9)`);
      grd.addColorStop(1, `hsla(${s.hue}, 90%, 60%, 0.05)`);
      ctx.fillStyle = grd;
      ctx.fill();
    }

    tick++;
    requestAnimationFrame(draw);
  }

  window.addEventListener('resize', resize);
  resize();
  requestAnimationFrame(draw);
})();
