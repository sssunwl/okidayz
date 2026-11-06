// 首頁「今日島況」跑馬燈:天氣、今天是、週末活動數、匯率、最新一則新聞,全部讀站上現成的 json
(function () {
  var box = document.getElementById('islandTicker');
  if (!box) return;
  var base = (document.querySelector('link[href$="assets/site.css"]') || {}).getAttribute
    ? document.querySelector('link[href$="assets/site.css"]').getAttribute('href').replace('assets/site.css', '') : '';
  function get(name) { return fetch(base + name, { cache: 'no-store' }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; }); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function okiDate(d) { return new Date(d.getTime() + 9 * 3600e3).toISOString().slice(0, 10); }
  function addDays(s, n) { var d = new Date(s + 'T00:00:00Z'); d.setUTCDate(d.getUTCDate() + n); return d.toISOString().slice(0, 10); }
  Promise.all([get('weather.json'), get('signals.json'), get('rates.json')]).then(function (res) {
    var w = res[0] || [], sig = (res[1] || {}).items || [], rt = (res[2] || {}).rates || {};
    var today = okiDate(new Date()), items = [];
    var t = w.filter(function (x) { return x.date === today; })[0] || w[0];
    if (t) items.push(['今天', t.icon + ' ' + t.temp_min + '–' + t.temp_max + '°・降雨 ' + t.rain_chance + '%']);
    var ti = sig.filter(function (x) { return x.kind === 'today' && x.date === today; })[0];
    if (ti) items.push(['今天是', ti.title]);
    var dow = new Date(today + 'T00:00:00Z').getUTCDay(), sat = dow === 0 ? addDays(today, -1) : addDays(today, (6 - dow + 7) % 7), sun = addDays(sat, 1);
    var wk = sig.filter(function (x) { return x.kind === 'event' && x.date <= sun && (x.date_end || x.date) >= sat; }).length;
    if (wk) items.push(['這週末', '全島 ' + wk + ' 個活動']);
    if (rt.TWD) items.push(['匯率', '1 萬日圓 ≈ NT$' + Math.round(rt.TWD * 1e4).toLocaleString() + (rt.HKD ? '・HK$' + Math.round(rt.HKD * 1e4) : '')]);
    var al = sig.filter(function (x) { return x.kind === 'alert'; })[0];
    if (al) items.push(['注意', al.title]);
    var nw = sig.filter(function (x) { return x.kind === 'news'; })[0];
    if (nw) items.push(['島上新聞', nw.title]);
    if (!items.length) return;
    var one = items.map(function (x) { return '<span><b>' + esc(x[0]) + '</b>' + esc(x[1]) + '</span>'; }).join('');
    // 內容放兩次,捲到一半剛好接上
    box.querySelector('.run').innerHTML = one + one;
  });
})();
