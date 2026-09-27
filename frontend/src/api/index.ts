import { api } from "./client";
import type {
  Account,
  AuditEvent,
  DashboardSummary,
  FraudAlert,
  ImportSummary,
  LedgerPage,
  Page,
  ReceiptDraft,
  RiskSettings,
  Transaction,
} from "../types";

interface ModelMetrics {
  precision: number;
  recall: number;
  f1: number;
  pr_auc: number;
  false_positive_rate: number;
}

export const dashboardApi = {
  summary: async () => (await api.get<DashboardSummary>("/api/dashboard/summary")).data,
};

export const accountsApi = {
  list: async () => (await api.get<Account[]>("/api/accounts")).data,
  get: async (id: string) => (await api.get<Account>(`/api/accounts/${id}`)).data,
  create: async (payload: { name: string; account_type: string; currency: string; opening_balance: string }) =>
    (await api.post<Account>("/api/accounts", payload)).data,
  transactions: async (id: string) => (await api.get<Transaction[]>(`/api/accounts/${id}/transactions`)).data,
};

export const transactionsApi = {
  list: async (params: Record<string, string | number>) =>
    (await api.get<Page<Transaction>>("/api/transactions", { params })).data,
  create: async (payload: Record<string, unknown>, idempotencyKey?: string) =>
    (
      await api.post<Transaction>("/api/transactions", payload, {
        headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      })
    ).data,
  get: async (id: string) => (await api.get<Transaction>(`/api/transactions/${id}`)).data,
  importCsv: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return (await api.post<ImportSummary>("/api/transactions/import", body)).data;
  },
  readReceipt: async (file: File) => {
    const body = new FormData();
    body.append("file", file);
    return (await api.post<ReceiptDraft>("/api/transactions/receipts", body)).data;
  },
  confirmReceipt: async (payload: Record<string, unknown>, idempotencyKey?: string) =>
    (
      await api.post<Transaction>("/api/transactions/receipts/confirm", payload, {
        headers: idempotencyKey ? { "Idempotency-Key": idempotencyKey } : undefined,
      })
    ).data,
};

export const fraudApi = {
  list: async (params: Record<string, string | number>) =>
    (await api.get<Page<FraudAlert>>("/api/fraud-alerts", { params })).data,
  review: async (id: string, payload: { status: string; resolution_note: string }) =>
    (await api.post<FraudAlert>(`/api/fraud-alerts/${id}/review`, payload)).data,
};

export const analyticsApi = {
  transactions: async () =>
    (
      await api.get<{
        volume_over_time: { date: string; amount: string }[];
        credit_vs_debit: { type: string; amount: string }[];
        category_breakdown: { category: string; amount: string }[];
      }>("/api/analytics/transactions")
    ).data,
  risk: async () =>
    (
      await api.get<{
        risk_distribution: { level: string; count: number }[];
        alerts_over_time: { date: string; count: number }[];
        fraud_by_category: { category: string; amount: string }[];
        score_histogram: { bucket: string; count: number }[];
        rule_frequency: { rule: string; count: number }[];
        model_comparison: {
          note: string;
          rules: ModelMetrics;
          model: ModelMetrics;
          hybrid: ModelMetrics;
        };
      }>("/api/analytics/risk")
    ).data,
};

export const auditApi = {
  list: async (page: number) => (await api.get<Page<AuditEvent>>("/api/audit-logs", { params: { page, page_size: 30 } })).data,
};

export const settingsApi = {
  get: async () => (await api.get<RiskSettings>("/api/settings")).data,
  update: async (payload: RiskSettings) => (await api.patch<RiskSettings>("/api/settings", payload)).data,
};

export const ledgerApi = {
  list: async (params: Record<string, string | number | boolean>) =>
    (await api.get<LedgerPage>("/api/ledger", { params })).data,
};

export interface SessionUser {
  id: string;
  email: string;
  full_name: string;
}

export const authApi = {
  login: async (payload: { email: string; password: string }) =>
    (await api.post<{ token: string; user: SessionUser }>("/api/auth/login", payload)).data,
  register: async (payload: { full_name: string; email: string; password: string }) =>
    (await api.post<{ token: string; user: SessionUser }>("/api/auth/register", payload)).data,
  me: async () => (await api.get<SessionUser>("/api/auth/me")).data,
};
