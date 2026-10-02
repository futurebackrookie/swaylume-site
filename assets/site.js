/* 全站：滚动引擎启动、导航深浅、语言菜单收起。首页专属的在 home.js。 */
(function () {
  "use strict";
  Scenes.collect();
  Scenes.start();

  // 导航压在哪个区块上，就用哪个区块的深浅。观察的是视口顶上导航那一条
  var nav = document.querySelector(".nav");
  var themed = document.querySelectorAll("main [data-theme]");
  // 文档页没有深浅交替的区块，整页是白纸：导航用浅色
  if (nav && !themed.length) nav.setAttribute("data-theme", "light");
  if (nav && themed.length && "IntersectionObserver" in window) {
    var io;
    var watch = function () {
      if (io) io.disconnect();
      io = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) nav.setAttribute("data-theme", e.target.getAttribute("data-theme"));
        });
      }, { rootMargin: "-26px 0px " + (26 - window.innerHeight) + "px 0px" });
      for (var i = 0; i < themed.length; i++) io.observe(themed[i]);
    };
    watch();
    window.addEventListener("resize", watch, { passive: true });
  }

  // 技术细节页的频谱装饰：几十根柱子各自起伏，纯 CSS 动画，不跑脚本循环
  var spectrum = document.getElementById("spectrum");
  if (spectrum && !spectrum.children.length) {
    for (var b = 0; b < 48; b++) {
      var bar = document.createElement("i");
      // 低频高、高频低，像真实的音乐频谱
      var h = 30 + 60 * Math.pow(1 - b / 48, 1.4) * (0.6 + 0.4 * Math.random());
      bar.style.setProperty("--h", h.toFixed(0) + "%");
      bar.style.animationDelay = (-Math.random() * 1.2).toFixed(2) + "s";
      bar.style.animationDuration = (0.5 + Math.random() * 0.9).toFixed(2) + "s";
      spectrum.appendChild(bar);
    }
  }

  // 语言菜单（<details>）：点外面、按 Esc 收起。坏了也只是关不掉，不会打不开。
  function closeLang(except) {
    document.querySelectorAll("details.langs[open]").forEach(function (d) {
      if (d !== except) d.removeAttribute("open");
    });
  }
  document.addEventListener("click", function (e) {
    var inside = e.target.closest && e.target.closest("details.langs");
    closeLang(inside);
  });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") closeLang(null); });
})();
