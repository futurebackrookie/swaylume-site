/* Every interaction has a visible result; the desktop UI is a labelled web demo. */
(function () {
  "use strict";
  var reduced = window.Scenes && Scenes.reduce, strings = window.__I18N || {};
  function T(k) { return strings[k] || k; }
  function $(s, r) { return (r || document).querySelector(s); }
  function all(s, r) { return Array.from((r || document).querySelectorAll(s)); }
  function clamp(n, min, max) { return Math.max(min, Math.min(max, n)); }
  function px(n) { return n.toFixed(1) + "px"; }
  function radioGroup(buttons, pick) {
    buttons.forEach(function (button, i) {
      button.tabIndex = button.getAttribute("aria-checked") === "true" ? 0 : -1;
      button.addEventListener("click", function () { select(i, false); });
      button.addEventListener("keydown", function (e) {
        var next = e.key === "ArrowRight" || e.key === "ArrowDown" ? i + 1 : e.key === "ArrowLeft" || e.key === "ArrowUp" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? buttons.length - 1 : null;
        if (next === null) return;
        e.preventDefault(); select((next + buttons.length) % buttons.length, true);
      });
    });
    function select(i, focus) {
      buttons.forEach(function (b, k) { b.setAttribute("aria-checked", String(i === k)); b.tabIndex = i === k ? 0 : -1; });
      pick(buttons[i], i); if (focus) buttons[i].focus();
    }
  }
  function hero() {
    var el = $(".hero"), time = $("#world-time"), launch = $("#world-launch"), layers = all("[data-world-depth]");
    if (!el) return;
    time.addEventListener("click", function () {
      var night = el.classList.toggle("night");
      time.setAttribute("aria-pressed", String(night));
      time.lastElementChild.textContent = T(night ? "js.world.day" : "js.world.night");
      $(".time-symbol", time).textContent = night ? "☾" : "☼";
    });
    var launchTimer, launchRAF = 0;
    launch.addEventListener("click", function () {
      // Replaying is an explicit request to revisit this scene, even when only its bottom is visible.
      window.scrollTo({ top: 0, left: 0, behavior: "instant" });
      clearTimeout(launchTimer); cancelAnimationFrame(launchRAF);
      el.classList.remove("launching"); void el.offsetWidth;
      el.classList.add("launching");
      if (!reduced) {
        var aperture = $("#launch-aperture"), begin = performance.now(), width = el.clientWidth, height = el.clientHeight;
        var iconOffset = (12 + $(".launch-curtain span").offsetHeight) / 2;
        function open(now) {
          var t = clamp((now - begin - 650) / 1150, 0, 1), ease = 1 - Math.pow(1 - t, 4);
          var w = now - begin < 650 ? 0 : 116 + (width * 1.08 - 116) * ease;
          var h = now - begin < 650 ? 0 : 116 + (height * 1.08 - 116) * ease;
          aperture.setAttribute("x", (width - w) / 2); aperture.setAttribute("y", (height - h) / 2 - iconOffset * (1 - ease));
          aperture.setAttribute("width", w); aperture.setAttribute("height", h); aperture.setAttribute("rx", 27 * (1 - ease));
          if (t < 1) launchRAF = requestAnimationFrame(open);
        }
        open(begin);
      }
      launchTimer = setTimeout(function () { el.classList.remove("launching"); }, reduced ? 180 : 1900);
    });
    if (reduced) return;
    var pointerRAF = 0, nx = 0, ny = 0;
    function paint() {
      pointerRAF = 0;
      layers.forEach(function (layer) { var depth = Number(layer.dataset.worldDepth); layer.style.transform = "translate(" + px(nx * depth) + "," + px(ny * depth * .55) + ")"; });
    }
    el.addEventListener("pointermove", function (e) {
      if (e.pointerType === "touch") return;
      var r = el.getBoundingClientRect(); nx = (e.clientX - r.left) / r.width - .5; ny = (e.clientY - r.top) / r.height - .5;
      if (!pointerRAF) pointerRAF = requestAnimationFrame(paint);
    }, { passive: true });
    el.addEventListener("pointerleave", function () { nx = ny = 0; if (!pointerRAF) pointerRAF = requestAnimationFrame(paint); });
    all(".magnetic").forEach(function (button) {
      button.addEventListener("pointermove", function (e) {
        if (e.pointerType === "touch") return;
        var r = button.getBoundingClientRect(); button.style.translate = px((e.clientX - r.left - r.width / 2) * .12) + " " + px((e.clientY - r.top - r.height / 2) * .2);
      });
      button.addEventListener("pointerleave", function () { button.style.translate = "0 0"; });
    });
  }
  function gallery() {
    var screen = $("#gallery-live"); if (!screen) return;
    var slot = Live.slot(screen), thumbs = all(".thumb"), inputs = all(".props input", screen), pause = $("#preview-pause");
    radioGroup(thumbs, function (button, i) {
      // Exclude its ordinal from the accessible wallpaper name.
      var name = $("span", button).lastChild.textContent.trim();
      $(".poster", screen).alt = name; $("#wallpaper-name").textContent = name;
      $("#wallpaper-number").textContent = String(i + 1).padStart(2, "0") + " / 06";
      slot.set(button.dataset.slug);
    });
    function apply() {
      var props = {};
      inputs.forEach(function (input) {
        props[input.dataset.prop] = { value: Number(input.value) };
        input.nextElementSibling.textContent = Number(input.value).toFixed(2) + "×";
        input.style.setProperty("--range-fill", ((input.value - input.min) / (input.max - input.min) * 100) + "%");
      });
      slot.apply(props);
    }
    inputs.forEach(function (input) { input.addEventListener("input", apply); }); apply();
    pause.addEventListener("click", function () {
      var paused = pause.getAttribute("aria-pressed") !== "true";
      pause.setAttribute("aria-pressed", String(paused)); pause.setAttribute("aria-label", T(paused ? "js.preview.resume" : "js.preview.pause"));
      slot.pause(paused);
    });
    screen.addEventListener("pointermove", function (e) { var r = screen.getBoundingClientRect(); slot.pointer((e.clientX - r.left) / r.width, (e.clientY - r.top) / r.height); }, { passive: true });
    var expand = $("#preview-expand"), dialog = document.createElement("dialog"), placeholder = document.createElement("div");
    dialog.className = "preview-dialog"; dialog.setAttribute("aria-label", T("js.preview.immersive"));
    document.body.appendChild(dialog);
    expand.addEventListener("click", function () {
      if (dialog.open) { dialog.close(); return; }
      placeholder.style.height = screen.offsetHeight + "px"; screen.before(placeholder);
      dialog.appendChild(screen); document.body.classList.add("demo-immersive");
      expand.setAttribute("aria-label", T("js.preview.exit")); dialog.showModal(); expand.focus();
    });
    dialog.addEventListener("close", function () {
      placeholder.replaceWith(screen); document.body.classList.remove("demo-immersive");
      expand.setAttribute("aria-label", T("js.preview.immersive")); expand.focus({ preventScroll: true });
    });
    var folder = $("#demo-folder"), win = $(".demo-window"), grip = $(".window-grip"), close = $(".window-close");
    folder.setAttribute("aria-expanded", "false");
    function hide() { win.hidden = true; folder.setAttribute("aria-expanded", "false"); folder.focus({ preventScroll: true }); }
    function fitWindow() {
      if (win.hidden) return;
      win.style.left = px(clamp(win.offsetLeft, 0, screen.clientWidth - win.offsetWidth));
      win.style.top = px(clamp(win.offsetTop, 0, screen.clientHeight - win.offsetHeight));
    }
    folder.addEventListener("click", function () { win.hidden = false; fitWindow(); folder.setAttribute("aria-expanded", "true"); close.focus({ preventScroll: true }); });
    close.addEventListener("click", hide);
    win.addEventListener("keydown", function (e) { if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); hide(); } });
    if (window.ResizeObserver) new ResizeObserver(fitWindow).observe(screen);
    grip.addEventListener("keydown", function (e) {
      if (e.target !== grip) return;
      var dx = e.key === "ArrowLeft" ? -16 : e.key === "ArrowRight" ? 16 : 0;
      var dy = e.key === "ArrowUp" ? -16 : e.key === "ArrowDown" ? 16 : 0;
      if (dx || dy) {
        e.preventDefault(); win.style.left = px(win.offsetLeft + dx); win.style.top = px(win.offsetTop + dy); fitWindow();
      }
    });
    var drag = null;
    grip.addEventListener("pointerdown", function (e) {
      if (e.target.closest("button") || e.button !== 0) return;
      var box = win.getBoundingClientRect(), bounds = screen.getBoundingClientRect();
      drag = { x: e.clientX, y: e.clientY, left: box.left - bounds.left, top: box.top - bounds.top };
      grip.setPointerCapture(e.pointerId);
    });
    grip.addEventListener("pointermove", function (e) {
      if (!drag) return;
      win.style.left = px(clamp(drag.left + e.clientX - drag.x, 0, screen.clientWidth - win.offsetWidth));
      win.style.top = px(clamp(drag.top + e.clientY - drag.y, 0, screen.clientHeight - win.offsetHeight));
    });
    function end() { drag = null; }
    grip.addEventListener("pointerup", end); grip.addEventListener("pointercancel", end); grip.addEventListener("lostpointercapture", end);
  }
  function multi() {
    var screens = $(".screens"); if (!screens) return;
    var buttons = all(".seg button"), displays = all(".scr", screens), movable = $(".scr-std"), handle = $(".screen-handle"), seg = $(".seg");
    var pill = document.createElement("span"); pill.className = "seg-pill"; pill.setAttribute("aria-hidden", "true"); seg.prepend(pill);
    var x = 0, y = 0, drag = null;
    function layout() {
      var boxes = displays.map(function (d) { return d.getBoundingClientRect(); });
      var left = Math.min.apply(null, boxes.map(function (r) { return r.left; })), top = Math.min.apply(null, boxes.map(function (r) { return r.top; }));
      var w = Math.max.apply(null, boxes.map(function (r) { return r.right; })) - left, h = Math.max.apply(null, boxes.map(function (r) { return r.bottom; })) - top;
      var size = Math.max(w, h * 16 / 9);
      displays.forEach(function (d, i) {
        var layer = $("i.span", d);
        layer.style.backgroundSize = px(size) + " auto";
        layer.style.backgroundPosition = px(left - boxes[i].left - d.clientLeft + (w - size) / 2) + " " + px(top - boxes[i].top - d.clientTop + (h - size * 9 / 16) / 2);
      });
      var selected = $(".seg button[aria-checked='true']"); pill.style.left = px(selected.offsetLeft); pill.style.width = px(selected.offsetWidth);
    }
    radioGroup(buttons, function (button) { screens.dataset.mode = button.dataset.mode; layout(); });
    function position(nx, ny) {
      x = clamp(nx, -Math.min(100, screens.clientWidth * .2), 16); y = clamp(ny, -64, 64);
      movable.style.transform = "translate(" + px(x) + "," + px(y) + ")"; layout();
    }
    handle.addEventListener("pointerdown", function (e) {
      if (e.button !== 0) return;
      drag = { clientX: e.clientX, clientY: e.clientY, x: x, y: y };
      movable.classList.add("dragging"); handle.setPointerCapture(e.pointerId);
    });
    handle.addEventListener("pointermove", function (e) { if (drag) position(drag.x + e.clientX - drag.clientX, drag.y + e.clientY - drag.clientY); });
    function end() { drag = null; movable.classList.remove("dragging"); }
    handle.addEventListener("pointerup", end); handle.addEventListener("pointercancel", end); handle.addEventListener("lostpointercapture", end);
    handle.addEventListener("keydown", function (e) {
      var dx = e.key === "ArrowLeft" ? -12 : e.key === "ArrowRight" ? 12 : 0, dy = e.key === "ArrowUp" ? -12 : e.key === "ArrowDown" ? 12 : 0;
      if (dx || dy) { e.preventDefault(); movable.classList.add("dragging"); position(x + dx, y + dy); end(); }
      if (e.key === "Home") { e.preventDefault(); movable.classList.add("dragging"); position(0, 0); end(); }
    });
    // Calculate at the rendered position, including a responsive resize.
    if (window.ResizeObserver) new ResizeObserver(layout).observe(screens);
    window.addEventListener("resize", function () { movable.classList.add("dragging"); position(0, 0); end(); }, { passive: true });
    layout();
  }
  function power() {
    var stage = $(".power-stage"); if (!stage) return;
    var slot = Live.slot($("#power-live")), number = $(".fps-n"), label = $(".fps-state"), chart = $(".power-chart"), buttons = all("[data-power]");
    var states = { playing: { fps: 60, label: "js.power.playing" }, covered: { fps: 0, label: "js.power.covered" }, lowpower: { fps: 24, label: "js.power.lowpower" }, locked: { fps: 0, label: "js.power.locked" } };
    var drawn = 60, numberRAF = 0;
    for (var i = 0; i < 42; i++) { var bar = document.createElement("i"); bar.style.setProperty("--h", (25 + (Math.sin(i * .7) + 1) * 30) + "%"); chart.appendChild(bar); }
    function pick(key) {
      var state = states[key]; stage.dataset.state = key;
      $(".power-cover", stage).setAttribute("aria-hidden", String(key !== "covered"));
      buttons.forEach(function (button) { button.setAttribute("aria-pressed", String(button.dataset.power === key)); });
      slot.fps(state.fps); slot.pause(state.fps === 0); slot.apply({ speed: { value: key === "lowpower" ? .4 : 1 } });
      label.textContent = T(state.label);
      cancelAnimationFrame(numberRAF);
      var from = drawn, start = performance.now();
      function roll(now) {
        var t = reduced ? 1 : clamp((now - start) / 600, 0, 1);
        drawn = Math.round(from + (state.fps - from) * (1 - Math.pow(1 - t, 3))); number.textContent = drawn;
        if (t < 1) numberRAF = requestAnimationFrame(roll);
      }
      numberRAF = requestAnimationFrame(roll);
    }
    buttons.forEach(function (button) { button.addEventListener("click", function () { pick(button.dataset.power); }); });
    slot.fps(60);
  }
  function pet() {
    var yard = $("#pet-yard"), cat = $("#pet-cat"), say = $("#pet-say"), call = $("#pet-call"); if (!yard) return;
    var x = yard.clientWidth / 2, target = x, frame = 0, pose = "idle", facing = 1, last = 0, previous = 0, pettedUntil = 0, raf = 0, visible = false, sayTimer;
    var frames = { idle: 5, walk: 4, petted: 2 };
    function place() { cat.style.transform = "translateX(" + px(x) + ") scaleX(" + facing + ")"; cat.dataset.pose = pose; cat.style.backgroundPosition = (-frame * 168) + "px 0"; say.style.left = px(x); }
    function bounded(value) { return clamp(value, 84, Math.max(84, yard.clientWidth - 84)); }
    function tick(now) {
      var dt = Math.min(40, previous ? now - previous : 16); previous = now;
      var dx = target - x, next = now < pettedUntil ? "petted" : Math.abs(dx) > 4 ? "walk" : "idle";
      if (next !== pose) { pose = next; frame = 0; last = now; }
      if (pose === "walk") { facing = dx > 0 ? 1 : -1; x += dx * (1 - Math.exp(-dt / 210)); }
      var hold = pose === "walk" ? 150 : pose === "petted" ? 260 : 420;
      if (now - last >= hold) { last = now; frame = (frame + 1) % frames[pose]; }
      place(); raf = requestAnimationFrame(tick);
    }
    function schedule() {
      if (visible && !document.hidden && !reduced) { if (!raf) { previous = 0; raf = requestAnimationFrame(tick); } }
      else if (raf) { cancelAnimationFrame(raf); raf = 0; }
    }
    function meow() {
      pettedUntil = performance.now() + 1600; say.textContent = T("js.pet.meow"); say.classList.add("on");
      if (reduced) { pose = "petted"; frame = 0; place(); }
      clearTimeout(sayTimer); sayTimer = setTimeout(function () { say.classList.remove("on"); if (reduced) { pose = "idle"; place(); } }, 1600);
    }
    cat.addEventListener("click", meow);
    call.addEventListener("click", function () { target = bounded(yard.clientWidth * .38); if (reduced) { x = target; place(); } meow(); });
    yard.addEventListener("pointermove", function (e) { if (!reduced) target = bounded(e.clientX - yard.getBoundingClientRect().left); }, { passive: true });
    yard.addEventListener("pointerleave", function () { target = bounded(yard.clientWidth / 2); });
    document.addEventListener("visibilitychange", schedule);
    if ("IntersectionObserver" in window) new IntersectionObserver(function (entries) { visible = entries[0].isIntersecting; schedule(); }, { threshold: .05 }).observe(yard);
    else { visible = true; schedule(); }
    if (window.ResizeObserver) new ResizeObserver(function () { target = x = bounded(yard.clientWidth / 2); place(); }).observe(yard);
    place();
  }
  function keys() {
    var caps = all("kbd[data-k]");
    function release() { caps.forEach(function (c) { c.classList.remove("down"); }); }
    document.addEventListener("keydown", function (e) { var key = e.code.startsWith("Key") ? e.code.slice(3) : e.key; caps.forEach(function (c) { if (c.dataset.k.toLowerCase() === key.toLowerCase()) c.classList.add("down"); }); });
    document.addEventListener("keyup", function (e) { var key = e.code.startsWith("Key") ? e.code.slice(3) : e.key; caps.forEach(function (c) { if (c.dataset.k.toLowerCase() === key.toLowerCase()) c.classList.remove("down"); }); if (e.key === "Meta") release(); });
    window.addEventListener("blur", release);
  }
  hero(); gallery(); multi(); power(); pet(); keys();
})();
