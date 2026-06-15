import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { http, HttpResponse } from "msw";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";

import { App } from "../src/App";
import { AuthProvider } from "../src/auth/AuthContext";
import { server } from "./server";

// ADR-015: auth via cookie httpOnly + bootstrap GET /users/me. loginAs men-set cookie CSRF
// (agar header X-CSRF-Token ikut pada mutasi) dan meng-override /users/me agar mengembalikan
// role yang diminta — itulah sumber role saat AuthProvider bootstrap.
export function loginAs(role: "admin" | "user"): void {
  document.cookie = "aegis_csrf=test-csrf;path=/";
  server.use(
    http.get("http://localhost/v1/users/me", () =>
      HttpResponse.json({ id: "u1", username: role, role, timezone: "Asia/Jakarta" }),
    ),
  );
}

export function renderApp(initialEntries: string[] = ["/"]): ReturnType<typeof render> {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <MemoryRouter initialEntries={initialEntries}>
            <App />
          </MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    </MantineProvider>,
  );
}

export function renderNode(node: ReactElement, initialEntries: string[] = ["/"]): ReturnType<typeof render> {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <MantineProvider>
      <QueryClientProvider client={qc}>
        <AuthProvider>
          <MemoryRouter initialEntries={initialEntries}>{node}</MemoryRouter>
        </AuthProvider>
      </QueryClientProvider>
    </MantineProvider>,
  );
}
