/* ============================================================
   FlyCircuit 連結體論文知識庫 — 共用互動腳本
   目前負責：目錄頁(index.html)的即時篩選與搜尋。
   論文頁載入此檔不會有副作用（找不到篩選器就跳過）。
   ============================================================ */
(function () {
  "use strict";

  function ready(fn) {
    if (document.readyState !== "loading") fn();
    else document.addEventListener("DOMContentLoaded", fn);
  }

  ready(function () {
    var q = document.getElementById("q");
    var fSpecies = document.getElementById("f-species");
    var fScale = document.getElementById("f-scale");
    var fTech = document.getElementById("f-technique");
    var reset = document.getElementById("reset");
    var countEl = document.getElementById("count");
    var cards = Array.prototype.slice.call(document.querySelectorAll(".card"));

    if (!cards.length) return; // 不是目錄頁，直接離開

    function apply() {
      var qs = (q && q.value || "").trim().toLowerCase();
      var sp = fSpecies ? fSpecies.value : "";
      var sc = fScale ? fScale.value : "";
      var te = fTech ? fTech.value : "";
      var shown = 0;

      cards.forEach(function (card) {
        var okQ = !qs || (card.dataset.search || "").indexOf(qs) !== -1;
        var okSp = !sp || card.dataset.species === sp;
        var okSc = !sc || card.dataset.scale === sc;
        var okTe = !te || (card.dataset.technique || "").indexOf("|" + te + "|") !== -1;
        var show = okQ && okSp && okSc && okTe;
        card.classList.toggle("hidden", !show);
        if (show) shown++;
      });

      if (countEl) countEl.textContent = shown + " / " + cards.length + " 篇";
    }

    [q, fSpecies, fScale, fTech].forEach(function (el) {
      if (!el) return;
      el.addEventListener("input", apply);
      el.addEventListener("change", apply);
    });

    if (reset) reset.addEventListener("click", function () {
      if (q) q.value = "";
      [fSpecies, fScale, fTech].forEach(function (s) { if (s) s.value = ""; });
      apply();
    });

    apply();
  });
})();
