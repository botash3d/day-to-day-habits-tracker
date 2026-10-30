import {
  useCallback,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  ApiError,
  getMe,
  login as loginRequest,
  signup as signupRequest,
  tokenStore,
  type User,
} from "../api/client";
import { AuthContext } from "./authContext";

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(() => tokenStore.get() !== null);

  // On page load, restore the session if a saved token is still valid.
  useEffect(() => {
    if (!tokenStore.get()) return;
    let cancelled = false;
    getMe()
      .then((u) => {
        if (!cancelled) setUser(u);
      })
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) tokenStore.clear();
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await loginRequest(email, password);
    tokenStore.set(access_token);
    try {
      setUser(await getMe());
    } catch (err) {
      tokenStore.clear();
      throw err;
    }
  }, []);

  const signup = useCallback(
    async (fullName: string, email: string, password: string) => {
      await signupRequest(fullName, email, password);
      await login(email, password); // log the new user in straight away
    },
    [login],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, signup, logout }),
    [user, loading, login, signup, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
