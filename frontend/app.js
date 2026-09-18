const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"];
const SUITS = [
  { code: "s", symbol: "♠", imageName: "spades" },
  { code: "h", symbol: "♥", imageName: "hearts" },
  { code: "d", symbol: "♦", imageName: "diamonds" },
  { code: "c", symbol: "♣", imageName: "clubs" },
];
const RANK_IMAGE_TOKEN = {
  A: "ace",
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
  return `/vendor/classic-cards/cards/${RANK_IMAGE_TOKEN[rank]}_of_${suit.imageName}.png`;
}

function cardLabel(code) {
  if (!code) return "";
  const suit = SUITS.find((s) => s.code === code[1]);
  return `${code[0]}${suit.symbol}`;
}

function escapeAttr(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
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

function initialVillainModes() {
  const modes = {};
  for (let i = 1; i <= MAX_OPPONENTS; i++) modes[i] = "unknown";
  return modes;
}

function initialVillainRanges() {
  const ranges = {};
  for (let i = 1; i <= MAX_OPPONENTS; i++) ranges[i] = [];
  return ranges;
}

function initialVillainNotes() {
  const notes = {};
  for (let i = 1; i <= MAX_OPPONENTS; i++) notes[i] = "";
  return notes;
}

const state = {
  slots: initialSlots(),
  villainMode: initialVillainModes(), // "unknown" | "known" | "range"
  villainRanges: initialVillainRanges(),
  villainNotes: initialVillainNotes(),
  numOpponents: 1,
  activeSlot: null,
  activeRangeVillain: null,
  positions: { dealer: "hero", sb: "hero", bb: "villain1" },
  // Storico della sessione corrente: solo in memoria, mai persistito (si perde
  // ricaricando la pagina), coerente con il vincolo "nessuna mano salvata".
  history: [],
};
const MAX_HISTORY_ENTRIES = 15;
let lastSummaryText = "";

const pickerModalEl = document.getElementById("cardPickerModal");
const pickerModal = new bootstrap.Modal(pickerModalEl);
const pickerGrid = document.getElementById("pickerGrid");
const villainsContainer = document.getElementById("villainsContainer");
const positionsContainer = document.getElementById("positionsContainer");
const rangeModalEl = document.getElementById("rangeModal");
const rangeModal = new bootstrap.Modal(rangeModalEl);
const rangeGrid = document.getElementById("rangeGrid");

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

const VILLAIN_MODES = [
  { key: "unknown", label: "Ignoto" },
  { key: "known", label: "Note" },
  { key: "range", label: "Range" },
];

function renderVillains() {
  let html = "";
  for (let i = 1; i <= state.numOpponents; i++) {
    const mode = state.villainMode[i];
    const modeButtons = VILLAIN_MODES.map(
      (m) => `
        <button type="button"
                class="btn btn-sm btn-outline-secondary villain-mode-btn ${mode === m.key ? "active" : ""}"
                data-villain="${i}" data-mode="${m.key}">${m.label}</button>
      `
    ).join("");

    let content = "";
    if (mode === "known") {
      content = `
        <div class="d-flex gap-2 mt-2">
          <button type="button" class="card-slot" data-slot="villain${i}_1">+</button>
          <button type="button" class="card-slot" data-slot="villain${i}_2">+</button>
        </div>
      `;
    } else if (mode === "range") {
      const count = state.villainRanges[i].length;
      content = `
        <div class="mt-2">
          <button type="button" class="btn btn-sm btn-outline-success villain-range-btn" data-villain="${i}">
            ${count > 0 ? `Modifica range (${count} classi)` : "Imposta range"}
          </button>
        </div>
      `;
    }

    html += `
      <div class="villain-row mb-2 pb-2 border-bottom border-secondary-subtle">
        <div class="d-flex justify-content-between align-items-center flex-wrap gap-2">
          <span class="text-secondary small">Avversario ${i}</span>
          <div class="btn-group" role="group">${modeButtons}</div>
        </div>
        ${content}
        <input type="text" class="form-control form-control-sm mt-2 villain-note-input" data-villain="${i}"
               placeholder="Note libere (es. aggressivo, bluffa spesso)" value="${escapeAttr(state.villainNotes[i] || "")}">
      </div>
    `;
  }
  villainsContainer.innerHTML = html;
  for (let i = 1; i <= state.numOpponents; i++) {
    if (state.villainMode[i] === "known") {
      renderSlot(`villain${i}_1`);
      renderSlot(`villain${i}_2`);
    }
  }
  updateVillainConsistencyWarning();
}

// Promemoria (non bloccante): se hai personalizzato solo alcuni avversari,
// facile dimenticare gli altri quando il tavolo è pieno.
function updateVillainConsistencyWarning() {
  const warningEl = document.getElementById("villainConsistencyWarning");
  let customized = 0;
  for (let i = 1; i <= state.numOpponents; i++) {
    if (state.villainMode[i] !== "unknown") customized++;
  }
  if (customized > 0 && customized < state.numOpponents) {
    const remaining = state.numOpponents - customized;
    warningEl.textContent = `Hai impostato carte/range per ${customized} avversari su ${state.numOpponents}: gli altri ${remaining} restano a mano ignota/casuale. Verifica che sia corretto prima di calcolare.`;
    warningEl.classList.remove("d-none");
  } else {
    warningEl.classList.add("d-none");
  }
}

villainsContainer.addEventListener("input", (e) => {
  const noteInput = e.target.closest(".villain-note-input");
  if (!noteInput) return;
  // Aggiorna solo lo stato, senza ri-renderizzare: un re-render perderebbe
  // il focus e la posizione del cursore mentre l'utente sta ancora scrivendo.
  state.villainNotes[parseInt(noteInput.dataset.villain, 10)] = noteInput.value;
});

villainsContainer.addEventListener("click", (e) => {
  const modeBtn = e.target.closest(".villain-mode-btn");
  if (modeBtn) {
    const idx = parseInt(modeBtn.dataset.villain, 10);
    const mode = modeBtn.dataset.mode;
    state.villainMode[idx] = mode;
    if (mode !== "known") {
      state.slots[`villain${idx}_1`] = null;
      state.slots[`villain${idx}_2`] = null;
    }
    if (mode !== "range") {
      state.villainRanges[idx] = [];
    }
    renderVillains();
    return;
  }

  const rangeBtn = e.target.closest(".villain-range-btn");
  if (rangeBtn) {
    openRangeModal(parseInt(rangeBtn.dataset.villain, 10));
  }
});

function rangeCellLabel(row, col) {
  const higher = RANKS[Math.min(row, col)];
  const lower = RANKS[Math.max(row, col)];
  if (row === col) return `${higher}${higher}`;
  return row < col ? `${higher}${lower}s` : `${higher}${lower}o`;
}

function buildRangeGrid() {
  const idx = state.activeRangeVillain;
  const selected = new Set(state.villainRanges[idx]);
  let html = "";
  for (let row = 0; row < RANKS.length; row++) {
    for (let col = 0; col < RANKS.length; col++) {
      const label = rangeCellLabel(row, col);
      const isPair = row === col;
      html += `
        <button type="button" class="range-cell ${isPair ? "pair" : ""} ${selected.has(label) ? "selected" : ""}"
                data-label="${label}">${label}</button>
      `;
    }
  }
  rangeGrid.innerHTML = html;
  updateRangeSummary();
}

function allPlacedCards() {
  return Object.values(state.slots).filter(Boolean);
}

async function updateRangeSummary() {
  const idx = state.activeRangeVillain;
  const labels = state.villainRanges[idx];
  const count = labels.length;
  const summaryEl = document.getElementById("rangeSummary");
  summaryEl.textContent = `${count} classi selezionate`;
  if (count === 0) return;

  try {
    const { combo_count } = await postJSON("/api/range-combo-count", {
      labels,
      known_cards: allPlacedCards(),
    });
    // L'utente potrebbe aver cambiato avversario/selezione mentre la richiesta era in volo.
    if (state.activeRangeVillain !== idx) return;
    summaryEl.textContent = `${count} classi selezionate · ${combo_count} combo utilizzabili`;
  } catch (err) {
    // Non blocchiamo l'uso del range picker se il conteggio combo fallisce: è solo informativo.
  }
}

function openRangeModal(idx) {
  state.activeRangeVillain = idx;
  document.getElementById("rangeModalTitle").textContent = `Range avversario ${idx}`;
  buildRangeGrid();
  rangeModal.show();
}

rangeGrid.addEventListener("click", (e) => {
  const cell = e.target.closest(".range-cell");
  if (!cell) return;
  const idx = state.activeRangeVillain;
  const label = cell.dataset.label;
  const current = state.villainRanges[idx];
  const position = current.indexOf(label);
  if (position === -1) {
    current.push(label);
    cell.classList.add("selected");
  } else {
    current.splice(position, 1);
    cell.classList.remove("selected");
  }
  updateRangeSummary();
});

document.getElementById("clearRangeBtn").addEventListener("click", () => {
  const idx = state.activeRangeVillain;
  state.villainRanges[idx] = [];
  buildRangeGrid();
});

rangeModalEl.addEventListener("hidden.bs.modal", () => {
  renderVillains();
});

function playerOptionsHTML(selectedValue) {
  let html = `<option value="hero" ${selectedValue === "hero" ? "selected" : ""}>Io</option>`;
  for (let i = 1; i <= state.numOpponents; i++) {
    html += `<option value="villain${i}" ${selectedValue === `villain${i}` ? "selected" : ""}>Avversario ${i}</option>`;
  }
  return html;
}

function renderPositions() {
  const roles = [
    { key: "dealer", label: "Dealer" },
    { key: "sb", label: "Small Blind" },
    { key: "bb", label: "Big Blind" },
  ];
  positionsContainer.innerHTML = roles
    .map(
      (role) => `
        <div class="col-4">
          <label class="form-label text-secondary text-uppercase small mb-1" for="position-${role.key}">${role.label}</label>
          <select class="form-select form-select-sm position-select" id="position-${role.key}" data-role="${role.key}">
            ${playerOptionsHTML(state.positions[role.key])}
          </select>
        </div>
      `
    )
    .join("");
}

positionsContainer.addEventListener("change", (e) => {
  const select = e.target.closest(".position-select");
  if (!select) return;
  state.positions[select.dataset.role] = select.value;
});

document.getElementById("tableSize").addEventListener("change", (e) => {
  const tableSize = parseInt(e.target.value, 10);
  state.numOpponents = tableSize - 1;
  for (let i = state.numOpponents + 1; i <= MAX_OPPONENTS; i++) {
    state.villainMode[i] = "unknown";
    state.villainRanges[i] = [];
    state.villainNotes[i] = "";
    state.slots[`villain${i}_1`] = null;
    state.slots[`villain${i}_2`] = null;
  }
  renderVillains();
  renderPositions();
});

document.getElementById("useBlindsBtn").addEventListener("click", () => {
  const sb = parseFloat(document.getElementById("smallBlind").value || "0");
  const bb = parseFloat(document.getElementById("bigBlind").value || "0");
  document.getElementById("potBeforeCall").value = (sb + bb).toFixed(2);
  updateBBHints();
});

// Scorciatoie ÷2/×2: utili quando si ragiona per size relative alla puntata
// avversaria ("e se puntasse il doppio?") senza dover ricalcolare a mano.
function scaleField(inputId, factor) {
  const input = document.getElementById(inputId);
  const current = parseFloat(input.value || "0");
  input.value = (current * factor).toFixed(2);
  updateBBHints();
  updateImpliedMaxHint();
}

document.getElementById("halveCallBtn").addEventListener("click", () => scaleField("amountToCall", 0.5));
document.getElementById("doubleCallBtn").addEventListener("click", () => scaleField("amountToCall", 2));
document.getElementById("halveShoveBtn").addEventListener("click", () => scaleField("shoveAmount", 0.5));
document.getElementById("doubleShoveBtn").addEventListener("click", () => scaleField("shoveAmount", 2));

// Conversione rapida €->BB: in cash game si ragiona spesso in big blind piuttosto
// che in valuta assoluta, mostrata come semplice testo informativo sotto ogni campo.
const BB_HINT_FIELDS = [
  { inputId: "potBeforeCall", hintId: "potBeforeCallBB" },
  { inputId: "amountToCall", hintId: "amountToCallBB" },
  { inputId: "shoveAmount", hintId: "shoveAmountBB" },
];

function updateBBHints() {
  const bb = parseFloat(document.getElementById("bigBlind").value || "0");
  BB_HINT_FIELDS.forEach(({ inputId, hintId }) => {
    const amount = parseFloat(document.getElementById(inputId).value || "0");
    const hintEl = document.getElementById(hintId);
    hintEl.textContent = bb > 0 && amount > 0 ? `= ${(amount / bb).toFixed(1)} BB` : "";
  });
}

BB_HINT_FIELDS.forEach(({ inputId }) => {
  document.getElementById(inputId).addEventListener("input", updateBBHints);
});
document.getElementById("bigBlind").addEventListener("input", updateBBHints);

document.getElementById("useBuyInBtn").addEventListener("click", () => {
  const buyIn = parseFloat(document.getElementById("buyIn").value || "0");
  document.getElementById("shoveAmount").value = buyIn.toFixed(2);
});

document.getElementById("useBuyInStackBtn").addEventListener("click", () => {
  const buyIn = parseFloat(document.getElementById("buyIn").value || "0");
  document.getElementById("effectiveStack").value = buyIn.toFixed(2);
  updateImpliedMaxHint();
});

// Tetto teorico per le implied odds: non è una previsione di quanto pagherà
// l'avversario (dipenderebbe dal suo comportamento futuro, terreno di un
// solver), solo il vincolo fisico "non puoi vincere più di quanto resta negli
// stack". Rispecchia calculate_max_implied_bet in engine/metrics.py.
function maxImpliedBet() {
  const effectiveStack = parseFloat(document.getElementById("effectiveStack").value || "0");
  const amountToCall = parseFloat(document.getElementById("amountToCall").value || "0");
  return Math.max(0, effectiveStack - amountToCall);
}

function updateImpliedMaxHint() {
  const effectiveStack = parseFloat(document.getElementById("effectiveStack").value || "0");
  const hintEl = document.getElementById("impliedMaxHint");
  if (effectiveStack > 0) {
    hintEl.textContent = `Max teorico: €${maxImpliedBet().toFixed(2)} (stack residuo dopo la chiamata)`;
  } else {
    hintEl.textContent = "Puntate future stimate se vinci a showdown.";
  }
}

document.getElementById("effectiveStack").addEventListener("input", updateImpliedMaxHint);
document.getElementById("amountToCall").addEventListener("input", updateImpliedMaxHint);

document.getElementById("useMaxImpliedBtn").addEventListener("click", () => {
  document.getElementById("impliedFutureBet").value = maxImpliedBet().toFixed(2);
});

document.getElementById("enableShove").addEventListener("change", (e) => {
  document.getElementById("shoveInputs").classList.toggle("d-none", !e.target.checked);
  document.getElementById("shoveResultCard").classList.add("d-none");
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
    if (state.villainMode[i] !== "known") continue;
    const c1 = state.slots[`villain${i}_1`];
    const c2 = state.slots[`villain${i}_2`];
    if (!c1 || !c2) {
      throw new Error(`Seleziona entrambe le carte per l'avversario ${i}, oppure cambia modalità`);
    }
    villainCards.push([c1, c2]);
  }
  return villainCards.length > 0 ? villainCards : null;
}

function collectVillainRanges() {
  const villainRanges = [];
  for (let i = 1; i <= state.numOpponents; i++) {
    if (state.villainMode[i] !== "range") continue;
    const labels = state.villainRanges[i];
    if (labels.length === 0) {
      throw new Error(`Imposta almeno una classe di mano nel range dell'avversario ${i}, oppure cambia modalità`);
    }
    villainRanges.push(labels);
  }
  return villainRanges.length > 0 ? villainRanges : null;
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

function renderResults(equity, potOdds, ev, shoveEv, tableMetrics, impliedFutureBet) {
  document.getElementById("results").classList.remove("d-none");
  document.getElementById("heroEquity").textContent = `${(equity.hero_equity * 100).toFixed(1)}%`;
  document.getElementById("requiredEquity").textContent = `${potOdds.required_equity_percentage.toFixed(1)}%`;

  const confidenceEl = document.getElementById("equityConfidence");
  if (equity.ci_low != null && equity.ci_high != null) {
    confidenceEl.textContent = `IC 95%: ${(equity.ci_low * 100).toFixed(1)}% - ${(equity.ci_high * 100).toFixed(1)}%`;
    confidenceEl.classList.remove("d-none");
  } else {
    confidenceEl.classList.add("d-none");
  }

  const metricsRow = document.getElementById("tableMetricsRow");
  if (tableMetrics && (tableMetrics.spr != null || tableMetrics.mdf != null)) {
    metricsRow.classList.remove("d-none");
    document.getElementById("sprValue").textContent = tableMetrics.spr != null ? tableMetrics.spr.toFixed(1) : "-";
    document.getElementById("mdfValue").textContent =
      tableMetrics.mdf != null ? `${(tableMetrics.mdf * 100).toFixed(1)}%` : "-";
  } else {
    metricsRow.classList.add("d-none");
  }

  const evEl = document.getElementById("evValue");
  const evSign = ev.ev > 0 ? "+" : "";
  evEl.textContent = `${evSign}${ev.ev.toFixed(2)}`;
  evEl.classList.toggle("text-success", ev.ev > 0);
  evEl.classList.toggle("text-danger", ev.ev < 0);

  const impliedWarningEl = document.getElementById("impliedWarning");
  if (tableMetrics && impliedFutureBet > tableMetrics.max_implied_bet + 0.01) {
    impliedWarningEl.textContent = `Le implied odds inserite (€${impliedFutureBet.toFixed(2)}) superano il tetto teorico di €${tableMetrics.max_implied_bet.toFixed(2)}: l'EV potrebbe essere ottimistico.`;
    impliedWarningEl.classList.remove("d-none");
  } else {
    impliedWarningEl.classList.add("d-none");
  }

  const shoveCard = document.getElementById("shoveResultCard");
  if (shoveEv) {
    shoveCard.classList.remove("d-none");
    const shoveEl = document.getElementById("shoveEvValue");
    const shoveSign = shoveEv.ev > 0 ? "+" : "";
    shoveEl.textContent = `${shoveSign}${shoveEv.ev.toFixed(2)}`;
    shoveEl.classList.toggle("text-success", shoveEv.ev > 0);
    shoveEl.classList.toggle("text-danger", shoveEv.ev < 0);
  } else {
    shoveCard.classList.add("d-none");
  }

  const verdict = document.getElementById("verdict");
  const profitable = shoveEv ? shoveEv.profitable : ev.profitable;
  const verdictLabel = shoveEv ? "shove" : "call";
  verdict.textContent = profitable ? `EV positivo (${verdictLabel})` : `EV negativo (${verdictLabel})`;
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

function buildSummaryText(heroCards, board, numOpponents, equity, potOdds, ev, shoveEv, tableMetrics) {
  const heroLabel = `${cardLabel(heroCards[0])} ${cardLabel(heroCards[1])}`;
  const boardLabel = board.length > 0 ? board.map(cardLabel).join(" ") : "preflop";
  const lines = [
    `${heroLabel} su ${boardLabel} (vs ${numOpponents} avversari)`,
    `Equity: ${(equity.hero_equity * 100).toFixed(1)}%` +
      (equity.ci_low != null ? ` (IC95%: ${(equity.ci_low * 100).toFixed(1)}-${(equity.ci_high * 100).toFixed(1)}%)` : "") +
      ` | Richiesta: ${potOdds.required_equity_percentage.toFixed(1)}%`,
    `EV chiamata: ${ev.ev > 0 ? "+" : ""}${ev.ev.toFixed(2)}€` +
      (tableMetrics && tableMetrics.spr != null ? ` | SPR: ${tableMetrics.spr.toFixed(1)}` : "") +
      (tableMetrics && tableMetrics.mdf != null ? ` | MDF: ${(tableMetrics.mdf * 100).toFixed(1)}%` : ""),
  ];
  if (shoveEv) {
    lines.push(`EV shove: ${shoveEv.ev > 0 ? "+" : ""}${shoveEv.ev.toFixed(2)}€`);
  }
  const verdictLabel = shoveEv ? "shove" : "call";
  const profitable = shoveEv ? shoveEv.profitable : ev.profitable;
  lines.push(`Verdetto: EV ${profitable ? "positivo" : "negativo"} (${verdictLabel})`);
  return lines.join("\n");
}

async function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }
  // Fallback per contesti non sicuri (es. accesso via IP in LAN senza HTTPS)
  // dove l'API Clipboard moderna non è disponibile.
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  textarea.select();
  document.execCommand("copy");
  document.body.removeChild(textarea);
}

document.getElementById("copySummaryBtn").addEventListener("click", async () => {
  const btn = document.getElementById("copySummaryBtn");
  try {
    await copyToClipboard(lastSummaryText);
    const originalLabel = btn.textContent;
    btn.textContent = "Copiato!";
    setTimeout(() => {
      btn.textContent = originalLabel;
    }, 1500);
  } catch (err) {
    showError("Impossibile copiare negli appunti su questo browser.");
  }
});

function renderHistory() {
  const listEl = document.getElementById("historyList");
  const emptyEl = document.getElementById("historyEmpty");
  const clearBtn = document.getElementById("clearHistoryBtn");

  if (state.history.length === 0) {
    listEl.innerHTML = "";
    emptyEl.classList.remove("d-none");
    clearBtn.classList.add("d-none");
    return;
  }

  emptyEl.classList.add("d-none");
  clearBtn.classList.remove("d-none");
  listEl.innerHTML = state.history
    .map((entry) => {
      const evClass = entry.ev > 0 ? "text-success" : entry.ev < 0 ? "text-danger" : "";
      const evSign = entry.ev > 0 ? "+" : "";
      const boardLabel = entry.board.length > 0 ? entry.board.map(cardLabel).join(" ") : "preflop";
      return `
        <div class="history-item">
          <div>
            <div class="fw-semibold">${cardLabel(entry.heroCards[0])} ${cardLabel(entry.heroCards[1])} · ${boardLabel}</div>
            <div class="text-secondary" style="font-size: 0.75rem;">${entry.time} · vs ${entry.numOpponents} avversari</div>
          </div>
          <div class="text-end">
            <div>${(entry.heroEquity * 100).toFixed(1)}%</div>
            <div class="${evClass}">${evSign}${entry.ev.toFixed(2)}€</div>
          </div>
        </div>
      `;
    })
    .join("");
}

function pushHistoryEntry(entry) {
  state.history.unshift(entry);
  if (state.history.length > MAX_HISTORY_ENTRIES) {
    state.history.length = MAX_HISTORY_ENTRIES;
  }
  renderHistory();
}

document.getElementById("clearHistoryBtn").addEventListener("click", () => {
  state.history = [];
  renderHistory();
});

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
  let villainRanges;
  try {
    board = collectBoard();
    villainCards = collectVillainCards();
    villainRanges = collectVillainRanges();
  } catch (err) {
    showError(err.message);
    return;
  }

  const potBeforeCall = parseFloat(document.getElementById("potBeforeCall").value || "0");
  const amountToCall = parseFloat(document.getElementById("amountToCall").value || "0");
  const effectiveStack = parseFloat(document.getElementById("effectiveStack").value || "0");
  const impliedFutureBet = parseFloat(document.getElementById("impliedFutureBet").value || "0");

  const equityPayload = {
    hero_cards: [hero1, hero2],
    board,
    villain_cards: villainCards,
    villain_ranges: villainRanges,
    num_opponents: state.numOpponents,
  };
  const potOddsPayload = { amount_to_call: amountToCall, pot_before_call: potBeforeCall };
  const tableMetricsPayload = {
    effective_stack: effectiveStack,
    pot_before_call: potBeforeCall,
    amount_to_call: amountToCall,
  };

  const shoveEnabled = document.getElementById("enableShove").checked;
  let shoveAmount = 0;
  let foldProbability = 0;
  if (shoveEnabled) {
    shoveAmount = parseFloat(document.getElementById("shoveAmount").value || "0");
    const foldPercentage = parseFloat(document.getElementById("foldProbability").value || "0");
    if (foldPercentage < 0 || foldPercentage > 100) {
      showError("La fold % deve essere tra 0 e 100");
      return;
    }
    foldProbability = foldPercentage / 100;
  }

  const btn = document.getElementById("calcolaBtn");
  btn.disabled = true;
  btn.textContent = "Calcolo...";
  try {
    // Pot odds e table-metrics non dipendono dall'equity: le avviamo subito
    // invece di aspettare che l'equity (Monte Carlo, potenzialmente lenta) sia pronta.
    const potOddsPromise = postJSON("/api/pot-odds", potOddsPayload);
    const tableMetricsPromise = postJSON("/api/table-metrics", tableMetricsPayload);
    const equity = await postJSON("/api/equity", equityPayload);
    const evPayload = {
      hero_equity: equity.hero_equity,
      amount_to_call: amountToCall,
      pot_before_call: potBeforeCall,
      implied_future_bet: impliedFutureBet,
    };
    const requests = [potOddsPromise, tableMetricsPromise, postJSON("/api/ev", evPayload)];
    if (shoveEnabled) {
      requests.push(
        postJSON("/api/shove-ev", {
          hero_equity_if_called: equity.hero_equity,
          fold_probability: foldProbability,
          pot_before_shove: potBeforeCall,
          shove_amount: shoveAmount,
        })
      );
    }
    const [potOdds, tableMetrics, ev, shoveEv] = await Promise.all(requests);
    renderResults(equity, potOdds, ev, shoveEv, tableMetrics, impliedFutureBet);
    lastSummaryText = buildSummaryText([hero1, hero2], board, state.numOpponents, equity, potOdds, ev, shoveEv, tableMetrics);
    pushHistoryEntry({
      time: new Date().toLocaleTimeString("it-IT"),
      heroCards: [hero1, hero2],
      board,
      numOpponents: state.numOpponents,
      heroEquity: equity.hero_equity,
      ev: shoveEv ? shoveEv.ev : ev.ev,
    });
  } catch (err) {
    showError(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "Calcola";
  }
});

renderAllSlots();
renderVillains();
renderPositions();
renderHistory();
updateBBHints();
updateImpliedMaxHint();

// Icone "i" informative: popover al tocco (trigger "focus" invece di "hover",
// così funzionano anche su smartphone) che si chiudono toccando altrove.
document.querySelectorAll('[data-bs-toggle="popover"]').forEach((el) => new bootstrap.Popover(el));

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("/service-worker.js").catch(() => {});
  });
}
