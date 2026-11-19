import { expect, test, type Page, type Request } from "@playwright/test";
import { API_URL, registerAndLogin, uniqueUser } from "./helpers";

const TOKEN_KEY = "revotask.token";

/**
 * The UI has no "add column" control, so columns are created through the API
 * with the logged-in user's token. Everything else goes through the UI.
 */
async function createColumn(page: Page, boardId: string, name: string): Promise<void> {
  const token = await page.evaluate((key) => localStorage.getItem(key), TOKEN_KEY);
  expect(token).toBeTruthy();
  const res = await page.request.post(`${API_URL}/boards/${boardId}/columns`, {
    headers: { Authorization: `Bearer ${token}` },
    data: { name },
  });
  expect(res.status()).toBe(201);
}

test("kanban journey: board, columns, card, drag and drop, comment, search, notifications", async ({
  page,
}) => {
  const suffix = Date.now().toString(36);
  const boardName = `E2E Board ${suffix}`;
  const todo = "To Do";
  const done = "Done";
  const cardTitle = `E2E Card ${suffix}`;
  const commentText = `E2E comment ${suffix}`;

  // 1. Register and log in.
  await registerAndLogin(page, uniqueUser("kanban"));

  // 2. Create a board.
  await page.getByRole("button", { name: "Create Board" }).click();
  const boardDialog = page.getByRole("dialog", { name: "Create Board" });
  await boardDialog.getByLabel("Board name").fill(boardName);
  const boardCreated = page.waitForResponse(
    (r) => r.url().endsWith("/api/boards") && r.request().method() === "POST",
  );
  await boardDialog.getByRole("button", { name: "Create", exact: true }).click();
  const boardResponse = await boardCreated;
  expect(boardResponse.status()).toBe(201);
  const boardId: string = (await boardResponse.json()).data.id;
  await expect(boardDialog).toBeHidden();

  // 3. Create two columns (API), then open the board.
  await createColumn(page, boardId, todo);
  await createColumn(page, boardId, done);
  await page.getByRole("link", { name: new RegExp(boardName) }).click();
  await expect(page).toHaveURL(new RegExp(`/boards/${boardId}$`));
  await expect(page.getByRole("heading", { name: boardName })).toBeVisible();
  const todoColumn = page.getByRole("region", { name: todo, exact: true });
  const doneColumn = page.getByRole("region", { name: done, exact: true });
  await expect(todoColumn).toBeVisible();
  await expect(doneColumn).toBeVisible();

  // 4. Create a card in the first column.
  await todoColumn.getByRole("button", { name: "Add card" }).click();
  const cardDialog = page.getByRole("dialog", { name: "New card" });
  await cardDialog.getByLabel("Title").fill(cardTitle);
  const cardCreated = page.waitForResponse(
    (r) => /\/api\/columns\/[^/]+\/cards$/.test(r.url()) && r.request().method() === "POST",
  );
  await cardDialog.getByRole("button", { name: "Create", exact: true }).click();
  expect((await cardCreated).status()).toBe(201);
  await expect(cardDialog).toBeHidden();
  const cardInTodo = todoColumn.getByRole("button", { name: `Open card ${cardTitle}` });
  await expect(cardInTodo).toBeVisible();

  // 5. Drag the card to the second column.
  const moved = page.waitForResponse(
    (r) => /\/api\/cards\/[^/]+\/position$/.test(r.url()) && r.request().method() === "PATCH",
  );
  await cardInTodo.dragTo(doneColumn);
  expect((await moved).status()).toBe(200);
  await expect(doneColumn.getByRole("button", { name: `Open card ${cardTitle}` })).toBeVisible();
  await expect(todoColumn.getByRole("button", { name: `Open card ${cardTitle}` })).toHaveCount(0);

  // 6. Reload: the card must persist in the second column.
  const boardReloaded = page.waitForResponse(
    (r) => r.url().endsWith(`/api/boards/${boardId}`) && r.request().method() === "GET",
  );
  await page.reload();
  expect((await boardReloaded).status()).toBe(200);
  const doneAfterReload = page.getByRole("region", { name: done, exact: true });
  const todoAfterReload = page.getByRole("region", { name: todo, exact: true });
  await expect(doneAfterReload.getByRole("button", { name: `Open card ${cardTitle}` })).toBeVisible();
  await expect(todoAfterReload.getByRole("button", { name: `Open card ${cardTitle}` })).toHaveCount(0);

  // 7. Open the card detail modal and add a comment.
  await doneAfterReload.getByRole("button", { name: `Open card ${cardTitle}` }).click();
  const detail = page.getByRole("dialog", { name: "Card details" });
  await expect(detail.getByLabel("Title")).toHaveValue(cardTitle);
  await detail.getByLabel("New comment").fill(commentText);
  const commented = page.waitForResponse(
    (r) => /\/api\/cards\/[^/]+\/comments$/.test(r.url()) && r.request().method() === "POST",
  );
  await detail.getByRole("button", { name: "Post comment" }).click();
  expect((await commented).status()).toBe(201);
  await expect(detail.getByText(commentText)).toBeVisible();
  await expect(detail.getByRole("heading", { name: "Comments (1)" })).toBeVisible();
  await detail.getByRole("button", { name: "Close" }).click();
  await expect(detail).toBeHidden();

  // 8. Search is debounced by 300 ms: typing a burst sends one request, with the final query.
  const searchRequests: string[] = [];
  const onRequest = (req: Request) => {
    if (/\/api\/boards\/[^/]+\/cards\?q=/.test(req.url())) searchRequests.push(req.url());
  };
  page.on("request", onRequest);
  const search = page.getByLabel("Search cards");
  const isSearch = (q: string) => (r: { url(): string; request(): Request }) =>
    r.url().includes(`/cards?q=${encodeURIComponent(q)}`) && r.request().method() === "GET";

  const noMatchQuery = `zzz-no-match-${suffix}`;
  const noMatch = page.waitForResponse(isSearch(noMatchQuery));
  await search.pressSequentially(noMatchQuery);
  expect((await noMatch).status()).toBe(200);
  await expect(page.getByText("No cards match your search.")).toBeVisible();
  expect(searchRequests).toHaveLength(1);
  expect(searchRequests[0]).toContain(`q=${encodeURIComponent(noMatchQuery)}`);

  const match = page.waitForResponse(isSearch(cardTitle));
  await search.fill(cardTitle);
  expect((await match).status()).toBe(200);
  await expect(page.getByText("No cards match your search.")).toBeHidden();
  await expect(doneAfterReload.getByRole("button", { name: `Open card ${cardTitle}` })).not.toHaveClass(
    /opacity-30/,
  );
  page.off("request", onRequest);

  // 9. The notification bell is displayed with an unread count and a menu.
  const bell = page.getByRole("button", { name: /^Notifications, \d+ unread$/ });
  await expect(bell).toBeVisible();
  await bell.click();
  await expect(bell).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("menu")).toBeVisible();
});
