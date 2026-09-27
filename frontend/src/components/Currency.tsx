import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { settingsApi } from "../api";
import { money as formatMoney } from "../lib/format";
import { useAuth } from "./Auth";

type FormatMoney = (value: string | number | null | undefined) => string;

const MoneyContext = createContext<FormatMoney>((value) => formatMoney(value, "USD"));
const CodeContext = createContext({ code: "USD", setCode: (_code: string) => undefined as void });

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  const [code, setCode] = useState("USD");

  useEffect(() => {
    if (!user) return;
    settingsApi
      .get()
      .then((row) => setCode(row.ledger_currency || "USD"))
      .catch(() => undefined);
  }, [user]);

  const format = useCallback<FormatMoney>((value) => formatMoney(value, code), [code]);

  return (
    <CodeContext.Provider value={{ code, setCode }}>
      <MoneyContext.Provider value={format}>{children}</MoneyContext.Provider>
    </CodeContext.Provider>
  );
}

export function useMoney() {
  return useContext(MoneyContext);
}

export function useLedgerCurrency() {
  return useContext(CodeContext);
}
