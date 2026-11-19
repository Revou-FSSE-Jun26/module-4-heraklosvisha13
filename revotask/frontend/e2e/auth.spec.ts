import { expect, test } from "@playwright/test";
import { login, register, registerAndLogin, uniqueUser } from "./helpers";

test.describe("authentication", () => {
  test("registers a new user and shows the success toast", async ({ page }) => {
    const user = uniqueUser("register");
    await register(page, user);
    await expect(page.getByText("Account created. Please log in.")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
  });

  test("logs in with valid credentials", async ({ page }) => {
    const user = uniqueUser("login");
    await registerAndLogin(page, user);
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByText(user.name)).toBeVisible();
    await expect(page.getByRole("button", { name: "Logout" })).toBeVisible();
  });

  test("shows an error toast for invalid credentials", async ({ page }) => {
    const user = uniqueUser("invalid");
    await register(page, user);

    const failed = page.waitForResponse(
      (r) => r.url().endsWith("/api/auth/login") && r.request().method() === "POST",
    );
    await login(page, user.email, "WrongPassword!999");
    expect((await failed).status()).toBe(401);

    await expect(page.getByText("Invalid email or password")).toBeVisible();
    await expect(page).toHaveURL(/\/login$/);
  });

  test("redirects to /login when logged out", async ({ page }) => {
    for (const path of ["/", "/my-tasks", "/profile"]) {
      await page.goto(path);
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();
    }
  });

  test("logs out and loses access to protected routes", async ({ page }) => {
    await registerAndLogin(page, uniqueUser("logout"));

    await page.getByRole("button", { name: "Logout" }).click();
    await expect(page).toHaveURL(/\/login$/);
    await expect(page.getByRole("heading", { name: "Log in" })).toBeVisible();

    await page.goto("/");
    await expect(page).toHaveURL(/\/login$/);
  });
});
