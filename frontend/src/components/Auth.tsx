import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { authApi, type SessionUser } from "../api";

const TOKEN_KEY = "finsight_token";

type AuthValue = {
  user: SessionUser | null;
  ready: boolean;
  signIn: (token: string, user: SessionUser) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (!token) {
      setReady(true);
      return;
    }
    authApi
      .me()
      .then(setUser)
      .catch(() => sessionStorage.removeItem(TOKEN_KEY))
      .finally(() => setReady(true));
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      user,
      ready,
      signIn(token, next) {
        sessionStorage.setItem(TOKEN_KEY, token);
        setUser(next);
      },
      signOut() {
        sessionStorage.removeItem(TOKEN_KEY);
        setUser(null);
      },
    }),
    [ready, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider is missing");
  return value;
}
