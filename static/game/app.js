(() => {
  const actionButtons = document.querySelectorAll(".action-btn[data-move]");
  const logBox = document.getElementById("log-entries");
  const potEl = document.getElementById("pot-value");
  const streetEl = document.getElementById("street-label");
  const playerStackEl = document.getElementById("player-stack");
  const communityEl = document.getElementById("community-cards");
  const playerHandEl = document.getElementById("player-hand");
  const botsEl = document.getElementById("bots");
  const adviceMsgEl = document.getElementById("advice-message");
  const adviceBadgeEl = document.getElementById("advice-badge");
  const adviceActionEl = document.getElementById("advice-action");
  const adviceExplainEl = document.getElementById("advice-explain");
  const handStatusEl = document.getElementById("hand-status");
  const initialScript = document.getElementById("initial-state");
  const tableNoticeEl = document.getElementById("table-notice");
  let lastCounts = { community: 0, log: 0 };
  let audioCtx = null;

  function setActionsEnabled(enabled) {
    actionButtons.forEach((btn) => {
      const realHref = btn.dataset.href || btn.getAttribute("href") || "#";
      if (!btn.dataset.hrefOriginal) {
        btn.dataset.hrefOriginal = realHref;
      }
      if (enabled) {
        btn.classList.remove("disabled", "action-disabled");
        btn.setAttribute("href", btn.dataset.hrefOriginal);
        btn.setAttribute("aria-disabled", "false");
      } else {
        btn.classList.add("disabled", "action-disabled");
        btn.setAttribute("href", "javascript:void(0)");
        btn.setAttribute("aria-disabled", "true");
      }
    });
  }

  function createCardEl(card) {
    const rank = card[0] === "T" ? "10" : card[0];
    const suitCode = card[1];
    const suitMap = { S: "♠", H: "♥", D: "♦", C: "♣" };
    const suit = suitMap[suitCode] || "?";
    const colorClass = suitCode === "H" || suitCode === "D" ? "red" : "black";

    const el = document.createElement("div");
    el.className = `playing-card ${colorClass}`;
    el.innerHTML = `
      <span class="corner tl">${rank}<span class="suit">${suit}</span></span>
      <span class="suit-large">${suit}</span>
      <span class="corner br">${rank}<span class="suit">${suit}</span></span>
    `;
    return el;
  }

  function renderCards(container, cards, { ghosts = 0, animateFrom = 0 } = {}) {
    container.innerHTML = "";
    cards.forEach((card, idx) => {
      const el = createCardEl(card);
      if (idx >= animateFrom) {
        el.classList.add("pop-card");
      }
      container.appendChild(el);
    });
    for (let i = 0; i < ghosts; i++) {
      const ghost = document.createElement("div");
      ghost.className = "playing-card ghost";
      container.appendChild(ghost);
    }
  }

  function renderBots(bots) {
    botsEl.innerHTML = "";
    bots.forEach((bot) => {
      const tag = document.createElement("div");
      tag.className = `bot-tag ${bot.folded ? "bot-folded" : ""}`;
      tag.innerHTML = `<span class="fw-semibold">${bot.name}</span> <span class="small text-secondary">(${bot.stack})</span>${bot.folded ? '<span class="ms-1 text-danger small">folded</span>' : ""}`;
      botsEl.appendChild(tag);
    });
  }

  function renderLog(log) {
    logBox.innerHTML = "";
    log.forEach((entry, idx) => {
      const row = document.createElement("div");
      row.className = "small log-entry";
      row.textContent = entry;
      logBox.appendChild(row);
    });
    logBox.scrollTop = logBox.scrollHeight;
  }

  function renderAdvice(advice) {
    if (advice) {
      adviceMsgEl.textContent = advice.message;
      adviceBadgeEl.textContent = `${advice.win_prob}% win chance`;
      adviceActionEl.textContent = `Suggested action: ${advice.suggested_action}`;
      adviceExplainEl.textContent = advice.explanation || "";
    } else {
      adviceMsgEl.textContent = "Finish the hand or start a new one to see guidance.";
      adviceBadgeEl.textContent = "--";
      adviceActionEl.textContent = "";
      adviceExplainEl.textContent = "";
    }
  }

  function renderState(state) {
    potEl.textContent = state.pot;
    streetEl.textContent = state.street
      ? state.street.charAt(0).toUpperCase() + state.street.slice(1)
      : "Unknown";
    playerStackEl.textContent = state.player?.stack ?? "--";
    const prevCommunity = lastCounts.community || 0;
    const currentCommunity = state.community?.length || 0;
    renderCards(communityEl, state.community || [], {
      ghosts: Math.max(0, 5 - (state.community?.length || 0)),
      animateFrom: Math.min(prevCommunity, state.community?.length || 0),
    });
    renderCards(playerHandEl, state.player?.hand || [], { ghosts: Math.max(0, 2 - (state.player?.hand?.length || 0)) });
    renderBots(state.bots || []);
    renderLog(state.log || []);
    renderAdvice(state.last_advice);

    const isOver = state.street === "hand_over" || state.player?.folded;
    handStatusEl.textContent = isOver ? "Hand complete" : "In progress";
    handStatusEl.className = isOver ? "badge status-badge done" : "badge status-badge active";
    if (tableNoticeEl) {
      tableNoticeEl.textContent = isOver ? "Hand is finished. Start a new hand to keep playing." : "";
      tableNoticeEl.classList.toggle("d-none", !isOver);
    }
    setActionsEnabled(!isOver);

    // Sounds
    if (currentCommunity > prevCommunity) {
      playDealSound();
    } else if ((state.log?.length || 0) > (lastCounts.log || 0)) {
      const lastMsg = state.log[state.log.length - 1] || "";
      if (/win|wins|Showdown/i.test(lastMsg)) {
        playWinSound();
      } else {
        playClickSound();
      }
    }

    lastCounts = { community: currentCommunity, log: state.log?.length || 0 };
  }

  actionButtons.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      if (btn.classList.contains("disabled")) return;
      playClickSound();
      setActionsEnabled(false);
      const url = btn.dataset.hrefOriginal || btn.dataset.href || btn.getAttribute("href");
      fetch(url, {
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
        credentials: "same-origin",
      })
        .then((res) => {
          if (!res.ok) throw new Error("request failed");
          return res.json();
        })
        .then((data) => {
          if (data?.state) {
            renderState(data.state);
          }
        })
        .catch(() => {
          // Keep the user on the page; show a notice if we have one
          if (tableNoticeEl) {
            tableNoticeEl.textContent = "Action failed. Please try again.";
            tableNoticeEl.classList.remove("d-none");
          }
        })
        .finally(() => {
          setActionsEnabled(true);
        });
    });
  });

  if (initialScript) {
    try {
      const initialState = JSON.parse(initialScript.textContent);
      renderState(initialState);
    } catch (err) {
      console.error("Failed to load initial state", err);
    }
  }

  // Sound helpers
  function ensureAudioCtx() {
    if (!audioCtx) {
      const Ctor = window.AudioContext || window.webkitAudioContext;
      if (Ctor) audioCtx = new Ctor();
    }
    return audioCtx;
  }

  function beep(freq, duration = 0.1, volume = 0.05) {
    const ctx = ensureAudioCtx();
    if (!ctx) return;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.value = volume;
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + duration);
  }

  function playClickSound() {
    beep(480, 0.08, 0.06);
  }

  function playDealSound() {
    beep(320, 0.08, 0.05);
    setTimeout(() => beep(260, 0.08, 0.04), 70);
  }

  function playWinSound() {
    beep(660, 0.12, 0.06);
    setTimeout(() => beep(520, 0.12, 0.05), 80);
  }

  function getCsrfToken() {
    const name = "csrftoken";
    const cookies = document.cookie ? document.cookie.split(";") : [];
    for (let i = 0; i < cookies.length; i++) {
      const c = cookies[i].trim();
      if (c.startsWith(name + "=")) {
        return decodeURIComponent(c.slice(name.length + 1));
      }
    }
    return "";
  }
})();
