// node --test site/tools/test_scenes.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const S = createRequire(import.meta.url)("../assets/scenes.js");
const near = (a, b) => assert.ok(Math.abs(a - b) < 1e-9, `${a} ≉ ${b}`);

test("钉住区块：顶边到视口顶是 0，底边到视口底是 1", () => {
  // 外层 3000 高、视口 1000：可滚动行程 2000
  assert.equal(S.pinnedProgress(0, 3000, 1000), 0);
  assert.equal(S.pinnedProgress(-1000, 3000, 1000), 0.5);
  assert.equal(S.pinnedProgress(-2000, 3000, 1000), 1);
  assert.equal(S.pinnedProgress(500, 3000, 1000), 0, "还没到");
  assert.equal(S.pinnedProgress(-2600, 3000, 1000), 1, "已经过去");
});

test("比视口还矮的钉住区块不除以零", () => {
  assert.equal(S.pinnedProgress(10, 800, 1000), 0);
  assert.equal(S.pinnedProgress(-10, 800, 1000), 1);
});

test("经过型区块：从视口底进入到从视口顶离开", () => {
  assert.equal(S.passProgress(1000, 500, 1000), 0);
  assert.equal(S.passProgress(-500, 500, 1000), 1);
  assert.equal(S.passProgress(250, 500, 1000), 0.5);
});

test("segment 把一段进度映射到 0..1 并夹住", () => {
  assert.equal(S.segment(0.1, 0.2, 0.6), 0);
  near(S.segment(0.4, 0.2, 0.6), 0.5);
  assert.equal(S.segment(0.9, 0.2, 0.6), 1);
  assert.equal(S.segment(0.5, 0.5, 0.5), 1, "零长度的段：到了就是 1");
});

test("缓动端点不越界", () => {
  for (const f of [S.easeOut, S.easeInOut]) {
    assert.equal(f(0), 0);
    assert.equal(f(1), 1);
    assert.ok(f(0.5) > 0 && f(0.5) < 1);
  }
  assert.equal(S.lerp(10, 20, 0.25), 12.5);
});
