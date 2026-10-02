/* 滚动引擎。把每个场景的滚动进度（0–1）写进它的 CSS 变量 --p，
   复杂一点的效果用 Scenes.on(el, fn) 拿到进度自己算。
   只有在视口附近的场景才计算；页面不滚就一帧都不算。 */
(function (root) {
  "use strict";

  function clamp(v, a, b) { return v < a ? a : v > b ? b : v; }
  // 外层顶边到达视口顶边 = 0，外层底边到达视口底边 = 1（中间这段内层是粘住的）
  function pinnedProgress(top, height, viewport) {
    var travel = height - viewport;
    if (travel <= 0) return top <= 0 ? 1 : 0;
    return clamp((0 - top) / travel, 0, 1);   // 不写 -top：top 为 0 时得到 -0
  }
  // 顶边从视口底部进来 = 0，底边从视口顶部出去 = 1
  function passProgress(top, height, viewport) {
    return clamp((viewport - top) / (viewport + height), 0, 1);
  }
  // 把总进度里 [a, b] 这一段映射成 0–1
  function segment(p, a, b) {
    if (b <= a) return p >= b ? 1 : 0;
    return clamp((p - a) / (b - a), 0, 1);
  }
  function lerp(a, b, t) { return a + (b - a) * t; }
  function easeOut(t) { return 1 - Math.pow(1 - t, 3); }
  function easeInOut(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }

  var api = { clamp: clamp, pinnedProgress: pinnedProgress, passProgress: passProgress,
              segment: segment, lerp: lerp, easeOut: easeOut, easeInOut: easeInOut };
  if (typeof module === "object" && module.exports) module.exports = api;
  if (typeof window === "undefined") return;

  var doc = document.documentElement;
  // ?reduce 强制走减弱动态效果那条路，方便验证（系统开关不好在浏览器里切）
  var reduce = /[?&]reduce\b/.test(location.search) ||
               !!(window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches);
  doc.classList.add("js");
  if (reduce) doc.classList.add("reduce");
  api.reduce = reduce;

  var scenes = [];
  function find(el) {
    for (var i = 0; i < scenes.length; i++) if (scenes[i].el === el) return scenes[i];
    return null;
  }

  // 订阅某个场景的进度。减弱动态效果时只回调一次：直接给最终状态。
  api.on = function (el, fn) {
    var s = find(el);
    if (!s) return;
    s.handlers.push(fn);
    fn(reduce ? 1 : s.p);
  };

  function measure(s) {
    var r = s.el.getBoundingClientRect(), vh = window.innerHeight;
    var p = s.mode === "pin" ? pinnedProgress(r.top, r.height, vh) : passProgress(r.top, r.height, vh);
    if (s.drawn && Math.abs(p - s.p) < 0.0005) return;
    s.p = p;
    s.drawn = true;
    s.el.style.setProperty("--p", p.toFixed(4));
    for (var i = 0; i < s.handlers.length; i++) s.handlers[i](p);
  }

  var queued = false;
  function frame() {
    queued = false;
    for (var i = 0; i < scenes.length; i++) if (scenes[i].near) measure(scenes[i]);
  }
  function request() {
    if (!queued) { queued = true; requestAnimationFrame(frame); }
  }

  function collect() {
    var els = document.querySelectorAll("[data-scene]");
    for (var i = 0; i < els.length; i++) {
      scenes.push({ el: els[i], mode: els[i].getAttribute("data-scene"),
                    handlers: [], p: 0, near: false, drawn: false });
    }
  }

  function watch() {
    if (reduce) {
      // 减弱动态效果：一律直接给最终状态，不挂任何监听
      scenes.forEach(function (s) { s.p = 1; s.el.style.setProperty("--p", "1"); });
      return;
    }
    if (!("IntersectionObserver" in window)) {
      scenes.forEach(function (s) { s.near = true; });
    } else {
      // 上下各多看半屏：进场前就算好，不会进来时先跳一下
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) { var s = find(e.target); if (s) s.near = e.isIntersecting; });
        request();
      }, { rootMargin: "50% 0px 50% 0px" });
      scenes.forEach(function (s) { io.observe(s.el); });
    }
    window.addEventListener("scroll", request, { passive: true });
    window.addEventListener("resize", function () {
      scenes.forEach(function (s) { s.drawn = false; });   // 尺寸变了，同样的进度也要重算一遍
      request();
    }, { passive: true });
    request();
  }

  // 只进场一次的元素：进视口加 .in。初始隐藏态只写在 .js .reveal 上 —— 脚本挂了内容照样在。
  function reveal() {
    var els = document.querySelectorAll(".reveal, .rise");   // .rise 是文档页的旧标记，同一回事
    if (reduce || !("IntersectionObserver" in window)) {
      for (var i = 0; i < els.length; i++) els[i].classList.add("in");
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      });
    }, { rootMargin: "0px 0px -12% 0px" });
    for (var j = 0; j < els.length; j++) io.observe(els[j]);
    // 兜底：观察器要靠渲染帧回调，窗口在后台、被嵌在别处时可能一直不来 ——
    // 那样首屏内容就永远是透明的。过一会儿还没进场、但人已经看得见的，直接放出来。
    setTimeout(function () {
      for (var k = 0; k < els.length; k++) {
        var r = els[k].getBoundingClientRect();
        if (r.top < window.innerHeight && r.bottom > 0) els[k].classList.add("in");
      }
    }, 1200);
  }

  // 场景在 DOM 就绪时收集，监听在各幕的 on() 都挂好之后再开（site.js 末尾调 start）
  api.collect = collect;
  api.start = function () { watch(); reveal(); };
  root.Scenes = api;
})(this);
