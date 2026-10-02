/* 实时壁纸。页面上有好几个位置想跑壁纸（开场、画廊、便当格），
   但同一时刻只挂一个 iframe：谁在视口里露得最多就是谁，其余显示海报。
   滚出视口、标签页切走就卸载 —— 页面自己守它宣传的省电规矩。
   减弱动态效果时一个都不挂，只看海报。 */
(function () {
  "use strict";
  var SITE = document.documentElement.getAttribute("data-site") || "";
  var FADE = 800;   // 与 app 换壁纸的交叉淡入同长
  var slots = [], active = null;
  window.__liveCount = 0;

  function count() { window.__liveCount = document.querySelectorAll("iframe.live").length; }

  function frameWindow(slot) {
    try { return slot.frame && slot.frame.contentWindow; } catch (e) { return null; }
  }

  function pushProps(slot) {
    var w = frameWindow(slot);
    try {
      if (w && slot.props && w.wallpaperPropertyListener) w.wallpaperPropertyListener.applyUserProperties(slot.props);
    } catch (e) { /* 拿不到就算了，画面照常 */ }
  }

  // 新的 iframe 叠在旧的上面，首帧画出来以后淡入，淡完再拆旧的
  function makeFrame(slot, slug) {
    var f = document.createElement("iframe");
    f.className = "live";
    f.setAttribute("aria-hidden", "true");
    f.setAttribute("tabindex", "-1");
    f.title = "";
    f.addEventListener("load", function () {
      if (slot.frame !== f) return;           // 等它加载的工夫里又换了一张
      pushProps(slot);
      // 再等两帧：WebGL 首帧没画出来之前是黑的，直接显形会闪一下
      requestAnimationFrame(function () { requestAnimationFrame(function () {
        if (slot.frame !== f) return;
        f.classList.add("on");
        setTimeout(function () {
          Array.prototype.forEach.call(slot.el.querySelectorAll("iframe.live"), function (o) {
            if (o !== slot.frame) o.remove();
          });
          count();
        }, FADE + 40);
      }); });
    });
    f.src = SITE + "/wallpapers/" + slug + "/index.html";
    slot.el.appendChild(f);
    slot.frame = f;
    count();
  }

  function mount(slot) {
    if (window.Scenes && Scenes.reduce) return;
    if (document.hidden || slot.frame) return;
    makeFrame(slot, slot.slug);
  }
  function unmount(slot) {
    Array.prototype.forEach.call(slot.el.querySelectorAll("iframe.live"), function (f) { f.remove(); });
    slot.frame = null;
    count();
  }

  function choose() {
    var best = null;
    slots.forEach(function (s) { if (s.ratio > 0.15 && (!best || s.ratio > best.ratio)) best = s; });
    if (best !== active && active) unmount(active);
    active = best;
    if (active) mount(active);
  }

  var io = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
    entries.forEach(function (e) {
      slots.forEach(function (s) { if (s.el === e.target) s.ratio = e.isIntersecting ? e.intersectionRatio : 0; });
    });
    choose();
  }, { threshold: [0, 0.15, 0.3, 0.45, 0.6, 0.75, 0.9, 1] }) : null;

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) slots.forEach(unmount); else choose();
  });

  window.Live = {
    slot: function (el) {
      var slot = { el: el, slug: el.getAttribute("data-live"), ratio: 0, frame: null, props: null };
      slots.push(slot);
      if (io) io.observe(el);
      return {
        set: function (slug) {
          if (slug === slot.slug) return;
          slot.slug = slug;
          var poster = el.querySelector(".poster");
          if (poster) poster.src = SITE + "/posters/" + slug + ".jpg";
          if (slot.frame) makeFrame(slot, slug);
        },
        // 和 app 一样走壁纸自己声明的属性接口
        apply: function (props) { slot.props = props; pushProps(slot); },
        // 鼠标视差：和 app 一样，宿主合成 mousemove 派发进去（0–1 归一化坐标）
        pointer: function (x01, y01) {
          var w = frameWindow(slot);
          if (!w) return;
          try {
            w.dispatchEvent(new MouseEvent("mousemove", { clientX: x01 * w.innerWidth, clientY: y01 * w.innerHeight }));
          } catch (e) {}
        }
      };
    }
  };
})();
