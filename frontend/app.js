const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const SUITS = [
  { code: "s", symbol: "♠" },
  { code: "h", symbol: "♥" },
  { code: "d", symbol: "♦" },
  { code: "c", symbol: "♣" },
];

const BOARD_ORDER = ["flop1", "flop2", "flop3", "turn", "river"];

const state = {
  slots: {
    hero1: null,
    hero2: null,
    flop1: null,
    flop2: null,
    flop3: null,
    turn: null,
    river: null,
    villain1: null,
    villain2: null,
  },
  activeSlot: null,
};

const pickerModalEl = document.getElementById("cardPickerModal");
const pickerModal = new bootstrap.Modal(pickerModalEl);
const pickerGrid = document.getElementById("pickerGrid");

function usedCards(excludeSlot) {
  return Object.entries(state.slots)
    .filter(([slot, card]) => card && slot !== excludeSlot)
    .map(([, card]) => card);
}

function renderSlot(slotId) {
  const el = document.querySelector(`[data-slot="${slotId}"]`);
  const card = state.slots[slotId];
  el.classList.remove("suit-h", "suit-d", "suit-s", "suit-c", "filled");
  if (!card) {
    el.textContent = "+";
    return;
  }
  const rank = card[0];
  const suit = card[1];
  const symbol = SUITS.find((s) => s.code === suit).symbol;
  el.textContent = `${rank}${symbol}`;
  el.classList.add("filled", `suit-${suit}`);
}

function renderAllSlots() {
  Object.keys(state.slots).forEach(renderSlot);
}

function buildPickerGrid() {
  pickerGrid.innerHTML = "";
  const excluded = usedCards(state.activeSlot);
  SUITS.forEach((suit) => {
    RANKS.forEach((rank) => {
      const code = `${rank}${suit.code}`;
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = `picker-card suit-${suit.code}`;
      btn.textContent = `${rank}${suit.symbol}`;
      btn.disabled = excluded.includes(code);
      btn.addEventListener("click", () => selectCard(code));
      pickerGrid.appendChild(btn);
    });
  });
}

function openPicker(slotId) {
  state.activeSlot = slotId;
  buildPickerGrid();
  pickerModal.show();
}

function selectCard(code) {
  state.slots[state.activeSlot] = code;
  renderSlot(state.activeSlot);
  pickerModal.hide();
}

document.getElementById("clearSlotBtn").addEventListener("click", () => {
  if (state.activeSlot) {
    state.slots[state.activeSlot] = null;
    renderSlot(state.activeSlot);
  }
  pickerModal.hide();
});

document.querySelectorAll(".card-slot").forEach((btn) => {
  btn.addEventListener("click", () => openPicker(btn.dataset.slot));
});

document.getElementById("knowVillain").addEventListener("change", (e) => {
  const villainSlots = document.getElementById("villainSlots");
  villainSlots.classList.toggle("d-none", !e.target.checked);
  if (!e.target.checked) {
    state.slots.villain1 = null;
    state.slots.villain2 = null;
    renderSlot("villain1");
    renderSlot("villain2");
  }
});

function collectBoard() {
  const filled = BOARD_ORDER.map((slot) => state.slots[slot]);
  const filledCount = filled.filter(Boolean).length;

  if (filledCount === 0) return [];

  // Flop: le prime 3 devono essere tutte piene o tutte vuote.
  const flopFilled = filled.slice(0, 3).filter(Boolean).length;
  if (flopFilled !== 0 && flopFilled !== 3) {
    throw new Error("Completa tutte e 3 le carte del flop prima di proseguire");
  }
  if (state.slots.turn && flopFilled !== 3) {
    throw new Error("Inserisci il flop prima del turn");
  }
  if (state.slots.river && !state.slots.turn) {
    throw new Error("Inserisci il turn prima del river");
  }

  return filled.filter(Boolean);
}

function showError(message) {
  const box = document.getElementById("errorBox");
  box.textContent = message;
  box.classList.remove("d-none");
}

function hideError() {
  document.getElementById("errorBox").classList.add("d-none");
}

async function postJSON(url, payload) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const body = await response.json();
  if (!response.ok) {
    const detail = Array.isArray(body.detail)
      ? body.detail.map((d) => d.msg).join("; ")
      : body.detail || "Errore nella richiesta";
    throw new Error(detail);
  }
  return body;
}

function renderResults(equity, potOdds) {
  document.getElementById("results").classList.remove("d-none");
  document.getElementById("heroEquity").textContent = `${(equity.hero_equity * 100).toFixed(1)}%`;
  document.getElementById("requiredEquity").textContent = `${potOdds.required_equity_percentage.toFixed(1)}%`;

  const verdict = document.getElementById("verdict");
  const profitable = equity.hero_equity > potOdds.required_equity;
  verdict.textContent = profitable ? "Call profittevole" : "Call in perdita";
  verdict.className = `alert text-center fw-bold ${profitable ? "alert-success" : "alert-danger"}`;

  const methodLabels = {
    monte_carlo: "Monte Carlo",
    exact_enumeration: "Enumerazione esatta",
    direct_comparison: "Confronto diretto",
  };
  document.getElementById("meta").textContent =
    `${methodLabels[equity.method] || equity.method} · ${equity.trials} scenari` +
    (equity.tie_probability > 0 ? ` · split ${(equity.tie_probability * 100).toFixed(1)}%` : "");
}

document.getElementById("calcolaBtn").addEventListener("click", async () => {
  hideError();

  const hero1 = state.slots.hero1;
  const hero2 = state.slots.hero2;
  if (!hero1 || !hero2) {
    showError("Seleziona entrambe le tue carte");
    return;
  }

  let board;
  try {
    board = collectBoard();
  } catch (err) {
    showError(err.message);
    return;
  }

  const knowVillain = document.getElementById("knowVillain").checked;
  const villain1 = state.slots.villain1;
  const villain2 = state.slots.villain2;
  let villainCards = null;
  if (knowVillain) {
    if (!villain1 || !villain2) {
      showError("Seleziona entrambe le carte dell'avversario, oppure disattiva l'opzione");
      return;
    }
    villainCards = [[villain1, villain2]];
  }

  const numOpponents = parseInt(document.getElementById("numOpponents").value, 10);
  const potBeforeCall = parseFloat(document.getElementById("potBeforeCall").value || "0");
  const amountToCall = parseFloat(document.getElementById("amountToCall").value || "0");

  const equityPayload = {
    hero_cards: [hero1, hero2],
    board,
    villain_cards: villainCards,
    num_opponents: numOpponents,
  };
  const potOddsPayload = { amount_to_call: amountToCall, pot_before_call: potBeforeCall };

  const btn = document.getElementById("calcolaBtn");
  btn.disabled = true;
  btn.textContent = "Calcolo...";
  try {
    const [equity, potOdds] = await Promise.all([
      postJSON("/api/equity", equityPayload),
      postJSON("/api/pot-odds", potOddsPayload),
    ]);
    renderResults(equity, potOdds);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Calcola";
  }
});

renderAllSlots();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}
