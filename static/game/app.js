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
  const aiNoteRow = document.getElementById("ai-note-row");
  const aiSpinner = document.getElementById("ai-spinner");
  const aiNoteText = document.getElementById("ai-note-text");
  const loadingOverlay = document.getElementById("loading-overlay");
  const loadingText = document.getElementById("loading-text");
  const handStatusEl = document.getElementById("hand-status");
  const initialScript = document.getElementById("initial-state");
  const tableNoticeEl = document.getElementById("table-notice");
  let lastCounts = { community: 0, log: 0 };
  let audioCtx = null;
  let currentState = null;
  let aiPending = false;
  let lastAiKey = null;

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

  function setLoading(show, text = "Loading...") {
    if (!loadingOverlay) return;
    if (loadingText) loadingText.textContent = text;
    loadingOverlay.classList.toggle("d-none", !show);
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

  function createBackCard() {
    const el = document.createElement("div");
    el.className = "playing-card back";
    el.innerHTML = `<span class="corner tl">★</span><span class="suit-large">♠</span><span class="corner br">★</span>`;
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

  function renderBots(bots, reveal = false) {
    botsEl.innerHTML = "";
    (bots || []).forEach((bot) => {
      const tag = document.createElement("div");
      tag.className = `bot-tag ${bot.folded ? "bot-folded" : ""}`;
      const cardsWrap = document.createElement("div");
      cardsWrap.className = "cards d-flex gap-2";

      if (reveal && !bot.folded) {
        (bot.hand || []).forEach((c) => cardsWrap.appendChild(createCardEl(c)));
      } else if (reveal && bot.folded) {
        (bot.hand || []).forEach(() => cardsWrap.appendChild(createBackCard()));
      } else {
        cardsWrap.appendChild(createBackCard());
        cardsWrap.appendChild(createBackCard());
      }

      const text = document.createElement("div");
      text.className = "text-center";
      text.innerHTML = `<div class="fw-semibold">${bot.name}</div><div class="small text-secondary">(${bot.stack})${bot.folded ? ' · <span class="text-danger">folded</span>' : ""}</div>`;
      tag.appendChild(cardsWrap);
      tag.appendChild(text);
      botsEl.appendChild(tag);
    });
  }

  function renderLog(log) {
    logBox.innerHTML = "";
    (log || []).forEach((entry) => {
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
      let base = advice.explanation || "";
      if (base.includes("AI guidance:")) {
        base = base.split("AI guidance:")[0].trim();
      }
      const aiNote = advice.ai_note;
      adviceExplainEl.textContent = base;
      if (aiNoteRow) {
        aiNoteRow.classList.remove("d-none");
        aiNoteText.textContent = aiNote || "AI tip pending...";
        const pending = !aiNote || /pending/i.test(aiNote);
        if (aiSpinner) {
          aiSpinner.classList.toggle("d-none", !pending);
        }
      }
    } else {
      adviceMsgEl.textContent = "Finish the hand or start a new one to see guidance.";
      adviceBadgeEl.textContent = "--";
      adviceActionEl.textContent = "";
      adviceExplainEl.textContent = "";
      if (aiNoteRow) aiNoteRow.classList.add("d-none");
    }
  }

  function aiKey(state) {
    return `${state.street}-${state.community?.length || 0}-${state.log?.length || 0}`;
  }

  function maybeFetchAi(state) {
    const advice = state?.last_advice || {};
    const aiNote = advice.ai_note || "";
    const needsAi = !aiNote || /pending|unavailable/i.test(aiNote);
    const key = aiKey(state);
    if (!needsAi) {
      aiPending = false;
      lastAiKey = key;
      return;
    }
    if (aiPending && lastAiKey === key) return;
    aiPending = true;
    lastAiKey = key;
    if (aiNoteText && (!aiNote || /pending|unavailable/i.test(aiNote))) {
      aiNoteText.textContent = "AI tip pending...";
    }
    if (aiSpinner) aiSpinner.classList.remove("d-none");
    fetch("/ai-tip/", {
      method: "GET",
      headers: { "X-Requested-With": "XMLHttpRequest" },
      credentials: "same-origin",
    })
      .then((res) => res.json())
      .then((data) => {
        aiPending = false;
        if (data?.ai_note && currentState) {
          currentState.last_advice = currentState.last_advice || {};
          currentState.last_advice.ai_note = data.ai_note;
          renderAdvice(currentState.last_advice);
        } else if (data?.ai_note && !currentState) {
          adviceExplainEl.textContent = adviceExplainEl.textContent;
          if (aiNoteText) aiNoteText.textContent = data.ai_note;
          if (aiSpinner) aiSpinner.classList.add("d-none");
        }
      })
      .catch(() => {
        aiPending = false;
        if (aiSpinner) aiSpinner.classList.add("d-none");
      });
  }

  function renderState(state) {
    currentState = state;
    potEl.textContent = state.pot;
    streetEl.textContent = state.street
      ? state.street.charAt(0).toUpperCase() + state.street.slice(1)
      : "Unknown";
    playerStackEl.textContent = state.player?.stack ?? "--";
    const isOver = state.street === "hand_over" || state.player?.folded;
    const isAllIn = !!state.player?.all_in || state.player?.stack === 0;
    const prevCommunity = lastCounts.community || 0;
    const currentCommunity = state.community?.length || 0;
    renderCards(communityEl, state.community || [], {
      ghosts: Math.max(0, 5 - (state.community?.length || 0)),
      animateFrom: Math.min(prevCommunity, state.community?.length || 0),
    });
    renderCards(playerHandEl, state.player?.hand || [], {
      ghosts: Math.max(0, 2 - (state.player?.hand?.length || 0)),
    });
    renderBots(state.bots || [], isOver);
    renderLog(state.log || []);
    renderAdvice(state.last_advice);
    maybeFetchAi(state);

    handStatusEl.textContent = isOver ? "Hand complete" : "In progress";
    if (isOver) {
      handStatusEl.className = "badge status-badge done";
    } else if (isAllIn) {
      handStatusEl.textContent = "All-in";
      handStatusEl.className = "badge status-badge active";
    } else {
      handStatusEl.className = "badge status-badge active";
    }
    if (tableNoticeEl) {
      if (isOver) {
        tableNoticeEl.textContent = "Hand is finished. Start a new hand to keep playing.";
        tableNoticeEl.classList.remove("d-none");
      } else if (isAllIn) {
        tableNoticeEl.textContent = "You are all-in. Waiting for showdown.";
        tableNoticeEl.classList.remove("d-none");
      } else {
        tableNoticeEl.classList.add("d-none");
      }
    }
    const forcedShove =
      !isOver &&
      !isAllIn &&
      (state.pending_call || 0) > 0 &&
      (state.pending_call || 0) >= (state.player?.stack || 0);

    setActionsEnabled(!isOver && !isAllIn);
    if (forcedShove) {
      actionButtons.forEach((btn) => {
        const move = btn.dataset.move;
        if (move === "call" || move === "raise") {
          btn.classList.add("disabled", "action-disabled");
          btn.setAttribute("href", "javascript:void(0)");
          btn.setAttribute("aria-disabled", "true");
        }
      });
      if (tableNoticeEl) {
        tableNoticeEl.textContent = "Facing all-in: you can fold or call all-in.";
        tableNoticeEl.classList.remove("d-none");
      }
    }

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
      const beforeLog = lastCounts.log || 0;
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
          if (tableNoticeEl) {
            tableNoticeEl.textContent = "Action failed. Please try again.";
            tableNoticeEl.classList.remove("d-none");
          }
        })
        .finally(() => {
          // Simulate bot thinking time based on how many new log lines arrived.
          const newLogCount = (currentState?.log?.length || 0) - beforeLog;
          const delay = Math.min(1500, 400 + Math.max(newLogCount, 1) * 180);
          setTimeout(() => setActionsEnabled(true), delay);
        });
    });
  });

  const startHandBtn = document.querySelector(".start-hand");
  if (startHandBtn) {
    startHandBtn.addEventListener("click", () => {
      setLoading(true, "Starting new hand...");
    });
  }

  if (initialScript) {
    try {
      const initialState = JSON.parse(initialScript.textContent);
      renderState(initialState);
    } catch (err) {
      console.error("Failed to load initial state", err);
    }
  }

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
})();
