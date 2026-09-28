export type RiskLevel = "LOW" | "MEDIUM" | "HIGH";

export interface Account {
  id: string;
  user_id: string;
  name: string;
  account_number: string;
  ifsc_code: string;
  account_type: string;
  balance: string;
  currency: string;
  status: string;
  created_at: string;
  transaction_count: number;
}

export interface TriggeredRule {
  code: string;
  points: number;
  explanation: string;
}

export interface LedgerEntry {
  id: string;
  transaction_id: string;
  account_id: string;
  account_name: string;
  entry_type: "DEBIT" | "CREDIT";
  amount: string;
  currency: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  account_name: string;
  destination_account_id: string | null;
  destination_account_name: string | null;
  transaction_type: "CREDIT" | "DEBIT" | "TRANSFER";
  amount: string;
  currency: string;
  merchant: string;
  category: string;
  description: string;
  timestamp: string;
  location: string | null;
  status: string;
  risk_score: number;
  rule_score: number;
  ml_score: number;
  rule_summary: string;
  risk_level: RiskLevel;
  risk_explanation: string;
  triggered_rules: TriggeredRule[];
  created_at: string;
  alert_id: string | null;
  ledger_entries?: LedgerEntry[];
}

export interface AlertReviewEvent {
  id: string;
  user_id: string;
  reviewer_name: string;
  from_status: string;
  to_status: string;
  note: string;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface FraudAlert {
  id: string;
  transaction_id: string;
  account_id: string;
  account_name: string;
  alert_type: string;
  risk_score: number;
  risk_level: RiskLevel;
  explanation: string;
  triggered_rules: TriggeredRule[];
  status: string;
  resolution_note: string;
  created_at: string;
  updated_at: string;
  amount: string | null;
  currency: string | null;
  merchant: string | null;
  rule_score: number | null;
  ml_score: number | null;
  rule_summary: string;
  reviews: AlertReviewEvent[];
}

export interface AuditEvent {
  id: string;
  action: string;
  entity_type: string;
  entity_id: string;
  message: string;
  details: Record<string, unknown>;
  created_at: string;
}

export interface DashboardSummary {
  total_balance: string;
  active_accounts: number;
  transaction_volume: string;
  transaction_count: number;
  open_alerts: number;
  high_risk_alerts: number;
  recent_transactions: Transaction[];
  attention_queue: FraudAlert[];
  volume_series: { date: string; amount: string }[];
  risk_distribution: Record<string, number>;
}

export interface RiskSettings {
  duplicate_window_minutes: number;
  duplicate_score: number;
  frequency_threshold: number;
  frequency_window_minutes: number;
  frequency_score: number;
  large_multiplier_medium: number;
  large_multiplier_high: number;
  large_score_medium: number;
  large_score_high: number;
  unusual_time_score: number;
  unusual_start_hour: number;
  unusual_end_hour: number;
  anomaly_score: number;
  min_history_count: number;
  alert_threshold: number;
  ledger_currency: string;
}

export interface ImportSummary {
  imported: number;
  rejected: number;
  errors: { row: number; message: string }[];
  transaction_ids: string[];
}

export interface ReceiptDraft {
  filename: string;
  source: string;
  merchant: string;
  amount: string;
  detected_currency: string;
  ledger_currency: string;
  timestamp: string;
  transaction_type: "DEBIT" | "CREDIT";
  category: string;
  description: string;
  warnings: string[];
  raw_text: string;
}

export interface LedgerPage {
  items: LedgerEntry[];
  total: number;
  page: number;
  page_size: number;
  debit_total: string;
  credit_total: string;
}
