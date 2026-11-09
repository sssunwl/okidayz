/* 地點頁／路線頁的「今天」面板：在瀏覽器讀 events.json、weather.json、海況 json，
   所以那幾份資料每天更新後，每個地點頁不用重新 build 也會跟著變。
   設定寫在 [data-place-live] 上：{prefix, area(可用 | 串多個市町村), region, ocean, surf}。 */
(function () {
  'use strict';

  var panels = document.querySelectorAll('[data-place-live]');
  if (!panels.length) return;

  // events.json 的 area 是市町村名；同一區的其他市町村當成「附近」補位
  var REGION_AREAS = {
    '南部': ['那覇市', '豊見城市', '糸満市', '南城市', '八重瀬町', '与那原町', '南風原町', '西原町'],
    '中部': ['浦添市', '宜野湾市', '北谷町', '嘉手納町', '読谷村', '沖縄市', 'うるま市', '北中城村', '中城村', '恩納村', '沖縄市（コザ）・北谷・宜野湾'],
    '北部': ['名護市', '本部町', '今帰仁村', '国頭村', '大宜味村', '東村', '宜野座村', '金武町', '沖縄県北部地域'],
    '離島': ['宮古島', '石垣島', '座間味村', '渡嘉敷村', '離島', '久米島町', '竹富町', '与那国町']
  };
  var WEEK = ['日', '一', '二', '三', '四', '五', '六'];
  var cache = {};

  function load(prefix, name) {
    var key = prefix + name;
    if (!cache[key]) {
      cache[key] = fetch(prefix + name, { cache: 'no-cache' })
        .then(function (r) { return r.ok ? r.json() : null; })
        .catch(function () { return null; });
    }
    return cache[key];
  }

  function esc(text) {
    return String(text == null ? '' : text).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  function safeUrl(url) {
    return /^https?:\/\//.test(url || '') ? url : '';
  }

  // 沖繩時間的今天（YYYY-MM-DD）
  function todayJst() {
    var d = new Date(Date.now() + 9 * 3600 * 1000);
    return d.toISOString().slice(0, 10);
  }

  function addDays(ymd, days) {
    var d = new Date(ymd + 'T00:00:00Z');
    d.setUTCDate(d.getUTCDate() + days);
    return d.toISOString().slice(0, 10);
  }

  function shortDate(ymd) {
    var d = new Date(ymd + 'T00:00:00Z');
    return (d.getUTCMonth() + 1) + '/' + d.getUTCDate() + '（' + WEEK[d.getUTCDay()] + '）';
  }

  function renderWeather(box, list, today) {
    if (!box) return;
    var day = (list || []).filter(function (w) { return w.date === today; })[0] || (list || [])[0];
    if (!day) {
      box.innerHTML = '<span class="live-muted">暫時拿不到天氣</span>';
      return;
    }
    box.innerHTML =
      '<span class="live-big">' + esc(day.icon) + ' ' + esc(day.temp_min) + '–' + esc(day.temp_max) + '°C</span>' +
      '<span class="live-chip">降雨 ' + esc(day.rain_chance) + '%</span>' +
      '<span class="live-chip">UV ' + esc(day.uv_label) + '</span>';
  }

  function conditionHtml(spot, label, href) {
    var wave = spot.wave_height_m != null ? spot.wave_height_m.toFixed(1) + ' m' : '—';
    var wind = (spot.wind_dir_label || '') + ' ' + (spot.wind_speed_kn != null ? Math.round(spot.wind_speed_kn) + ' kt' : '');
    return '<a class="live-cond is-' + esc(spot.verdict) + '" href="' + esc(href) + '">' +
      '<span class="live-cond-label">' + esc(label) + '・' + esc(spot.name) + '</span>' +
      '<strong>' + esc(spot.verdict_label) + '</strong>' +
      '<span>浪 ' + esc(wave) + '・風 ' + esc(wind) + '</span>' +
      '<small>' + esc(spot.verdict_reason) + '</small></a>';
  }

  function renderOcean(box, cfg, ocean, surf) {
    if (!box) return;
    var parts = [];
    function find(data, slug) {
      return ((data && data.spots) || []).filter(function (s) { return s.slug === slug; })[0];
    }
    var dive = cfg.ocean && find(ocean, cfg.ocean);
    var wave = cfg.surf && find(surf, cfg.surf);
    if (dive) parts.push(conditionHtml(dive, '海況', cfg.prefix + 'ocean/#live-conditions'));
    if (wave) parts.push(conditionHtml(wave, '浪況', cfg.prefix + 'ocean/#live-surf-conditions'));
    if (!parts.length) return;
    box.innerHTML = parts.join('');
    box.hidden = false;
  }

  function renderEvents(list, cfg, today) {
    var areas = (cfg.area || '').split('|').filter(Boolean);
    var regionAreas = REGION_AREAS[cfg.region] || [];
    var until = addDays(today, 21);
    var live = (list || []).filter(function (e) {
      var end = e.date_end || e.date_start;
      return e.area && e.date_start && e.date_start <= until && end >= today;
    });
    var near = live.filter(function (e) { return areas.indexOf(e.area) >= 0; });
    var region = live.filter(function (e) { return areas.indexOf(e.area) < 0 && regionAreas.indexOf(e.area) >= 0; });
    var byDate = function (a, b) { return a.date_start < b.date_start ? -1 : 1; };
    return near.sort(byDate).concat(region.sort(byDate)).slice(0, 5);
  }

  function eventsHtml(items, today) {
    if (!items.length) return '<li class="live-muted">這幾週附近沒有登錄的活動。</li>';
    return items.map(function (e) {
      var start = e.date_start < today ? today : e.date_start;
      var when = e.date_start <= today ? '進行中' : shortDate(start);
      var link = safeUrl(e.official_url) || safeUrl(e.url);
      var name = esc(e.name_zh || e.name);
      return '<li><span class="live-when' + (when === '進行中' ? ' is-now' : '') + '">' + when + '</span>' +
        (link ? '<a href="' + esc(link) + '" target="_blank" rel="noopener">' + name + '</a>' : '<span>' + name + '</span>') +
        '<small>' + esc(e.area) + '</small></li>';
    }).join('');
  }

  panels.forEach(function (panel) {
    var cfg;
    try {
      cfg = JSON.parse(panel.dataset.placeLive);
    } catch (error) {
      return;
    }
    var today = todayJst();
    var dateBox = panel.querySelector('[data-live-date]');
    if (dateBox) dateBox.textContent = shortDate(today);

    load(cfg.prefix, 'weather.json').then(function (w) {
      renderWeather(panel.querySelector('[data-live-weather]'), w, today);
    });
    if (cfg.ocean || cfg.surf) {
      Promise.all([
        cfg.ocean ? load(cfg.prefix, 'ocean-conditions.json') : null,
        cfg.surf ? load(cfg.prefix, 'surf-conditions.json') : null
      ]).then(function (res) {
        renderOcean(panel.querySelector('[data-live-ocean]'), cfg, res[0], res[1]);
      });
    }
    load(cfg.prefix, 'events.json').then(function (list) {
      var box = panel.querySelector('[data-live-events]');
      if (box) box.innerHTML = list ? eventsHtml(renderEvents(list, cfg, today), today) : '<li class="live-muted">暫時拿不到活動資料</li>';
    });
  });
})();
