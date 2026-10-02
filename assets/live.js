/* At most one visible renderer, or two during its crossfade. Leaving the viewport,
   pausing, reduced motion and a hidden tab all release the WebGL context. */
(function () {
  "use strict";
  var SITE = document.documentElement.getAttribute("data-site") || "";
  var slots = [], active = null, FADE = 800;
  function count() { window.__liveCount = document.querySelectorAll("iframe.live").length; }
  function pushProps(slot) {
    try {
      var w = slot.frame && slot.frame.contentWindow;
      if (w && w.wallpaperPropertyListener && slot.props) w.wallpaperPropertyListener.applyUserProperties(slot.props);
    } catch (_) { /* Poster remains available when a renderer cannot load. */ }
  }
  function unmount(slot) {
    clearTimeout(slot.cleanup);
    slot.el.querySelectorAll("iframe.live").forEach(function (f) { f.remove(); });
    slot.frame = null;
    count();
  }
  function makeFrame(slot) {
    clearTimeout(slot.cleanup);
    // Rapid selection keeps the last painted frame, never a queue of hidden renderers.
    var painted = Array.from(slot.el.querySelectorAll("iframe.live.on")).pop();
    slot.el.querySelectorAll("iframe.live").forEach(function (f) { if (f !== painted) f.remove(); });
    var f = document.createElement("iframe");
    f.className = "live";
    f.setAttribute("aria-hidden", "true"); f.tabIndex = -1; f.title = "";
    f.addEventListener("load", function () {
      if (slot.frame !== f) return;
      pushProps(slot);
      // The bundled wallpapers have one RAF loop. Throttle its callbacks for the
      // governor demo, so the 24 FPS mode changes rendering, not only its counter.
      try {
        var w = f.contentWindow, nativeRAF = w.requestAnimationFrame.bind(w), last = -Infinity;
        w.requestAnimationFrame = function (callback) {
          return nativeRAF(function tick(now) {
            if (!slot.fps || now - last >= 1000 / slot.fps - 0.5) { last = now; callback(now); }
            else nativeRAF(tick);
          });
        };
      } catch (_) {}
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        if (slot.frame !== f || slot.paused || document.hidden) return;
        f.classList.add("on");
        slot.cleanup = setTimeout(function () {
          if (slot.frame !== f) return;
          slot.el.querySelectorAll("iframe.live").forEach(function (old) { if (old !== f) old.remove(); });
          count();
        }, FADE + 40);
      }); });
    });
    f.src = SITE + "/wallpapers/" + slot.slug + "/index.html";
    slot.frame = f; slot.el.appendChild(f); count();
  }
  function mount(slot) {
    if ((window.Scenes && Scenes.reduce) || document.hidden || slot.paused || slot.frame) return;
    makeFrame(slot);
  }
  function choose() {
    var best = null;
    slots.forEach(function (s) { if (!s.paused && s.ratio > 0.15 && (!best || s.ratio > best.ratio)) best = s; });
    if (active && best !== active) unmount(active);
    active = best;
    if (active) mount(active);
  }
  var io = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) { slots.forEach(function (s) { if (s.el === e.target) s.ratio = e.isIntersecting ? e.intersectionRatio : 0; }); });
    choose();
  }, { threshold: [0, .15, .3, .45, .6, .75, .9, 1] }) : null;
  document.addEventListener("visibilitychange", function () {
    if (document.hidden) slots.forEach(unmount); else choose();
  });
  window.Live = {
    slot: function (el) {
      var slot = { el: el, slug: el.dataset.live, ratio: 0, frame: null, props: null, paused: false, fps: 0, cleanup: 0 };
      slots.push(slot);
      if (io) io.observe(el);
      else { slot.ratio = 1; choose(); }
      return {
        set: function (slug) {
          if (slug === slot.slug) return;
          slot.slug = slug; el.dataset.live = slug;
          var poster = el.querySelector(".poster");
          if (poster) poster.src = SITE + "/posters/" + slug + ".jpg";
          if (slot.frame) makeFrame(slot);
        },
        apply: function (props) { slot.props = props; pushProps(slot); },
        pause: function (paused) { slot.paused = paused; el.classList.toggle("paused", paused); if (paused) unmount(slot); choose(); },
        fps: function (value) { slot.fps = value; },
        pointer: function (x, y) {
          try {
            var w = slot.frame && slot.frame.contentWindow;
            if (w) w.dispatchEvent(new w.MouseEvent("mousemove", { clientX: x * w.innerWidth, clientY: y * w.innerHeight }));
          } catch (_) {}
        }
      };
    }
  };
  count();
})();
