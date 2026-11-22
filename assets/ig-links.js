/* /ig/ 連結頁：卡片內輪播左右切換、?from=threads 換 utm 來源、#標籤 直接套篩選。
   標籤篩選本身沿用 section.js（同一套 .filter-block）。 */
(function () {
  'use strict';

  var reduceMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Threads 簡介連到 /ig/?from=threads：卡片與快捷連結的 utm_source 改成 threads
  var from = new URLSearchParams(location.search).get('from');
  if (from === 'threads') {
    document.querySelectorAll('a[href*="utm_source=ig"]').forEach(function (a) {
      a.setAttribute('href', a.getAttribute('href').replace('utm_source=ig', 'utm_source=threads'));
    });
    var src = document.querySelector('[data-igl-src]');
    if (src) src.textContent = 'Threads';
  }

  document.querySelectorAll('[data-igl]').forEach(function (frame) {
    var track = frame.querySelector('.igl-track');
    var slides = track.children;
    var prev = frame.querySelector('.prev');
    var next = frame.querySelector('.next');
    var count = frame.querySelector('.igl-count');
    var total = slides.length;
    if (total < 2) { prev.hidden = true; next.hidden = true; count.hidden = true; return; }

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
    frame.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowLeft') { go(index() - 1); e.preventDefault(); }
      if (e.key === 'ArrowRight') { go(index() + 1); e.preventDefault(); }
    });
    track.addEventListener('scroll', update, { passive: true });
    update();
  });

  // 簡介或貼文可以直接連 /ig/#一日遊路線，進來就幫忙按好那個標籤
  var want = decodeURIComponent(location.hash.slice(1));
  if (want) {
    var chip = Array.prototype.find.call(document.querySelectorAll('#iglFilters .tag-chip'),
      function (c) { return c.dataset.tag === want; });
    if (chip) chip.click();
  }
})();
