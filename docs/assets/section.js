/* 內容區塊：多維 tag 篩選（同一排任一符合、不同排要同時符合）。一個頁面可以有多組獨立的篩選器＋格子
   （例如 /goods/ 同時有好物卡片格跟文章格），靠 data-target 對應各自的 grid。 */
(function () {
  'use strict';

  var blocks = document.querySelectorAll('.filter-block[data-target]');
  if (!blocks.length) return;

  blocks.forEach(function (filters) {
    var grid = document.getElementById(filters.dataset.target);
    if (!grid) return;
    var empty = document.getElementById(filters.dataset.target.replace(/Grid$/, 'Empty'));
    var active = [];

    function apply() {
      var cards = grid.children;
      var shown = 0;
      // 同一排（例如「教堂」「宴會廳」）點兩個是「都想看」，不是「兩個條件都要有」
      var groups = {};
      active.forEach(function (tag) {
        var row = filters.querySelector('.tag-chip[data-tag="' + tag.replace(/"/g, '\\"') + '"]');
        var label = row && row.closest('.filter-row');
        var key = label ? label.querySelector('.filter-label').textContent : tag;
        (groups[key] = groups[key] || []).push(tag);
      });
      for (var i = 0; i < cards.length; i++) {
        var tags = (cards[i].dataset.tags || '').split('|');
        var match = Object.keys(groups).every(function (key) {
          return groups[key].some(function (tag) { return tags.indexOf(tag) >= 0; });
        });
        cards[i].hidden = !match;
        if (match) shown++;
      }
      if (empty) empty.hidden = shown > 0;

      var chips = filters.querySelectorAll('.tag-chip');
      for (var j = 0; j < chips.length; j++) {
        var tag = chips[j].dataset.tag;
        chips[j].classList.toggle('active', tag ? active.indexOf(tag) >= 0 : active.length === 0);
        chips[j].setAttribute('aria-pressed', String(chips[j].classList.contains('active')));
      }
    }

    filters.addEventListener('click', function (event) {
      var chip = event.target.closest('.tag-chip');
      if (!chip) return;
      var tag = chip.dataset.tag;
      if (!tag) {
        active = [];
      } else {
        var index = active.indexOf(tag);
        if (index >= 0) active.splice(index, 1); else active.push(tag);
      }
      apply();
    });

    apply();
  });

  /* 海況卡片的地點切換標籤：手機版一次只顯示一張卡，桌機版維持整排 grid。
     用 matchMedia 判斷目前是不是手機寬度，切回桌機時自動還原全部顯示。 */
  var mobileQuery = window.matchMedia('(max-width: 760px)');
  var applyFns = [];

  document.querySelectorAll('[data-cond-tabs]').forEach(function (tabs) {
    var group = tabs.nextElementSibling;
    if (!group || !group.matches('[data-cond-group]')) return;
    var cards = group.querySelectorAll('[data-cond-card]');
    var tabButtons = tabs.querySelectorAll('.cond-tab');
    var activeIndex = 0;

    function apply() {
      if (!mobileQuery.matches) {
        cards.forEach(function (card) { card.hidden = false; });
        return;
      }
      cards.forEach(function (card, i) { card.hidden = i !== activeIndex; });
    }

    tabs.addEventListener('click', function (event) {
      var button = event.target.closest('.cond-tab');
      if (!button) return;
      activeIndex = Number(button.dataset.condTab || 0);
      tabButtons.forEach(function (b) { b.classList.remove('active'); });
      button.classList.add('active');
      apply();
    });

    applyFns.push(apply);
    apply();
  });

  if (applyFns.length) {
    var applyAll = function () { applyFns.forEach(function (fn) { fn(); }); };
    if (mobileQuery.addEventListener) {
      mobileQuery.addEventListener('change', applyAll);
    } else if (mobileQuery.addListener) {
      mobileQuery.addListener(applyAll);
    }
    // 保險：部分環境（例如自動化工具改視窗大小）不一定會觸發 matchMedia 的
    // change 事件，這裡額外掛一個 resize 監聽確保切回桌機寬度時卡片一定會還原。
    window.addEventListener('resize', applyAll);
  }

  /* 認識沖繩的地區卡片：桌機滑過（:hover/:focus-visible）就看得到說明，
     這裡額外補一個點擊切換，讓觸控裝置（沒有 hover）也能打開/關掉說明。 */
  document.querySelectorAll('[data-okiregion-card]').forEach(function (card) {
    card.addEventListener('click', function () {
      var expanded = card.classList.toggle('expanded');
      card.setAttribute('aria-expanded', String(expanded));
    });
  });
})();
