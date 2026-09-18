const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const SUITS = [
  { code: "s", symbol: "♠", imageName: "spade" },
  { code: "h", symbol: "♥", imageName: "heart" },
  { code: "d", symbol: "♦", imageName: "diamond" },
  { code: "c", symbol: "♣", imageName: "club" },
];
const RANK_IMAGE_TOKEN = {
  A: "1",
  K: "king",
  Q: "queen",
  J: "jack",
  T: "10",
  9: "9",
  8: "8",
  7: "7",
  6: "6",
  5: "5",
  4: "4",
  3: "3",
  2: "2",
};

function cardImageSrc(rank, suitCode) {
  const suit = SUITS.find((s) => s.code === suitCode);
  return `/vendor/svg-cards/cards/${suit.imageName}_${RANK_IMAGE_TOKEN[rank]}.png`;
}

const BOARD_ORDER = ["flop1", "flop2", "flop3", "turn", "river"];
const MAX_OPPONENTS = 8;

function initialSlots() {
  const slots = {
    hero1: null,
    hero2: null,
    flop1: null,
    flop2: null,
    flop3: null,
    turn: null,
    river: null,
  };
  for (let i = 1; i <= MAX_OPPONENTS; i++) {
    slots[`villain${i}_1`] = null;
    slots[`villain${i}_2`] = null;
  }
  return slots;
}

function initialVillainKnown() {
  const known = {};
  for (let i = 1; i <= MAX_OPPONENTS; i++) known[i] = false;
  return known;
}

const state = {
  slots: initialSlots(),
  villainKnown: initialVillainKnown(),
  numOpponents: 1,
  activeSlot: null,
};

const pickerModalEl = document.getElementById("cardPickerModal");
const pickerModal = new bootstrap.Modal(pickerModalEl);
const pickerGrid = document.getElementById("pickerGrid");
const villainsContainer = document.getElementById("villainsContainer");

function usedCards(excludeSlot) {
  return Object.entries(state.slots)
    .filter(([slot, card]) => card && slot !== excludeSlot)
    .map(([, card]) => card);
}

function cardFaceHTML(rank, suitCode) {
  const symbol = SUITS.find((s) => s.code === suitCode).symbol;
  return `<img class="card-image" src="${cardImageSrc(rank, suitCode)}" alt="${rank}${symbol}" draggable="false">`;
}

function renderSlot(slotId) {
  const el = document.querySelector(`[data-slot="${slotId}"]`);
  if (!el) return;
  const card = state.slots[slotId];
  el.classList.remove("suit-h", "suit-d", "suit-s", "suit-c", "filled");
  if (!card) {
    el.textContent = "+";
    return;
  }
  const rank = card[0];
  const suit = card[1];
  el.innerHTML = cardFaceHTML(rank, suit);
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
      btn.innerHTML = cardFaceHTML(rank, suit.code);
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

// Delega: gli slot delle carte avversario sono generati dinamicamente,
// un unico listener sul documento copre sia quelli statici (hero/board) sia quelli dinamici.
document.addEventListener("click", (e) => {
  const slotBtn = e.target.closest(".card-slot");
  if (slotBtn) {
    openPicker(slotBtn.dataset.slot);
  }
});

function renderVillains() {
  let html = "";
  for (let i = 1; i <= state.numOpponents; i++) {
    const known = state.villainKnown[i];
    html += `
      <div class="villain-row mb-2 pb-2 border-bottom border-secondary-subtle">
        <div class="d-flex justify-content-between align-items-center">
          <span class="text-secondary small">Avversario ${i}</span>
          <div class="form-check form-switch mb-0">
            <input class="form-check-input villain-known-toggle" type="checkbox" role="switch"
                   data-villain="${i}" id="villainKnown${i}" ${known ? "checked" : ""}>
            <label class="form-check-label small" for="villainKnown${i}">Conosco le carte</label>
          </div>
        </div>
        <div class="d-flex gap-2 mt-2 ${known ? "" : "d-none"}">
          <button type="button" class="card-slot" data-slot="villain${i}_1">+</button>
          <button type="button" class="card-slot" data-slot="villain${i}_2">+</button>
        </div>
      </div>
    `;
  }
  villainsContainer.innerHTML = html;
  for (let i = 1; i <= state.numOpponents; i++) {
    renderSlot(`villain${i}_1`);
    renderSlot(`villain${i}_2`);
  }
}

villainsContainer.addEventListener("change", (e) => {
  const toggle = e.target.closest(".villain-known-toggle");
  if (!toggle) return;
  const idx = parseInt(toggle.dataset.villain, 10);
  state.villainKnown[idx] = toggle.checked;
  if (!toggle.checked) {
    state.slots[`villain${idx}_1`] = null;
    state.slots[`villain${idx}_2`] = null;
  }
  renderVillains();
});

document.getElementById("tableSize").addEventListener("change", (e) => {
  const tableSize = parseInt(e.target.value, 10);
  state.numOpponents = tableSize - 1;
  for (let i = state.numOpponents + 1; i <= MAX_OPPONENTS; i++) {
    state.villainKnown[i] = false;
    state.slots[`villain${i}_1`] = null;
    state.slots[`villain${i}_2`] = null;
  }
  renderVillains();
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

function collectVillainCards() {
  const villainCards = [];
  for (let i = 1; i <= state.numOpponents; i++) {
    if (!state.villainKnown[i]) continue;
    const c1 = state.slots[`villain${i}_1`];
    const c2 = state.slots[`villain${i}_2`];
    if (!c1 || !c2) {
      throw new Error(`Seleziona entrambe le carte per l'avversario ${i}, oppure disattiva "conosco le carte"`);
    }
    villainCards.push([c1, c2]);
  }
  return villainCards.length > 0 ? villainCards : null;
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

function renderResults(equity, potOdds, ev) {
  document.getElementById("results").classList.remove("d-none");
  document.getElementById("heroEquity").textContent = `${(equity.hero_equity * 100).toFixed(1)}%`;
  document.getElementById("requiredEquity").textContent = `${potOdds.required_equity_percentage.toFixed(1)}%`;

  const evEl = document.getElementById("evValue");
  const evSign = ev.ev > 0 ? "+" : "";
  evEl.textContent = `${evSign}${ev.ev.toFixed(2)}`;
  evEl.classList.toggle("text-success", ev.ev > 0);
  evEl.classList.toggle("text-danger", ev.ev < 0);

  const verdict = document.getElementById("verdict");
  const profitable = ev.profitable;
  verdict.textContent = profitable ? "Call profittevole (EV positivo)" : "Call in perdita (EV negativo)";
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
  let villainCards;
  try {
    board = collectBoard();
    villainCards = collectVillainCards();
  } catch (err) {
    showError(err.message);
    return;
  }

  const potBeforeCall = parseFloat(document.getElementById("potBeforeCall").value || "0");
  const amountToCall = parseFloat(document.getElementById("amountToCall").value || "0");

  const equityPayload = {
    hero_cards: [hero1, hero2],
    board,
    villain_cards: villainCards,
    num_opponents: state.numOpponents,
  };
  const potOddsPayload = { amount_to_call: amountToCall, pot_before_call: potBeforeCall };

  const btn = document.getElementById("calcolaBtn");
  btn.disabled = true;
  btn.textContent = "Calcolo...";
  try {
    const equity = await postJSON("/api/equity", equityPayload);
    const evPayload = {
      hero_equity: equity.hero_equity,
      amount_to_call: amountToCall,
      pot_before_call: potBeforeCall,
    };
    const [potOdds, ev] = await Promise.all([
      postJSON("/api/pot-odds", potOddsPayload),
      postJSON("/api/ev", evPayload),
    ]);
    renderResults(equity, potOdds, ev);
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Calcola";
  }
});

renderAllSlots();
renderVillains();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}
