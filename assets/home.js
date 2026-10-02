/* 首页各幕。每幕一个函数，缺元素就跳过 —— 一处 null 不能拖垮后面所有的幕。 */
(function () {
  "use strict";
  var S = window.Scenes, I18N = window.__I18N || {};
  function T(k) { return Object.prototype.hasOwnProperty.call(I18N, k) ? I18N[k] : k; }
  function $(sel, root) { return (root || document).querySelector(sel); }
  function all(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function px(v) { return v.toFixed(1) + "px"; }

  // ① 开场：图标是一扇小窗，往下滚，窗口打开就是整片风景（与 app 启动动画同一个母题）
  function sceneHero() {
    var hero = $(".hero"); if (!hero) return;
    var win = $(".hero-window", hero), slot = Live.slot(win), st = hero.style;
    S.on(hero, function (p) {
      var vw = document.documentElement.clientWidth, vh = window.innerHeight;
      var icon = Math.min(180, vw * 0.36);
      // 图标画面只占 png 画布的 80.47%（macOS 图标网格，四周留透明边）。窗口从画面大小起步，
      // 再收 2px 防抗锯齿描边 —— 按画布大小起步的话，壁纸会从图标四周露出一圈
      var art = icon * 0.8047 - 2;
      var e = S.easeInOut(S.segment(p, 0.04, 0.56));
      var w = S.lerp(art, vw, e), h = S.lerp(art, vh, e);
      st.setProperty("--il", px((vw - w) / 2));
      st.setProperty("--it", px((vh - h) / 2));
      st.setProperty("--ir", px(S.lerp(art * 0.2237, 0, e)));   // macOS 图标的连续圆角比例
      st.setProperty("--isz", px(S.lerp(icon, icon * 1.7, e)));
      st.setProperty("--io", (1 - S.segment(p, 0.08, 0.34)).toFixed(3));
      st.setProperty("--no", (1 - S.segment(p, 0, 0.1)).toFixed(3));
      var c = S.easeOut(S.segment(p, 0.56, 0.8));
      st.setProperty("--co", c.toFixed(3));
      st.setProperty("--cy", px(S.lerp(28, 0, c)));
      st.setProperty("--cs", S.lerp(0.96, 1, c).toFixed(4));
    });
    hero.addEventListener("pointermove", function (ev) {
      slot.pointer(ev.clientX / window.innerWidth, ev.clientY / window.innerHeight);
    });
  }

  // ② 一句话：随滚动逐词点亮。中文按词切（Intl.Segmenter），没有就按空白切
  function sceneStatement() {
    var sec = $(".statement"); if (!sec) return;
    var p = $("[data-words]", sec), text = p.textContent.trim();
    var parts = (window.Intl && Intl.Segmenter)
      ? Array.from(new Intl.Segmenter(document.documentElement.lang, { granularity: "word" }).segment(text),
                   function (x) { return x.segment; })
      : text.split(/(\s+)/);
    p.textContent = "";
    var spans = parts.map(function (w) {
      var s = document.createElement("span");
      s.className = "w";
      s.textContent = w;
      p.appendChild(s);
      return s;
    });
    p.setAttribute("data-ready", "");
    S.on(sec, function (prog) {
      var lit = Math.round(S.segment(prog, 0.22, 0.58) * spans.length);
      spans.forEach(function (s, i) { s.classList.toggle("lit", i < lit); });
    });
  }

  // ③ 精选：点缩略图，壁纸像 app 一样交叉淡入；←→ 在缩略图之间走
  function sceneGallery() {
    var screen = $("#gallery-live"); if (!screen) return;
    var slot = Live.slot(screen), thumbs = all(".thumb");
    function pick(btn, focus) {
      thumbs.forEach(function (b) {
        var on = b === btn;
        b.setAttribute("aria-checked", String(on));
        b.tabIndex = on ? 0 : -1;
      });
      $(".poster", screen).alt = $("span", btn).textContent;
      slot.set(btn.getAttribute("data-slug"));
      if (focus) btn.focus();
    }
    thumbs.forEach(function (b, i) {
      b.addEventListener("click", function () { pick(b, false); });
      b.addEventListener("keydown", function (e) {
        var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (!d) return;
        e.preventDefault();
        pick(thumbs[(i + d + thumbs.length) % thumbs.length], true);
      });
    });
    screen.addEventListener("pointermove", function (e) {
      var r = screen.getBoundingClientRect();
      slot.pointer((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    });
  }

  // ④ 在图标之下：壁纸从底下铺上来，图标和窗口纹丝不动；最后光标点一下图标 —— 点击照样穿得过去
  function sceneUnder() {
    var sec = $(".under"); if (!sec) return;
    var steps = all(".under-steps li", sec), icon = $(".ico", sec), st = sec.style;
    S.on(sec, function (p) {
      st.setProperty("--reveal", S.easeInOut(S.segment(p, 0.1, 0.46)).toFixed(4));
      st.setProperty("--win", S.easeInOut(S.segment(p, 0.48, 0.66)).toFixed(4));
      var c = S.easeInOut(S.segment(p, 0.66, 0.86));
      st.setProperty("--cx", S.lerp(62, 91.5, c).toFixed(2) + "%");
      st.setProperty("--cy", S.lerp(72, 16, c).toFixed(2) + "%");
      st.setProperty("--click", p > 0.88 && p < 0.92 ? "0.85" : "1");
      icon.classList.toggle("sel", p > 0.89);
      var step = p < 0.47 ? 0 : p < 0.87 ? 1 : 2;
      steps.forEach(function (li, i) { li.classList.toggle("on", i === step); });
    });
  }

  // ⑤ 三种壁纸：滑块走的是和 app 一样的属性接口（wallpaperPropertyListener），不是网页特效
  function sceneKinds() {
    var media = $("#web-live"); if (!media) return;
    var slot = Live.slot(media), inputs = all(".props input");
    inputs.forEach(function (input) {
      input.addEventListener("input", function () {
        var props = {};
        inputs.forEach(function (i) {
          props[i.getAttribute("data-prop")] = { value: parseFloat(i.value) };
          i.nextElementSibling.textContent = parseFloat(i.value).toFixed(2) + "×";
        });
        slot.apply(props);
      });
    });
    media.addEventListener("pointermove", function (e) {
      var r = media.getBoundingClientRect();
      slot.pointer((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height);
    });

    // 2.5D 示意：几张图各带景深，按鼠标位置错位 —— 分层壁纸的真实机制
    var ridges = $(".ridges"); if (!ridges || S.reduce) return;
    var layers = all("[data-depth]", ridges), tile = ridges.parentNode;
    function shift(x, y) {
      layers.forEach(function (l) {
        var d = parseFloat(l.getAttribute("data-depth"));
        l.style.transform = "translate(" + (-x * 36 * d).toFixed(1) + "px," + (-y * 14 * d).toFixed(1) + "px)";
      });
    }
    tile.addEventListener("pointermove", function (e) {
      var r = ridges.getBoundingClientRect();
      shift((e.clientX - r.left) / r.width - 0.5, (e.clientY - r.top) / r.height - 0.5);
    });
    tile.addEventListener("pointerleave", function () { shift(0, 0); });
  }

  // ⑥ 桌宠：app 里同一套精灵图，跟着光标走，点它会叫。行为照搬 app：缓动跟随、走路快坐着慢
  function scenePet() {
    var yard = $("#pet-yard"); if (!yard) return;
    var pet = $("#pet-cat"), say = $("#pet-say");
    var CELL = 168, FRAMES = { idle: 5, walk: 4, petted: 2 };
    var x = yard.clientWidth / 2, target = x, frame = 0, pose = "idle", facing = 1;
    var last = 0, pettedUntil = 0, raf = 0, sayTimer = 0;
    function place() {
      pet.style.transform = "translateX(" + x.toFixed(1) + "px) scaleX(" + facing + ")";
      pet.setAttribute("data-pose", pose);
      pet.style.backgroundPosition = (-frame * CELL) + "px 0";
      say.style.left = x.toFixed(1) + "px";
    }
    place();
    if (S.reduce) return;   // 减弱动态效果：坐着不动，不跟光标，也不播帧
    yard.addEventListener("pointermove", function (e) { target = e.clientX - yard.getBoundingClientRect().left; });
    yard.addEventListener("pointerleave", function () { target = yard.clientWidth / 2; });
    yard.addEventListener("click", function () {
      pettedUntil = performance.now() + 1600;
      say.textContent = T("js.pet.meow");
      say.classList.add("on");
      clearTimeout(sayTimer);
      sayTimer = setTimeout(function () { say.classList.remove("on"); }, 1600);
    });
    function tick(now) {
      raf = requestAnimationFrame(tick);
      var dx = target - x, moving = Math.abs(dx) > 6;
      if (now < pettedUntil) {
        pose = "petted";
      } else {
        pose = moving ? "walk" : "idle";
        if (moving) { facing = dx > 0 ? 1 : -1; x += dx * 0.055; }   // 缓动，不是瞬移
      }
      var hold = pose === "walk" ? 150 : pose === "petted" ? 260 : 420;
      if (now - last > hold) { last = now; frame = (frame + 1) % FRAMES[pose]; }
      place();
    }
    // 先跑起来，观察器只负责滚出视野时停 —— 反过来写的话观察器不触发它就永远冻着
    raf = requestAnimationFrame(tick);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es) {
        es.forEach(function (e) {
          if (e.isIntersecting && !raf) raf = requestAnimationFrame(tick);
          else if (!e.isIntersecting && raf) { cancelAnimationFrame(raf); raf = 0; }
        });
      }, { threshold: 0.05 }).observe(yard);
    }
  }

  // ⑦ 多屏：纯状态切换。拼接时按两块屏在页面上的真实位置，各取同一张画的那一块 ——
  // 和 app 把所有显示器当成一整块画布是同一个思路，所以接缝在任何宽度下都对得上
  function sceneMulti() {
    var screens = $(".screens"); if (!screens) return;
    var seg = $(".seg"), btns = all("button", seg), scrs = all(".scr", screens);
    var pill = document.createElement("span");
    pill.className = "seg-pill";
    pill.setAttribute("aria-hidden", "true");
    seg.insertBefore(pill, seg.firstChild);

    function layoutSpan() {
      var boxes = scrs.map(function (el) { return el.getBoundingClientRect(); });
      var left = Math.min.apply(null, boxes.map(function (b) { return b.left; }));
      var top = Math.min.apply(null, boxes.map(function (b) { return b.top; }));
      var right = Math.max.apply(null, boxes.map(function (b) { return b.right; }));
      var bottom = Math.max.apply(null, boxes.map(function (b) { return b.bottom; }));
      var w = right - left, h = bottom - top;
      var size = Math.max(w, h * 16 / 9);   // 海报是 16:9，按「盖满」铺
      scrs.forEach(function (el, i) {
        var span = $("i.span", el), bw = el.clientLeft;   // 扣掉边框
        span.style.backgroundSize = size.toFixed(1) + "px auto";
        span.style.backgroundPosition = px(left - boxes[i].left - bw + (w - size) / 2) + " " +
                                        px(top - boxes[i].top - bw + (h - size * 9 / 16) / 2);
      });
    }
    function movePill(btn) {
      pill.style.left = btn.offsetLeft + "px";
      pill.style.width = btn.offsetWidth + "px";
    }
    function pick(btn, focus) {
      screens.setAttribute("data-mode", btn.getAttribute("data-mode"));
      btns.forEach(function (o) {
        var on = o === btn;
        o.setAttribute("aria-checked", String(on));
        o.tabIndex = on ? 0 : -1;
      });
      movePill(btn);
      if (focus) btn.focus();
    }
    btns.forEach(function (b, i) {
      b.tabIndex = i === 0 ? 0 : -1;
      b.addEventListener("click", function () { pick(b, false); });
      b.addEventListener("keydown", function (e) {
        var d = e.key === "ArrowRight" ? 1 : e.key === "ArrowLeft" ? -1 : 0;
        if (!d) return;
        e.preventDefault();
        pick(btns[(i + d + btns.length) % btns.length], true);
      });
    });
    movePill(btns[0]);
    layoutSpan();
    window.addEventListener("resize", function () {
      layoutSpan();
      movePill($("button[aria-checked='true']", seg));
    }, { passive: true });
    // 入场动画会位移屏幕，等它结束再算一次
    setTimeout(layoutSpan, 1200);
    new IntersectionObserver(function (es) { if (es[0].isIntersecting) setTimeout(layoutSpan, 1100); })
      .observe(screens);
  }

  // ⑧ 省电：滚动推着桌面经历四种状态，帧率数字像 app 里那样一格一格滚过去
  function scenePower() {
    var sec = $(".power"); if (!sec) return;
    var n = $(".fps-n", sec), state = $(".fps-state", sec), steps = all(".power-steps li", sec), st = sec.style;
    var STAGES = [
      { until: 0.22, fps: 60, label: "js.power.playing" },
      { until: 0.5,  fps: 0,  label: "js.power.covered" },
      { until: 0.76, fps: 30, label: "js.power.lowpower" },
      { until: 2,    fps: 0,  label: "js.power.locked" }
    ];
    var shown = 60, goal = 60, timer = 0, current = -1;
    function roll() {
      if (shown === goal) { timer = 0; return; }
      var step = Math.max(1, Math.round(Math.abs(goal - shown) / 5));
      shown += shown < goal ? step : -step;
      n.textContent = String(shown);
      timer = setTimeout(roll, 45);
    }
    S.on(sec, function (p) {
      // 窗口在第二段盖上来、第三段撤走
      st.setProperty("--cover", S.easeInOut(Math.min(S.segment(p, 0.1, 0.24), 1 - S.segment(p, 0.48, 0.58))).toFixed(4));
      st.setProperty("--dim", S.segment(p, 0.52, 0.6).toFixed(4));
      st.setProperty("--lock", S.easeOut(S.segment(p, 0.76, 0.86)).toFixed(4));
      var i = 0;
      while (p > STAGES[i].until) i++;
      if (i === current) return;
      current = i;
      steps.forEach(function (li, k) { li.classList.toggle("on", k === i); });
      state.textContent = T(STAGES[i].label);
      goal = STAGES[i].fps;
      if (S.reduce) { shown = goal; n.textContent = String(goal); }
      else if (!timer) roll();
    });
  }

  // ⑨ 快捷键：在页面上按组合键，键帽跟着按下去。不拦截按键 —— ⌥⌘→ 在有的浏览器里是切标签页
  function sceneKeys() {
    var keys = all("kbd[data-k]"); if (!keys.length) return;
    function set(name, down) {
      var k = String(name).toLowerCase();
      keys.forEach(function (el) { if (el.getAttribute("data-k").toLowerCase() === k) el.classList.toggle("down", down); });
    }
    function releaseAll() { keys.forEach(function (el) { el.classList.remove("down"); }); }
    document.addEventListener("keydown", function (e) {
      // ⌥ 按住时 e.key 会变成特殊字符（⌥P = π），按物理键位认
      var name = e.code && e.code.indexOf("Key") === 0 ? e.code.slice(3) : e.key;
      set(name, true);
    });
    document.addEventListener("keyup", function (e) {
      var name = e.code && e.code.indexOf("Key") === 0 ? e.code.slice(3) : e.key;
      set(name, false);
      if (e.key === "Meta") releaseAll();   // ⌘ 按住时其它键的 keyup 浏览器不发，松 ⌘ 时一起弹起
    });
    window.addEventListener("blur", releaseAll);
    keys.forEach(function (el) {
      el.addEventListener("pointerdown", function () { el.classList.add("down"); });
      el.addEventListener("pointerup", function () { el.classList.remove("down"); });
      el.addEventListener("pointerleave", function () { el.classList.remove("down"); });
    });
  }

  sceneHero();
  sceneStatement();
  sceneGallery();
  sceneUnder();
  sceneKinds();
  scenePet();
  sceneMulti();
  scenePower();
  sceneKeys();
})();
