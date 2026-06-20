function renderHorizontalChart(container, values) {
  if (!values.length) {
    container.innerHTML = '<p class="chart-empty">No chart data for this selection.</p>';
    return;
  }

  const maxValue = Math.max(...values.map((item) => Number(item.value) || 0), 1);
  const wrapper = document.createElement("div");
  wrapper.className = "chart-bars";

  values.forEach((item) => {
    const row = document.createElement("div");
    row.className = "chart-row";
    row.title = item.secondary
      ? `${item.label}: ${item.display_value} records, ${item.secondary}`
      : `${item.label}: ${item.display_value}`;

    const label = document.createElement("span");
    label.className = "chart-row-label";
    label.textContent = item.label;

    const track = document.createElement("div");
    track.className = "chart-row-track";

    const fill = document.createElement("span");
    fill.className = "chart-row-fill";
    fill.style.width = `${Math.max((Number(item.value) / maxValue) * 100, 6)}%`;
    track.appendChild(fill);

    const meta = document.createElement("div");
    meta.className = "chart-row-meta";

    const primary = document.createElement("strong");
    primary.textContent = item.display_value;
    meta.appendChild(primary);

    if (item.secondary) {
      const secondary = document.createElement("span");
      secondary.textContent = item.secondary;
      meta.appendChild(secondary);
    } else if (typeof item.share !== "undefined") {
      const share = document.createElement("span");
      share.textContent = `${item.share}%`;
      meta.appendChild(share);
    }

    row.append(label, track, meta);
    wrapper.appendChild(row);
  });

  container.replaceChildren(wrapper);
}

function renderVerticalChart(container, values) {
  if (!values.length) {
    container.innerHTML = '<p class="chart-empty">No chart data for this selection.</p>';
    return;
  }

  const maxValue = Math.max(...values.map((item) => Number(item.value) || 0), 1);
  const wrapper = document.createElement("div");
  wrapper.className = "chart-columns";

  values.forEach((item) => {
    const column = document.createElement("div");
    column.className = "chart-column";
    column.title = item.secondary
      ? `${item.label}: ${item.display_value} records, ${item.secondary}`
      : `${item.label}: ${item.display_value}`;

    const track = document.createElement("div");
    track.className = "chart-column-track";

    const fill = document.createElement("div");
    fill.className = "chart-column-fill";
    fill.style.height = `${Math.max((Number(item.value) / maxValue) * 100, 8)}%`;
    track.appendChild(fill);

    const label = document.createElement("span");
    label.className = "chart-column-label";
    label.textContent = item.label;

    const meta = document.createElement("div");
    meta.className = "chart-column-meta";
    meta.innerHTML = `<strong>${item.display_value}</strong>${item.secondary ? `<br>${item.secondary}` : ""}`;

    column.append(track, label, meta);
    wrapper.appendChild(column);
  });

  container.replaceChildren(wrapper);
}

function renderCharts() {
  document.querySelectorAll("[data-chart-values]").forEach((container) => {
    let values = [];
    try {
      values = JSON.parse(container.dataset.chartValues || "[]");
    } catch (_error) {
      values = [];
    }

    const type = container.dataset.chartType || "horizontal";
    if (type === "vertical") {
      renderVerticalChart(container, values);
    } else {
      renderHorizontalChart(container, values);
    }
  });
}

function setupCommandPalette() {
  const palette = document.querySelector("[data-command-palette]");
  if (!palette) {
    return;
  }

  const openButtons = document.querySelectorAll("[data-command-open]");
  const closeButtons = document.querySelectorAll("[data-command-close]");

  const openPalette = () => {
    palette.hidden = false;
  };

  const closePalette = () => {
    palette.hidden = true;
  };

  openButtons.forEach((button) => button.addEventListener("click", openPalette));
  closeButtons.forEach((button) => button.addEventListener("click", closePalette));
  palette.querySelectorAll("[data-command-item]").forEach((item) => {
    item.addEventListener("click", closePalette);
  });

  document.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
      event.preventDefault();
      if (palette.hidden) {
        openPalette();
      } else {
        closePalette();
      }
    }
    if (event.key === "Escape" && !palette.hidden) {
      closePalette();
    }
  });
}

function setupRecordDrawer() {
  const drawer = document.querySelector("[data-record-drawer]");
  const grid = document.querySelector("[data-record-grid]");
  if (!drawer || !grid) {
    return;
  }

  const closeDrawer = () => {
    drawer.hidden = true;
    grid.replaceChildren();
  };

  document.querySelectorAll("[data-record-close]").forEach((button) => {
    button.addEventListener("click", closeDrawer);
  });

  document.querySelectorAll("[data-row-detail]").forEach((row) => {
    row.addEventListener("click", () => {
      let payload = {};
      try {
        payload = JSON.parse(row.dataset.rowDetail || "{}");
      } catch (_error) {
        payload = {};
      }

      grid.replaceChildren();
      Object.entries(payload).forEach(([key, value]) => {
        const item = document.createElement("div");
        item.className = "record-item";
        item.innerHTML = `<span>${key.replaceAll("_", " ")}</span><strong>${value || "—"}</strong>`;
        grid.appendChild(item);
      });
      drawer.hidden = false;
    });
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !drawer.hidden) {
      closeDrawer();
    }
  });
}

document.addEventListener("DOMContentLoaded", () => {
  const revealItems = document.querySelectorAll("[data-reveal]");
  const revealObserver = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("is-visible");
          revealObserver.unobserve(entry.target);
        }
      });
    },
    { threshold: 0.18 }
  );

  revealItems.forEach((item) => revealObserver.observe(item));
  renderCharts();
  setupCommandPalette();
  setupRecordDrawer();

  document.querySelectorAll("[data-tabs]").forEach((tabStrip) => {
    const buttons = tabStrip.querySelectorAll("[data-tab-target]");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const targetId = button.getAttribute("data-tab-target");
        const scope = tabStrip.parentElement;

        buttons.forEach((candidate) => candidate.classList.remove("is-active"));
        scope.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("is-active"));

        button.classList.add("is-active");
        const target = scope.querySelector(`#${targetId}`);
        if (target) {
          target.classList.add("is-active");
        }
      });
    });
  });

  document.querySelectorAll("[data-accordion]").forEach((card) => {
    const trigger = card.querySelector(".qa-trigger");
    if (!trigger) {
      return;
    }

    trigger.addEventListener("click", () => {
      card.classList.toggle("is-open");
      const label = card.classList.contains("is-open") ? "Close" : "Open";
      const badge = trigger.querySelector("strong");
      if (badge) {
        badge.textContent = label;
      }
    });
  });
});
