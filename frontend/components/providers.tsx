"use client";
import { createContext, useCallback, useContext, useState } from "react";
import {
  QueryClient,
  QueryClientProvider,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { api, bootstrap } from "@/lib/api";

const Ready = createContext(false);
const Toast = createContext<(message: string) => void>(() => {});
function SessionGate({ children }: { children: React.ReactNode }) {
  const session = useQuery({
    queryKey: ["session"],
    queryFn: bootstrap,
    retry: false,
    staleTime: Infinity,
    gcTime: Infinity,
  });
  if (session.isError)
    return (
      <main className="center-state">
        <h1>Let’s reconnect</h1>
        <p>{session.error.message}</p>
        <button onClick={() => session.refetch()}>Try again</button>
      </main>
    );
  return <Ready.Provider value={session.isSuccess}>{children}</Ready.Provider>;
}
export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30000,
            retry: false,
            refetchOnWindowFocus: false,
          },
          mutations: { retry: false },
        },
      }),
  );
  const [toast, setToast] = useState("");
  const notify = useCallback((message: string) => {
    setToast(message);
    setTimeout(() => setToast(""), 5000);
  }, []);
  return (
    <QueryClientProvider client={client}>
      <Toast.Provider value={notify}>
        <SessionGate>{children}</SessionGate>
        <div
          className={toast ? "toast" : "sr-only"}
          role="status"
          aria-live="polite"
        >
          {toast}
        </div>
      </Toast.Provider>
    </QueryClientProvider>
  );
}
export function useApi<T>(path: string) {
  const ready = useContext(Ready);
  return useQuery({
    queryKey: ["api", path],
    queryFn: ({ signal }) => api<T>(path, { signal }),
    enabled: ready,
  });
}
export function useAction() {
  const client = useQueryClient();
  const notify = useContext(Toast);
  return useMutation({
    mutationFn: async (input: {
      path: string;
      method: string;
      body?: unknown;
      version?: number;
      key?: string;
      message?: string;
    }) => {
      const result = await api<unknown>(input.path, input);
      return { result, message: input.message };
    },
    onSuccess: async ({ message }) => {
      await client.invalidateQueries({ queryKey: ["api"] });
      if (message) notify(message);
    },
  });
}
