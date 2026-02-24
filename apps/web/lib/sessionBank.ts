export const BANK_SESSION_KEY = "playground_bank_id";
export const BANK_SCOPE_KEY = "playground_bank_scope"; // "session" | "demo" | "all"

export type BankScopeMode = "session" | "demo" | "all";

export function createSessionBankId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `bank-${crypto.randomUUID()}`;
  }
  const random = Math.random().toString(36).slice(2, 10);
  return `bank-${Date.now()}-${random}`;
}

export function getOrCreateSessionBankId(): string {
  const existing = window.sessionStorage.getItem(BANK_SESSION_KEY);
  const bankId = existing || createSessionBankId();
  window.sessionStorage.setItem(BANK_SESSION_KEY, bankId);
  return bankId;
}

export function getStoredBankScope(): BankScopeMode {
  const raw = (window.sessionStorage.getItem(BANK_SCOPE_KEY) || "").trim();
  if (raw === "demo" || raw === "all" || raw === "session") return raw;
  return "session";
}

export function setStoredBankScope(mode: BankScopeMode): void {
  window.sessionStorage.setItem(BANK_SCOPE_KEY, mode);
}

