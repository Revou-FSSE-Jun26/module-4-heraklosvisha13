# Frontend Guidelines (Next.js App Router + TypeScript + Tailwind)

Scope: components, API access from the browser and server, hooks, and E2E tests. The API contract (envelope and status codes) is defined in `backend.md`. Data models are defined in `database.md`.

---

## 1. Mandatory Shared Components

**Rule**
Shared components live in `components/shared/`.
- Every interactive button uses `<BaseButton>` with `variant` of `primary`, `secondary`, or `destructive`.
- Every status tag uses `<BaseBadge>`.
- Every form modal uses `<BaseModal>`.

Never use a raw `<button>` tag in pages or feature components. Raw `<button>` is allowed only inside `components/shared/BaseButton.tsx`.

**Rationale**
Shared components give consistent styling, accessibility, and behavior, and a change is made in one place.

**Example**
```tsx
// app/boards/[boardId]/page.tsx
import { BaseButton } from "@/components/shared/BaseButton";
import { BaseBadge } from "@/components/shared/BaseBadge";
import { BaseModal } from "@/components/shared/BaseModal";

<BaseButton variant="primary" onClick={() => setOpen(true)}>Add card</BaseButton>
<BaseBadge>{card.completedAt ? "Done" : "Open"}</BaseBadge>
<BaseModal isOpen={open} title="New card" onClose={() => setOpen(false)}>
  <CardForm onSubmit={createCard} />
</BaseModal>
<BaseButton variant="destructive" onClick={() => deleteCard(card.id)}>Delete</BaseButton>
```

---

## 2. Typed API Client & Environment Separation

**Rule**
All API requests go through `lib/apiClient.ts`. Never call `fetch` directly elsewhere.
- Server Components read `API_BASE_URL`. Client Components read `NEXT_PUBLIC_API_BASE_URL`.
- The client attaches `Authorization: Bearer <token>`. The token is held in `AuthContext` and passed to the client.
- On a non-2xx response it throws a typed `ApiError` built from the response's `{"error": "<message>"}`.
- On success it returns the `data` field of the envelope, typed by a generic.

**Rationale**
One client centralizes base URLs, auth headers, and error parsing. Separate variables keep server-only URLs out of the browser bundle.

**Example**
```ts
// lib/apiClient.ts
export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

const baseUrl = () =>
  typeof window === "undefined"
    ? process.env.API_BASE_URL!
    : process.env.NEXT_PUBLIC_API_BASE_URL!;

export async function apiClient<T>(path: string, token?: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${baseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, body.error ?? "Request failed");
  return body.data as T;
}
```

---

## 3. Drag and Drop With Optimistic UI

**Rule**
`hooks/useDragAndDrop.ts` implements card movement with the native HTML5 Drag and Drop API (`draggable`, `onDragStart`, `onDragOver`, `onDrop`). No drag-and-drop library. On drop it updates local state immediately, calls the API through `apiClient`, and restores the previous state if the call throws an `ApiError`.

**Rationale**
Immediate visual feedback is a brief requirement. Rollback keeps the UI consistent with the server when a move fails.

**Example**
```ts
// hooks/useDragAndDrop.ts
export function useDragAndDrop(cards: Card[], setCards: (c: Card[]) => void) {
  const handleError = useErrorHandler();
  const { token } = useAuth();

  const onDrop = async (cardId: string, columnId: string, order: number) => {
    const snapshot = cards;
    setCards(cards.map(c => (c.id === cardId ? { ...c, columnId, order } : c)));
    try {
      await apiClient(`/api/cards/${cardId}/move`, token, {
        method: "PATCH",
        body: JSON.stringify({ column_id: columnId, order }),
      });
    } catch (err) {
      setCards(snapshot);
      handleError(err);
    }
  };
  return { onDrop };
}
```

---

## 4. Notification Polling

**Rule**
`hooks/useNotifications.ts` polls `GET /api/notifications` every 30 seconds with `setInterval` and clears the interval on unmount. The bell icon reads from this hook only.

**Rationale**
The brief requires automatic refresh every 30 seconds. A single hook avoids duplicate timers.

**Example**
```ts
// hooks/useNotifications.ts
const POLL_MS = 30_000;

export function useNotifications() {
  const { token } = useAuth();
  const [items, setItems] = useState<Notification[]>([]);

  useEffect(() => {
    const load = () => apiClient<Notification[]>("/api/notifications", token).then(setItems).catch(() => {});
    load();
    const id = setInterval(load, POLL_MS);
    return () => clearInterval(id);
  }, [token]);

  return { items, unread: items.filter(n => !n.readAt).length };
}
```

---

## 5. Central Error Handling

**Rule**
`hooks/useErrorHandler.ts` maps a thrown `ApiError` to a `react-hot-toast` message. Components and other hooks call it and never call `toast.error` with raw error objects. A `401` also clears the session and redirects to `/login`.

**Rationale**
Users see consistent messages, and expired sessions are handled in one place.

**Example**
```ts
// hooks/useErrorHandler.ts
export function useErrorHandler() {
  const { logout } = useAuth();
  return useCallback((err: unknown) => {
    if (err instanceof ApiError) {
      if (err.status === 401) logout();
      toast.error(err.message);
    } else {
      toast.error("Something went wrong");
    }
  }, [logout]);
}
```

---

## 6. Debounced Card Search

**Rule**
Card search sends its request 300 ms after the last keystroke, using a `useDebouncedValue(value, 300)` hook.

**Rationale**
The brief requires a 300 ms debounce to avoid a request per keystroke.

**Example**
```ts
const [query, setQuery] = useState("");
const debounced = useDebouncedValue(query, 300);
useEffect(() => {
  apiClient<Card[]>(`/api/boards/${boardId}/cards?q=${encodeURIComponent(debounced)}`, token).then(setCards);
}, [debounced]);
```

---

## 7. Playwright E2E Testing Standards

**Rule**
Never use `page.waitForTimeout()` anywhere in E2E tests. Always wait explicitly for a DOM locator (`expect(locator).toBeVisible()`) or a network response (`page.waitForResponse`).

**Rationale**
Fixed sleeps make tests slow and flaky. Explicit waits continue as soon as the condition is met.

**Example**
```ts
// e2e/drag-card.spec.ts
const moved = page.waitForResponse(
  r => r.url().includes("/api/cards/") && r.url().endsWith("/move") && r.ok()
);
await card.dragTo(doneColumn);
await moved;
await expect(doneColumn.getByText("Write tests")).toBeVisible();
```
