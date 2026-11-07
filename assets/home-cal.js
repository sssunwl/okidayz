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
  // 首頁只放遊客會有興趣的：當天開始的、祭典市集花火這類；長期展覽、比賽、講座留給年曆頁
  var LIKE = /祭|節|花火|煙火|燈|光|音樂|演唱|爵士|Jazz|JAZZ|Fes|fes|市集|マルシェ|市場|美食|啤酒|BBQ|海|沙灘|水族館|首里城|琉球|舞|太鼓|三線|エイサー|聖誕|跨年|新年|夜|馬拉松|親子|兒童|新開張|開幕|開業|限定|聯名|派對/;
  var MEH = /紀念展|作品展|特展|展覽|美術展|陶藝展|錦標賽|高爾夫|駕訓|比賽|大會|攝影展|畫展|水彩|書法|書道|會員|校友|研討|講座|說明會|招募|募集|相談|研修|課程|考試/;
  function span(e) { return (Date.parse(e.date_end || e.date_start) - Date.parse(e.date_start)) / 864e5; }
  function score(e, day) {
    var t = name(e) + ' ' + (e.category || '');
    return (e.date_start === day ? 3 : 0) + (LIKE.test(t) ? 2 : 0) - (MEH.test(t) ? 3 : 0) -
      (e.date_start !== day && span(e) > 14 ? 2 : 0);
  }
  function all(day) {
    return EVENTS.filter(function (e) { return e.date_start <= day && (e.date_end || e.date_start) >= day; });
  }
  function on(day) {
    return all(day).map(function (e) { return { e: e, s: score(e, day) }; })
      .filter(function (x) { return x.s >= 0; })
      .sort(function (a, b) { return b.s - a.s || a.e.date_start.localeCompare(b.e.date_start); })
      .slice(0, 8).map(function (x) { return x.e; });
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
    var total = all(selected).length;
    head.innerHTML = escapeHTML(fmtDate(selected)) + '<small>精選 ' + items.length + ' 個</small>' +
      (total ? '<a class="hc-all" href="' + eventsHref + '?date=' + selected + '">這天全部 ' + total + ' 個 →</a>' : '');
    if (!items.length) { list.innerHTML = '<li class="hc-empty">這天沒有特別推薦的活動，看看全部活動或換一天。</li>'; return; }
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
      if (!open && !pane.innerHTML) {
        var ev0 = list._items[Number(item.dataset.i)];
        pane.innerHTML = preview(ev0);
        pane.classList.toggle('no-img', !safeURL(ev0.image));
      }
      item.setAttribute('aria-expanded', String(!open));
      item.querySelector('em').textContent = open ? '＋' : '－';
      pane.hidden = open;
    }
  });

  drawGrid();
  drawList();
})();
