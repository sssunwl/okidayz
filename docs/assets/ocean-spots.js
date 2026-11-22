/* 海況頁「沖繩的海」：沙灘／潛水／衝浪分頁（#beach #dive #surf 可直接開）、地區篩選、點位照片左右切換。
   舊連結 #live-conditions（岸潛海況）、#live-surf-conditions（浪況）會自動開對應分頁再捲過去。 */
(function () {
  'use strict';

  var root = document.getElementById('spots');
  if (!root) return;
  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  var tabs = root.querySelectorAll('[data-os-kind]');
  var panes = root.querySelectorAll('[data-os-pane]');

  function show(kind, updateHash) {
    var found = false;
    tabs.forEach(function (t) {
      var on = t.dataset.osKind === kind;
      found = found || on;
      t.classList.toggle('on', on);
      t.setAttribute('aria-pressed', String(on));
    });
    if (!found) return false;
    panes.forEach(function (p) { p.hidden = p.dataset.osPane !== kind; });
    if (updateHash && history.replaceState) history.replaceState(null, '', '#' + kind);
    return true;
  }

  root.addEventListener('click', function (e) {
    var tab = e.target.closest('[data-os-kind]');
    if (tab) { show(tab.dataset.osKind, true); return; }
    var chip = e.target.closest('[data-os-r]');
    if (chip) {
      var pane = chip.closest('[data-os-pane]');
      var region = chip.dataset.osR;
      pane.querySelectorAll('[data-os-r]').forEach(function (c) { c.classList.toggle('active', c === chip); });
      pane.querySelectorAll('[data-os-region]').forEach(function (g) {
        g.hidden = region !== '' && g.dataset.osRegion !== region;
      });
    }
  });

  var hash = location.hash.slice(1);
  var alias = { 'live-conditions': 'dive', 'live-surf-conditions': 'surf' };
  if (alias[hash]) {
    show(alias[hash], false);
    var target = document.getElementById(hash);
    if (target) setTimeout(function () { target.scrollIntoView(); }, 0);
  } else if (show(hash, false)) {
    setTimeout(function () { root.scrollIntoView(); }, 0);
  }

  root.querySelectorAll('[data-os-photos]').forEach(function (box) {
    var track = box.querySelector('.os-track');
    var prev = box.querySelector('.prev');
    var next = box.querySelector('.next');
    var count = box.querySelector('.os-count');
    if (!prev) return;
    var total = track.children.length;
    function index() { return Math.round(track.scrollLeft / track.clientWidth); }
    function go(i) {
      i = Math.max(0, Math.min(total - 1, i));
      track.scrollTo({ left: i * track.clientWidth, behavior: reduceMotion ? 'auto' : 'smooth' });
    }
    function update() {
      var i = index();
      count.textContent = (i + 1) + ' / ' + total;
      prev.hidden = i <= 0;
      next.hidden = i >= total - 1;
    }
    prev.addEventListener('click', function () { go(index() - 1); });
    next.addEventListener('click', function () { go(index() + 1); });
    track.addEventListener('scroll', update, { passive: true });
    update();
  });
})();
