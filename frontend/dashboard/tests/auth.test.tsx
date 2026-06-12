import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { server } from "./server";
import { loginAs, renderApp } from "./utils";

describe("AC-DASH-01 auth & role", () => {
  it("login → simpan token & masuk dashboard", async () => {
    server.use(
      http.post("http://localhost/v1/auth/login", () =>
        HttpResponse.json({ jwt: "jwt-abc", role: "admin" }),
      ),
    );
    renderApp(["/login"]);
    await userEvent.type(screen.getByLabelText("Username"), "admin");
    await userEvent.type(screen.getByLabelText("Password"), "secret");
    await userEvent.click(screen.getByRole("button", { name: "Masuk" }));

    await waitFor(() => expect(screen.getByRole("heading", { name: "Analitik" })).toBeInTheDocument());
    expect(localStorage.getItem("aegis_jwt")).toBe("jwt-abc");
  });

  it("login gagal → tampilkan error, tetap di login", async () => {
    server.use(
      http.post("http://localhost/v1/auth/login", () =>
        HttpResponse.json({ code: "invalid_credentials", message: "salah" }, { status: 401 }),
      ),
    );
    renderApp(["/login"]);
    await userEvent.type(screen.getByLabelText("Username"), "x");
    await userEvent.type(screen.getByLabelText("Password"), "y");
    await userEvent.click(screen.getByRole("button", { name: "Masuk" }));
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("menu admin vs user (role-gated)", async () => {
    loginAs("admin");
    const { unmount } = renderApp(["/"]);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Analitik" })).toBeInTheDocument());
    expect(screen.getByText("Users")).toBeInTheDocument();
    expect(screen.getByText("Campaign")).toBeInTheDocument();
    unmount();

    loginAs("user");
    renderApp(["/"]);
    await waitFor(() => expect(screen.getByRole("heading", { name: "Analitik" })).toBeInTheDocument());
    expect(screen.queryByText("Users")).not.toBeInTheDocument();
    expect(screen.getByText("Pencarian")).toBeInTheDocument();
  });

  it("tanpa login → diarahkan ke /login", async () => {
    renderApp(["/"]);
    await waitFor(() => expect(screen.getByText("Masuk Aegis")).toBeInTheDocument());
  });
});
