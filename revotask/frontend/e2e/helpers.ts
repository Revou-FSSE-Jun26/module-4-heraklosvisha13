import { expect, type Page } from "@playwright/test";

export const API_URL = process.env.E2E_API_URL ?? "http://localhost:5001/api";
export const PASSWORD = "Passw0rd!123";

export type TestUser = { name: string; email: string; password: string };

/** A unique user per call so tests never collide on the unique-email constraint. */
export function uniqueUser(prefix = "e2e"): TestUser {
  const id = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
  return { name: `${prefix} user ${id}`, email: `${prefix}-${id}@example.com`, password: PASSWORD };
}

export async function register(page: Page, user: TestUser): Promise<void> {
  await page.goto("/register");
  const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Register" }) });
  await form.getByLabel("Name", { exact: true }).fill(user.name);
  await form.getByLabel("Email", { exact: true }).fill(user.email);
  await form.getByLabel("Password", { exact: false }).fill(user.password);
  const registered = page.waitForResponse(
    (r) => r.url().endsWith("/api/auth/register") && r.request().method() === "POST",
  );
  await page.getByRole("button", { name: "Register" }).click();
  expect((await registered).status()).toBe(201);
  await expect(page).toHaveURL(/\/login$/);
}

export async function login(page: Page, email: string, password: string): Promise<void> {
  const form = page.locator("form").filter({ has: page.getByRole("button", { name: "Log in" }) });
  await form.getByLabel("Email", { exact: true }).fill(email);
  await form.getByLabel("Password", { exact: true }).fill(password);
  await form.getByRole("button", { name: "Log in" }).click();
}

export async function registerAndLogin(page: Page, user: TestUser): Promise<void> {
  await register(page, user);
  const loggedIn = page.waitForResponse(
    (r) => r.url().endsWith("/api/auth/login") && r.request().method() === "POST",
  );
  await login(page, user.email, user.password);
  expect((await loggedIn).status()).toBe(200);
  await expect(page.getByRole("heading", { name: "Your boards" })).toBeVisible();
}
