/* Лента макроэкономических новостей: загрузка, фильтры, индикатор обновления. */
(function () {
  "use strict";

  const PAGE_SIZE = 30;
  const state = { offset: 0, total: 0, loading: false };

  const el = {
    feed: document.getElementById("feed"),
    feedInfo: document.getElementById("feed-info"),
    loadMore: document.getElementById("load-more"),
    lastUpdated: document.getElementById("last-updated"),
    refreshBtn: document.getElementById("refresh-btn"),
    resetBtn: document.getElementById("reset-btn"),
    source: document.getElementById("f-source"),
    category: document.getElementById("f-category"),
    from: document.getElementById("f-from"),
    to: document.getElementById("f-to"),
    q: document.getElementById("f-q"),
  };

  function filterParams() {
    const p = new URLSearchParams();
    if (el.source.value) p.set("source", el.source.value);
    if (el.category.value) p.set("category", el.category.value);
    if (el.from.value) p.set("date_from", el.from.value);
    if (el.to.value) p.set("date_to", el.to.value);
    if (el.q.value.trim()) p.set("q", el.q.value.trim());
    return p;
  }

  function fmtDate(iso) {
    if (!iso) return "";
    const d = new Date(iso);
    return d.toLocaleString("ru-RU", {
      day: "2-digit", month: "2-digit", year: "numeric",
      hour: "2-digit", minute: "2-digit",
    });
  }

  function relTime(iso) {
    if (!iso) return null;
    const sec = Math.round((Date.now() - new Date(iso).getTime()) / 1000);
    if (sec < 60) return "только что";
    const min = Math.round(sec / 60);
    if (min < 60) return `${min} мин назад`;
    const h = Math.round(min / 60);
    if (h < 24) return `${h} ч назад`;
    return fmtDate(iso);
  }

  function esc(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

  function renderCard(item) {
    const verified = item.verified
      ? ' <span class="verified-mark" title="Официальный первоисточник">✓</span>'
      : "";
    return `
      <article class="card">
        <div class="card-meta">
          <span class="chip">${esc(item.category)}</span>
          <span class="source-badge">${esc(item.source_title || item.source)}${verified}</span>
          <span class="card-date" title="Собрано: ${esc(fmtDate(item.collected_at))}">
            ${esc(fmtDate(item.published_at))}
          </span>
        </div>
        <h2 class="card-title">
          <a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">${esc(item.title)}</a>
        </h2>
        ${item.summary ? `<p class="card-summary">${esc(item.summary)}</p>` : ""}
        <div class="card-footer">
          <a href="${esc(item.url)}" target="_blank" rel="noopener noreferrer">Первоисточник ↗</a>
        </div>
      </article>`;
  }

  async function loadNews(append) {
    if (state.loading) return;
    state.loading = true;
    if (!append) {
      state.offset = 0;
      el.feed.innerHTML = '<div class="empty">Загрузка…</div>';
    }
    try {
      const p = filterParams();
      p.set("limit", PAGE_SIZE);
      p.set("offset", state.offset);
      const resp = await fetch(`/api/news?${p}`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data = await resp.json();
      state.total = data.total;

      const html = data.items.map(renderCard).join("");
      if (append) {
        el.feed.insertAdjacentHTML("beforeend", html);
      } else {
        el.feed.innerHTML =
          html || '<div class="empty">Новостей по заданным фильтрам нет.</div>';
      }
      state.offset += data.items.length;
      el.feedInfo.textContent = state.total
        ? `Показано ${state.offset} из ${state.total}`
        : "";
      el.loadMore.hidden = state.offset >= state.total;
    } catch (err) {
      el.feed.innerHTML = `<div class="error-box">Не удалось загрузить новости: ${esc(err.message)}</div>`;
    } finally {
      state.loading = false;
    }
  }

  async function loadMeta() {
    try {
      const resp = await fetch("/api/meta");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const meta = await resp.json();

      fillSelect(el.source, meta.sources.map((s) => [s.id, s.title]));
      fillSelect(el.category, meta.all_categories.map((c) => [c, c]));

      const rel = relTime(meta.last_updated);
      el.lastUpdated.textContent = rel ? `Обновлено: ${rel}` : "Данные ещё не собраны";
      // если последнее обновление сильно старше интервала сбора — подсветить
      const stale =
        meta.last_updated &&
        Date.now() - new Date(meta.last_updated).getTime() >
          meta.collect_interval_minutes * 60 * 1000 * 3;
      el.lastUpdated.classList.toggle("stale", Boolean(stale));
    } catch {
      el.lastUpdated.textContent = "Статус недоступен";
    }
  }

  function fillSelect(select, pairs) {
    const current = select.value;
    while (select.options.length > 1) select.remove(1);
    for (const [value, label] of pairs) {
      const opt = document.createElement("option");
      opt.value = value;
      opt.textContent = label;
      select.appendChild(opt);
    }
    select.value = current;
  }

  async function collectNow() {
    el.refreshBtn.disabled = true;
    el.refreshBtn.textContent = "Собираем…";
    try {
      await fetch("/api/collect", { method: "POST" });
    } catch { /* статус обновится ниже */ }
    el.refreshBtn.disabled = false;
    el.refreshBtn.textContent = "Обновить сейчас";
    await Promise.all([loadMeta(), loadNews(false)]);
  }

  // --- события ---
  el.refreshBtn.addEventListener("click", collectNow);
  el.resetBtn.addEventListener("click", () => {
    el.source.value = "";
    el.category.value = "";
    el.from.value = "";
    el.to.value = "";
    el.q.value = "";
    loadNews(false);
  });
  el.loadMore.addEventListener("click", () => loadNews(true));
  for (const control of [el.source, el.category, el.from, el.to]) {
    control.addEventListener("change", () => loadNews(false));
  }
  let qTimer;
  el.q.addEventListener("input", () => {
    clearTimeout(qTimer);
    qTimer = setTimeout(() => loadNews(false), 350);
  });

  // --- старт ---
  loadMeta().then(() => loadNews(false));
  // периодическое обновление ленты и индикатора (сбор идёт на сервере по расписанию)
  setInterval(loadMeta, 60 * 1000);
  setInterval(() => { if (state.offset <= PAGE_SIZE) loadNews(false); }, 120 * 1000);
})();
