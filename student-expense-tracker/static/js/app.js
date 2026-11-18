// app.js - the browser side. It talks to Flask ONLY through fetch() calls to /api/...
// Idea: the HTML page never stores data itself. Every change goes to the server, then we reload from it.

// ---------- 1. Shared state and small helpers ----------
const state = {
  month: "",          // selected month, like "2026-10"
  editingId: null,    // id of the expense being edited (null = adding a new one)
  deleteId: null,     // id waiting for delete confirmation
};

const $ = (id) => document.getElementById(id);   // shortcut for document.getElementById

const rupees = new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" });

function pad(number) {
  return String(number).padStart(2, "0");
}

function todayString() {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
}

function monthLabel(month) {            // "2026-10" -> "October 2026"
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("en-IN", { month: "long", year: "numeric" });
}

function formatDate(isoDate) {          // "2026-10-05" -> "05 Oct 2026"
  const [year, month, day] = isoDate.split("-").map(Number);
  return new Date(year, month - 1, day).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" });
}

let toastTimer;
function showToast(message, type = "success") {
  const toast = $("toast");
  toast.textContent = message;          // textContent is safe: it never runs HTML
  toast.className = `toast ${type}`;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 4000);
}

// ---------- 2. The one function that calls the Flask API ----------
// fetch() sends an HTTP request and returns a Promise. `await` waits for the answer.
async function api(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {                   // status 400, 404 ... -> throw so callers can use try/catch
    const error = new Error(data.error || "Something went wrong.");
    error.details = data.details || {};
    throw error;
  }
  return data;
}

// ---------- 3. Loading data and drawing the screen ----------
async function refreshAll() {
  try {
    await Promise.all([loadSummary(), loadExpenses(), loadBudget()]);
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function loadSummary() {
  const summary = await api(`/api/summary?month=${state.month}`);
  renderSummaryCards(summary);
  renderBudgetPage(summary);
}

function renderSummaryCards(summary) {
  const label = monthLabel(summary.month);
  $("card-total").textContent = rupees.format(summary.total_expenses);
  $("card-total-note").textContent = `${summary.expense_count} transaction(s) in ${label}`;

  $("card-budget").textContent = rupees.format(summary.budget);
  $("card-budget-note").textContent = summary.budget_is_set ? `Budget for ${label}` : "No budget set yet";

  $("card-remaining").textContent = rupees.format(summary.remaining);
  const box = $("card-remaining-box");
  box.className = "card";
  const notes = {
    no_budget: "Set a budget on the Monthly Budget page",
    ok: `${summary.percent_remaining}% of budget remaining`,
    warning: `Only ${summary.percent_remaining}% of budget left`,
    exhausted: "Budget fully used",
    over: `Over budget by ${rupees.format(Math.abs(summary.remaining))}`,
  };
  const styles = { ok: "good", warning: "warn", exhausted: "warn", over: "bad" };
  $("card-remaining-note").textContent = notes[summary.status];
  if (styles[summary.status]) box.classList.add(styles[summary.status]);
}

function currentFilters() {
  const [sort, order] = $("sort-select").value.split("-");
  const params = new URLSearchParams({ month: state.month, sort, order });
  if ($("filter-category").value) params.set("category", $("filter-category").value);
  if ($("search-input").value.trim()) params.set("search", $("search-input").value.trim());
  return params.toString();
}

async function loadExpenses() {
  const data = await api(`/api/expenses?${currentFilters()}`);
  renderTable(data.expenses);
}

function makeCell(text, label, className = "") {
  const cell = document.createElement("td");
  cell.dataset.label = label;           // used by the mobile CSS to show a small label
  cell.textContent = text;
  if (className) cell.className = className;
  return cell;
}

function makeActionButton(text, extraClass, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `link-btn ${extraClass}`;
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

function renderTable(expenses) {
  const body = $("expense-body");
  body.innerHTML = "";
  const filtersActive = $("search-input").value.trim() || $("filter-category").value;
  $("empty-state").hidden = expenses.length > 0;
  $("expense-table").hidden = expenses.length === 0;
  if (expenses.length === 0) {
    $("empty-state").textContent = filtersActive
      ? "No expenses match your search or filter."
      : "No expenses yet. Add your first expense to get started.";
  }

  for (const expense of expenses) {
    const row = document.createElement("tr");
    row.appendChild(makeCell(formatDate(expense.date), "Date"));

    const descriptionCell = makeCell(expense.description || "-", "Description");
    if (expense.is_demo) {
      const tag = document.createElement("span");
      tag.className = "demo-tag";
      tag.textContent = "demo";
      descriptionCell.appendChild(tag);
    }
    row.appendChild(descriptionCell);

    const categoryCell = makeCell("", "Category");
    const badge = document.createElement("span");
    badge.className = "badge";
    badge.textContent = expense.category;
    categoryCell.appendChild(badge);
    row.appendChild(categoryCell);

    row.appendChild(makeCell(expense.amount.toFixed(2), "Amount (₹)", "num"));

    const actionsCell = makeCell("", "Actions", "actions");
    actionsCell.appendChild(makeActionButton("Edit", "", () => startEdit(expense.id)));
    actionsCell.appendChild(makeActionButton("Delete", "danger", () => askDelete(expense)));
    row.appendChild(actionsCell);

    body.appendChild(row);
  }
}

// ---------- 4. Add / edit expense form ----------
function clearFormErrors() {
  document.querySelectorAll("#expense-form .field").forEach((f) => f.classList.remove("invalid"));
  document.querySelectorAll("#expense-form .field-error").forEach((e) => { e.textContent = ""; });
}

function showFieldErrors(details) {
  for (const [field, message] of Object.entries(details)) {
    const errorSpan = document.querySelector(`.field-error[data-for="${field}"]`);
    if (errorSpan) {
      errorSpan.textContent = message;
      errorSpan.closest(".field").classList.add("invalid");
    }
  }
}

function resetForm() {
  $("expense-form").reset();
  $("date").value = todayString();
  state.editingId = null;
  $("form-heading").textContent = "Add Expense";
  $("submit-btn").textContent = "Add Expense";
  $("cancel-edit-btn").hidden = true;
  clearFormErrors();
}

async function handleFormSubmit(event) {
  event.preventDefault();               // stop the browser from reloading the page
  clearFormErrors();
  const expenseData = {
    amount: $("amount").value,
    category: $("category").value,
    date: $("date").value,
    description: $("description").value,
  };
  const isEditing = state.editingId !== null;
  const url = isEditing ? `/api/expenses/${state.editingId}` : "/api/expenses";
  try {
    await api(url, { method: isEditing ? "PUT" : "POST", body: JSON.stringify(expenseData) });
    showToast(isEditing ? "Expense updated." : "Expense added.");
    resetForm();
    await refreshAll();
  } catch (error) {
    showFieldErrors(error.details);
    showToast(error.message, "error");
  }
}

async function startEdit(expenseId) {
  try {
    const expense = await api(`/api/expenses/${expenseId}`);   // GET one expense
    state.editingId = expense.id;
    $("amount").value = expense.amount;
    $("category").value = expense.category;
    $("date").value = expense.date;
    $("description").value = expense.description;
    $("form-heading").textContent = "Edit Expense";
    $("submit-btn").textContent = "Update Expense";
    $("cancel-edit-btn").hidden = false;
    clearFormErrors();
    $("amount").focus();
    $("expense-form").scrollIntoView({ behavior: "smooth", block: "center" });
  } catch (error) {
    showToast(error.message, "error");
  }
}

// ---------- 5. Delete with confirmation ----------
function askDelete(expense) {
  state.deleteId = expense.id;
  $("delete-text").textContent =
    `${expense.description || expense.category} - ${rupees.format(expense.amount)} on ${formatDate(expense.date)}`;
  $("delete-dialog").showModal();
}

async function confirmDelete() {
  $("delete-dialog").close();
  try {
    await api(`/api/expenses/${state.deleteId}`, { method: "DELETE" });
    if (state.editingId === state.deleteId) resetForm();
    showToast("Expense deleted.");
    await refreshAll();
  } catch (error) {
    showToast(error.message, "error");
  }
}

// ---------- 6. Monthly budget page ----------
async function loadBudget() {
  const budget = await api(`/api/budget?month=${state.month}`);
  $("budget-amount").value = budget.is_set ? budget.amount : "";
}

function renderBudgetPage(summary) {
  $("budget-spent").textContent = rupees.format(summary.total_expenses);
  $("budget-remaining").textContent = rupees.format(summary.remaining);

  const bar = $("progress-bar");
  const used = summary.percent_used === null ? 0 : summary.percent_used;
  bar.style.width = `${Math.min(used, 100)}%`;
  bar.className = "progress-bar";
  $("progress-text").textContent = summary.status === "no_budget"
    ? "No budget set for this month."
    : `${used}% of the budget used.`;

  const alertBox = $("budget-alert");
  alertBox.className = "alert";
  const alerts = {
    no_budget: ["info", "Set a budget above to start tracking your limit."],
    warning: ["warn", "Careful! You have used 80% or more of this month's budget."],
    exhausted: ["warn", "Your budget is fully used. Any new expense will go over budget."],
    over: ["bad", `You are over budget by ${rupees.format(Math.abs(summary.remaining))}.`],
  };
  if (alerts[summary.status]) {
    alertBox.classList.add(alerts[summary.status][0]);
    alertBox.textContent = alerts[summary.status][1];
    alertBox.hidden = false;
  } else {
    alertBox.hidden = true;
  }
  if (summary.status === "warning" || summary.status === "exhausted") bar.classList.add("warn");
  if (summary.status === "over") bar.classList.add("bad");
}

async function saveBudget() {
  document.querySelector('.field-error[data-for="budget-amount"]').textContent = "";
  try {
    await api("/api/budget", {
      method: "PUT",
      body: JSON.stringify({ month: state.month, amount: $("budget-amount").value }),
    });
    showToast(`Budget saved for ${monthLabel(state.month)}.`);
    await refreshAll();
  } catch (error) {
    const message = error.details["amount"] || error.message;
    document.querySelector('.field-error[data-for="budget-amount"]').textContent = message;
    showToast(message, "error");
  }
}

// ---------- 7. Demo data ----------
async function loadDemoData() {
  try {
    const result = await api(`/api/demo-data?month=${state.month}`, { method: "POST" });
    showToast(result.message);
    await refreshAll();
  } catch (error) {
    showToast(error.message, "error");
  }
}

async function clearDemoData() {
  try {
    const result = await api("/api/demo-data", { method: "DELETE" });
    showToast(result.message);
    await refreshAll();
  } catch (error) {
    showToast(error.message, "error");
  }
}

// ---------- 8. Navigation and month selection ----------
function showView() {
  const showBudget = window.location.hash === "#budget";
  $("view-dashboard").hidden = showBudget;
  $("view-budget").hidden = !showBudget;
  $("nav-dashboard").classList.toggle("active", !showBudget);
  $("nav-budget").classList.toggle("active", showBudget);
}

function changeMonth(newMonth) {
  if (!newMonth) return;                // the user cleared the field; keep the old month
  state.month = newMonth;
  $("month-select").value = newMonth;
  $("budget-month").value = newMonth;
  refreshAll();
}

// ---------- 9. Connect everything when the page loads ----------
function init() {
  const now = new Date();
  state.month = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`;
  $("month-select").value = state.month;
  $("budget-month").value = state.month;
  $("date").value = todayString();

  $("month-select").addEventListener("change", (e) => changeMonth(e.target.value));
  $("budget-month").addEventListener("change", (e) => changeMonth(e.target.value));
  $("expense-form").addEventListener("submit", handleFormSubmit);
  $("cancel-edit-btn").addEventListener("click", resetForm);
  $("save-budget-btn").addEventListener("click", saveBudget);
  $("load-demo-btn").addEventListener("click", loadDemoData);
  $("clear-demo-btn").addEventListener("click", clearDemoData);
  $("delete-confirm-btn").addEventListener("click", confirmDelete);
  $("delete-cancel-btn").addEventListener("click", () => $("delete-dialog").close());
  $("filter-category").addEventListener("change", () => loadExpenses().catch((e) => showToast(e.message, "error")));
  $("sort-select").addEventListener("change", () => loadExpenses().catch((e) => showToast(e.message, "error")));

  let searchTimer;                      // wait 300 ms after typing stops, then search
  $("search-input").addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => loadExpenses().catch((e) => showToast(e.message, "error")), 300);
  });

  window.addEventListener("hashchange", showView);
  showView();
  refreshAll();
}

init();
