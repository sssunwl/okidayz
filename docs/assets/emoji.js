// tools/emoji_icons.py 產生,不要手改(程式本體在 tools/emoji_swap.js)
/* 把頁面上的 emoji 換成品牌手繪圖(assets/brand/emoji/*.svg)。
   靜態 HTML 和 JS 後來畫上去的內容都會換(MutationObserver)。對照表沒有的 emoji 用 spark。 */
(function () {
  'use strict';
  var MAP = {"☀": "sun", "🌞": "sun", "🌤": "suncloud", "⛅": "suncloud", "🌥": "suncloud", "🌦": "rain", "☁": "cloud", "🌫": "cloud", "🌧": "rain", "☔": "rain", "⛈": "storm", "🌩": "storm", "🌬": "storm", "🌀": "storm", "❄": "snow", "🌨": "snow", "🌙": "moon", "💧": "drop", "🌊": "wave", "🏄": "wave", "🤿": "wave", "🪸": "wave", "🏖": "island", "🏝": "island", "🐢": "turtle", "📍": "pin", "📰": "news", "📡": "news", "🗾": "news", "📄": "news", "📚": "news", "✉": "news", "🧳": "suitcase", "📦": "suitcase", "📅": "calendar", "🗓": "calendar", "💱": "coin", "💰": "coin", "💴": "coin", "💯": "coin", "🚗": "car", "🚌": "car", "🗣": "speech", "🔊": "speech", "♡": "heart_o", "♥": "heart", "💝": "heart", "❤": "heart", "🧭": "compass", "☰": "menu", "✕": "close", "☓": "close", "⚠": "warn", "✎": "pencil", "🎨": "pencil", "🌸": "flower", "🌺": "flower", "🌼": "flower", "🌿": "leaf", "🌳": "leaf", "🌾": "leaf", "🍂": "leaf", "🍋": "leaf", "🎋": "leaf", "🎍": "leaf", "🍙": "food", "🍔": "food", "🍧": "food", "🫘": "food", "🍠": "food", "🍫": "food", "🌶": "food", "🧂": "food", "🍜": "food", "☕": "drink", "🍶": "drink", "🥃": "drink", "🍺": "drink", "🥁": "festival", "🎭": "festival", "👹": "festival", "🎎": "festival", "🎃": "lantern", "🏮": "lantern", "🎄": "leaf", "⛩": "shrine", "🏯": "shrine", "🙏": "shrine", "🕊": "shrine", "👘": "shrine", "⛰": "mountain", "♨": "onsen"};
  var me = document.currentScript && document.currentScript.src;
  var base = me ? me.replace(/assets\/emoji\.js.*$/, '') : '/';
  // 變體選擇字、膚色、ZWJ 組合字也吃進來,整串換成一張圖
  var RE = /(?:[☀-➿⭐⌚-⏿←-⇿]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|\uD83E[\uDC00-\uDFFF])(?:️|‍(?:[☀-➿]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|\uD83E[\uDC00-\uDFFF])|\uD83C[\uDFFB-\uDFFF])*/g;
  var KEEP = /^[←-⇿]$/; // 箭頭(↗ ← →)是排版符號,不換
  var SKIP = { SCRIPT: 1, STYLE: 1, TEXTAREA: 1, INPUT: 1, TITLE: 1, OPTION: 1, NOSCRIPT: 1 };
  function nameOf(e) {
    var k = e.replace(/[️‍]|\uD83C[\uDFFB-\uDFFF]/g, '');
    return MAP[k] || MAP[Array.from(k)[0]] || 'spark';
  }
  function swap(node) {
    var t = node.nodeValue, frag = document.createDocumentFragment(), last = 0, changed = false, m;
    RE.lastIndex = 0;
    while ((m = RE.exec(t))) {
      if (KEEP.test(m[0])) continue;
      changed = true;
      if (m.index > last) frag.appendChild(document.createTextNode(t.slice(last, m.index)));
      var img = document.createElement('img');
      img.className = 'oki-emoji'; img.alt = ''; img.setAttribute('aria-hidden', 'true'); img.decoding = 'async';
      img.src = base + 'assets/brand/emoji/' + nameOf(m[0]) + '.svg';
      frag.appendChild(img);
      last = m.index + m[0].length;
    }
    if (!changed) return;
    if (last < t.length) frag.appendChild(document.createTextNode(t.slice(last)));
    node.parentNode.replaceChild(frag, node);
  }
  function walk(root) {
    if (root.nodeType === 3) { if (root.parentNode && !SKIP[root.parentNode.nodeName]) swap(root); return; }
    if (root.nodeType !== 1 || SKIP[root.nodeName]) return;
    var w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null), list = [], n;
    while ((n = w.nextNode())) if (!SKIP[n.parentNode.nodeName]) list.push(n);
    list.forEach(swap);
  }
  function start() {
    walk(document.body);
    new MutationObserver(function (ms) {
      ms.forEach(function (m) {
        if (m.type === 'characterData') walk(m.target);
        else m.addedNodes.forEach(walk);
      });
    }).observe(document.body, { childList: true, subtree: true, characterData: true });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start); else start();
})();
