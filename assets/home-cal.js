/* 首頁活動月曆：點日子 → 看當天活動標題 → 點標題才展開預覽 */
(function () {
  'use strict';
  var box = document.getElementById('homeCal');
  if (!box) return;
  var escapeHTML = OKIP.escapeHTML, safeURL = OKIP.safeURL, fmtDate = OKIP.fmtDate;
  var node = document.getElementById('eventData');
  var EVENTS = [];
  try { EVENTS = JSON.parse(node.textContent) || []; } catch (err) { EVENTS = []; }
  EVENTS = EVENTS.filter(function (e) { return e.source !== 'today_is'; });
  var today = OKIP.tokyoToday();
  var eventsHref = box.dataset.eventsHref || 'events/';
  var grid = box.querySelector('[data-cal-grid]');
  var title = box.querySelector('[data-cal-title]');
  var list = box.querySelector('[data-cal-list]');
  var head = box.querySelector('[data-cal-day]');
  var view = new Date(today + 'T00:00:00');
  view.setDate(1);
  var selected = today;

  function iso(d) {
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function on(day) {
    return EVENTS.filter(function (e) { return e.date_start <= day && (e.date_end || e.date_start) >= day; })
      .sort(function (a, b) { return (b.date_start === day) - (a.date_start === day) || a.date_start.localeCompare(b.date_start); });
  }
  function name(e) { return e.name_zh || e.name || '未命名活動'; }

  function drawGrid() {
    title.textContent = view.getFullYear() + ' 年 ' + (view.getMonth() + 1) + ' 月';
    var first = view.getDay(), days = new Date(view.getFullYear(), view.getMonth() + 1, 0).getDate();
    var cells = [];
    for (var i = 0; i < first; i++) cells.push('<span class="hc-blank"></span>');
    for (var d = 1; d <= days; d++) {
      var day = iso(new Date(view.getFullYear(), view.getMonth(), d));
      var n = on(day).length;
      var cls = 'hc-day' + (day === today ? ' is-today' : '') + (day === selected ? ' is-on' : '') +
        (day < today ? ' is-past' : '') + (n ? ' has' : '');
      cells.push('<button type="button" class="' + cls + '" data-day="' + day + '"><b>' + d + '</b>' +
        (n ? '<i>' + (n > 9 ? '9+' : n) + '</i>' : '') + '</button>');
    }
    grid.innerHTML = cells.join('');
  }

  function drawList() {
    var items = on(selected);
    head.innerHTML = escapeHTML(fmtDate(selected)) + '<small>' + items.length + ' 個活動</small>';
    if (!items.length) { list.innerHTML = '<li class="hc-empty">這天還沒有整理到活動，換一天看看。</li>'; return; }
    list.innerHTML = items.map(function (e, i) {
      var start = e.date_start === selected ? '<span class="hc-new">開始</span>' : '';
      return '<li><button type="button" class="hc-item" data-i="' + i + '" aria-expanded="false">' + start +
        '<span>' + escapeHTML(name(e)) + '</span><em>＋</em></button><div class="hc-preview" hidden></div></li>';
    }).join('');
    list._items = items;
  }

  function preview(e) {
    var img = safeURL(e.image);
    var range = fmtDate(e.date_start) + (e.date_end && e.date_end !== e.date_start ? ' – ' + fmtDate(e.date_end) : '');
    return (img ? '<div class="hc-thumb" style="background-image:url(\'' + escapeHTML(img) + '\')"></div>' : '') +
      '<div><p class="hc-meta">🗓 ' + escapeHTML(range) + (e.location ? '<br>📍 ' + escapeHTML(e.location) : '') + '</p>' +
      (e.description ? '<p class="hc-desc">' + escapeHTML(e.description) + (e.description.length >= 140 ? '…' : '') + '</p>' : '') +
      (e._detail_slug ? '<a class="hc-go" href="' + eventsHref + escapeHTML(e._detail_slug) + '/">看活動介紹 →</a>' : '') +
      '</div>';
  }

  box.addEventListener('click', function (ev) {
    var dayBtn = ev.target.closest('[data-day]');
    if (dayBtn) { selected = dayBtn.dataset.day; drawGrid(); drawList(); return; }
    var nav = ev.target.closest('[data-cal-nav]');
    if (nav) { view.setMonth(view.getMonth() + Number(nav.dataset.calNav)); drawGrid(); return; }
    var item = ev.target.closest('.hc-item');
    if (item) {
      var pane = item.nextElementSibling, open = item.getAttribute('aria-expanded') === 'true';
      if (!open && !pane.innerHTML) pane.innerHTML = preview(list._items[Number(item.dataset.i)]);
      item.setAttribute('aria-expanded', String(!open));
      item.querySelector('em').textContent = open ? '＋' : '－';
      pane.hidden = open;
    }
  });

  drawGrid();
  drawList();
})();
