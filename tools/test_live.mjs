/* Exercise the real renderer lifecycle without loading a WebGL engine in Node. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
const source = readFileSync(new URL('../assets/live.js', import.meta.url), 'utf8');
function harness(reduce = false) {
  const slots = [], events = {}, raf = [], timers = new Map();
  let io, nextTimer = 0;
  function query(selector, children) {
    return children.filter(f => !f.removed && f.classList.contains('live') && (!selector.endsWith('.on') || f.classList.contains('on')));
  }
  const document = {
    hidden: false,
    documentElement: { getAttribute: () => '/demo' },
    querySelectorAll: sel => slots.flatMap(el => query(sel, el.children)),
    addEventListener: (name, fn) => { events[name] = fn; },
    createElement: () => {
      const classes = new Set(), callbacks = {}, props = [], requests = [];
      return {
        removed: false, classes, callbacks, props, requests,
        classList: { add: c => classes.add(c), contains: c => classes.has(c) },
        set className(c) { c.split(' ').forEach(k => classes.add(k)); },
        setAttribute() {}, addEventListener: (name, fn) => { callbacks[name] = fn; },
        remove() { this.removed = true; },
        contentWindow: {
          wallpaperPropertyListener: { applyUserProperties: p => props.push(p) },
          requestAnimationFrame: fn => { requests.push(fn); return requests.length; }
        }
      };
    }
  };
  const window = { Scenes: { reduce } };
  const sandbox = { window, document, Scenes: window.Scenes,
    IntersectionObserver: class { constructor(fn) { io = fn; } observe() {} },
    requestAnimationFrame: fn => { raf.push(fn); },
    setTimeout: fn => { const id = ++nextTimer; timers.set(id, fn); return id; },
    clearTimeout: id => timers.delete(id)
  };
  window.IntersectionObserver = sandbox.IntersectionObserver;
  vm.runInNewContext(source, sandbox);
  function slot(slug) {
    const poster = {}, classes = new Set();
    const el = {
      dataset: { live: slug }, children: [],
      classList: { toggle: (c, on) => on ? classes.add(c) : classes.delete(c) },
      querySelector: () => poster,
      querySelectorAll: sel => query(sel, el.children),
      appendChild: f => el.children.push(f)
    };
    slots.push(el);
    return { el, api: window.Live.slot(el), frames: () => el.querySelectorAll('iframe.live'), poster };
  }
  function see(entries) { io(entries.map(([s, ratio]) => ({ target: s.el, isIntersecting: ratio > 0, intersectionRatio: ratio }))); }
  function paint(f) { f.callbacks.load(); while (raf.length) raf.shift()(); }
  function settle() { for (const [id, fn] of timers) { timers.delete(id); fn(); } }
  function hidden(on) { document.hidden = on; events.visibilitychange(); }
  return { window, slot, see, paint, settle, hidden };
}

test('rapid selections retain one painted fallback and at most one incoming renderer', () => {
  const h = harness(), s = h.slot('jade-vein');
  h.see([[s, 1]]); const first = s.frames()[0]; h.paint(first);
  s.api.set('daybreak'); const superseded = s.frames().at(-1);
  s.api.set('copper-fold'); s.api.set('neon-rain');
  assert.equal(s.frames().length, 2);
  assert.ok(s.frames().includes(first));
  h.paint(superseded); // A load event may arrive after the user selects something else.
  assert.equal(s.frames().length, 2);
  const last = s.frames().at(-1); h.paint(last); h.settle();
  assert.equal(s.frames().length, 1); assert.equal(s.frames()[0], last);
  assert.equal(last.src, '/demo/wallpapers/neon-rain/index.html');
});

test('pause releases renderers immediately; resume retains the selected wallpaper and properties', () => {
  const h = harness(), s = h.slot('jade-vein'); h.see([[s, 1]]); h.paint(s.frames()[0]);
  const props = { speed: { value: 2.5 } }; s.api.apply(props); s.api.set('daybreak');
  s.api.pause(true); assert.equal(h.window.__liveCount, 0);
  s.api.set('copper-fold'); assert.equal(s.frames().length, 0);
  s.api.pause(false); const resumed = s.frames()[0]; h.paint(resumed);
  assert.equal(resumed.src, '/demo/wallpapers/copper-fold/index.html');
  assert.deepEqual(resumed.props.at(-1), props);
});

test('only the most visible slot renders; paused slots do not starve another slot', () => {
  const h = harness(), a = h.slot('jade-vein'), b = h.slot('neon-rain');
  h.see([[a, .8], [b, .4]]); assert.equal(a.frames().length, 1); assert.equal(b.frames().length, 0);
  a.api.pause(true); assert.equal(a.frames().length, 0); assert.equal(b.frames().length, 1);
  h.see([[a, 0], [b, 0]]); assert.equal(h.window.__liveCount, 0);
});

test('hidden tabs release even a crossfade; returning restores only the active slot', () => {
  const h = harness(), s = h.slot('jade-vein'); h.see([[s, 1]]); h.paint(s.frames()[0]);
  s.api.set('daybreak'); assert.equal(h.window.__liveCount, 2);
  h.hidden(true); assert.equal(h.window.__liveCount, 0);
  h.settle(); assert.equal(h.window.__liveCount, 0);
  h.hidden(false); assert.equal(h.window.__liveCount, 1);
});

test('reduced motion never starts a renderer, including after resume and selection', () => {
  const h = harness(true), s = h.slot('jade-vein'); h.see([[s, 1]]);
  s.api.pause(true); s.api.set('daybreak'); s.api.pause(false); h.hidden(true); h.hidden(false);
  assert.equal(h.window.__liveCount, 0); assert.match(s.poster.src, /daybreak/);
});

test('low power actually throttles the wallpaper RAF callbacks, and normal mode releases the cap', () => {
  const h = harness(), s = h.slot('neon-rain'); s.api.fps(24); h.see([[s, 1]]);
  const f = s.frames()[0]; h.paint(f); const seen = [];
  f.contentWindow.requestAnimationFrame(now => seen.push(now)); f.requests.shift()(0);
  f.contentWindow.requestAnimationFrame(now => seen.push(now)); f.requests.shift()(16); f.requests.shift()(33);
  assert.deepEqual(seen, [0]); f.requests.shift()(42); assert.deepEqual(seen, [0, 42]);
  s.api.fps(0); f.contentWindow.requestAnimationFrame(now => seen.push(now)); f.requests.shift()(48);
  assert.deepEqual(seen, [0, 42, 48]);
});
