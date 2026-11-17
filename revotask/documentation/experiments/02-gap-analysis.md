# 02. Requirements Gap Analysis & Architectural Decisions

## 1. Purpose & Learning Objective
Building on the baseline experiment (`01-initial-test.md`), this exercise performs a structured **Requirements Gap Analysis** on `specs/project-brief.md`. The goal is to systematically uncover missing technical rules, ambiguous permissions, and open architectural choices before authoring the steering guidelines and specifications.

---

## 2. Input
- **Workspace State:** Read-only analysis mode based on `specs/project-brief.md` and the 12 assumptions observed in `01-initial-test.md`.
- **Prompt Executed:**
```text
Based on the previous implementation exercise, perform a requirements gap analysis of the existing RevoTask project brief.
Your previous response introduced several assumptions because certain technical and business requirements were not explicitly defined.

Please review those assumptions and identify:
1. Missing database entities, relationships, constraints, and business rules.
2. Missing authentication and authorization requirements.
3. Missing API design conventions, including response formats, error handling, and pagination.
4. Missing backend and frontend architectural conventions.
5. Missing validation, testing, and security requirements.
6. Any conflicting, ambiguous, or incomplete requirements.
7. For each finding:
- Explain why the requirement matters.
- Identify whether it is essential for the MVP or can be postponed.
- Recommend a solution based on common professional software engineering practices.
- Output the findings in a structured table.

Important constraints:
- Do not modify any existing files.
- Do not generate application code.
- Do not invent requirements without identifying them as recommendations or assumptions.
- Prioritize requirements that could lead to inconsistent architecture or incorrect implementation.
- Wait for my approval before making any changes.
```

---

## 3. Execution Process & Resulting Output

### Step 1: Domain Categorization & Gap Identification
Kiro audited the brief across 6 engineering domains, evaluated whether each gap was essential for the **MVP** or could be deferred (**Later**), and produced structured tables of recommendations without modifying any files:

> **Kiro Output (Core MVP Gaps Identified):**
>
> #### A. Database Entities, Relationships & Business Rules
> | # | Gap | Why It Matters | Priority | Kiro Recommendation |
> | :--- | :--- | :--- | :--- | :--- |
> | 1.1 | No explicit table schema defined. | Developers/AI could design incompatible tables. | **MVP** | Define ERD in `database.md` (`users`, `boards`, `board_members`, `columns`, `cards`, `comments`, `notifications`). |
> | 1.2 | Board membership table is unmodeled. | Authorization depends on tracking board access. | **MVP** | Create `board_members` join table with unique `(board_id, user_id)` constraint. |
> | 1.3 | Role scope (`Member` vs `Admin`) is unclear. | Determines where `role` is stored. | **MVP** | Store `role` per board inside `board_members`. |
> | 1.4 | Board creator privileges unspecified. | A board could end up with zero admins. | **MVP** | Creator becomes `admin` automatically; block removing the last admin. |
> | 1.5 | Delete behavior (`CASCADE` vs soft delete) undefined. | Risks orphaned records or permanent data loss. | **MVP** | Use soft delete (`deleted_at`) across tables and `SET NULL` on `assignee_id` upon user deletion. |
> | 1.6 | `FLOAT` ordering precision & rebalance rules vague. | Narrow float gaps can break card ordering. | **MVP** | Use initial spacing (`1000.0`), midpoint insertion, and transactional column rebalancing. |
> | 1.7 | Card assignee rules missing. | Affects schema and `/my-tasks` view. | **MVP** | Single nullable `assignee_id` restricted to board members. |
> | 1.8 | Cross-board card moves undefined. | Could bypass board membership checks. | **MVP** | Restrict card movement strictly within the same board. |
> | 1.9 | "Completed" card criteria for analytics undefined. | "Completed this week" metric cannot be queried. | **MVP** | Track via `completed_at` timestamp or designated completion column. |
>
> #### B. Auth, API Conventions & Architecture
> | # | Gap | Why It Matters | Priority | Kiro Recommendation |
> | :--- | :--- | :--- | :--- | :--- |
> | 2.1–2.2 | JWT lifetime & frontend storage unspecified. | Impacts XSS/CSRF security and Next.js Server/Client fetches. | **MVP** | Define explicit token handling in `frontend.md`. |
> | 2.6–2.9 | Permission matrix & `403` vs `404` rules incomplete. | Leads to inconsistent endpoint authorization. | **MVP** | Enforce owner-only comment edit/delete (`403 Forbidden`). |
> | 3.1–3.2 | JSON response envelope & error format unstandardized. | Frontend/backend parsing will diverge. | **MVP** | Lock a single envelope standard in `backend.md`. |
> | 3.4 | Card search query contract missing. | Frontend 300ms debounce needs a defined query contract. | **MVP** | Case-insensitive filtering across card `title` and `description`. |
> | 3.10 | CORS policy between Vercel & Railway undefined. | Production requests will be blocked by browsers. | **MVP** | Configure `Flask-CORS` restricted to the frontend origin. |
> | 4.1–4.5 | Backend layering & frontend client conventions missing. | Logic risks leaking into route handlers or UI pages. | **MVP** | Enforce `routes.py` $\rightarrow$ `service.py` $\rightarrow$ `schema.py` and `lib/apiClient.ts`. |

### Step 2: Developer's Architectural Decisions (Resolving Kiro's Open Questions)
At the end of its analysis, Kiro paused and asked for approval on five open architectural decisions (`2.2`, `2.9`, `3.5`, `3.10`, and `4.5`). The following decisions were finalized to be written into `.kiro/steering/`:

1. **Database Standards (`database.md`):** Enforce **UUID** primary keys, audit/soft-delete columns (`created_at`, `updated_at`, `deleted_at`), and **`order = db.Column(db.Float, nullable=False)`** on `Column` and `Card`.
2. **Frontend Token Strategy (Decision 2.2):** Store JWT in `AuthContext` and sync it so `lib/apiClient.ts` attaches `Authorization: Bearer <token>` in both Server Components (`API_BASE_URL`) and Client Components (`NEXT_PUBLIC_API_BASE_URL`).
3. **HTTP Status Policy (Decision 2.9):** Return `401` for missing/invalid tokens, `403` for authenticated users lacking board access or comment ownership, and `404` for missing resources.
4. **API Envelope & Routing (Decisions 3.1 & 3.5):** Use `/api/<resource>` endpoints (including `GET /api/health`) and enforce flat JSON envelopes: `{"data": ...}` for success and `{"error": "<message>"}` for failure.
5. **CORS & Frontend Architecture (Decisions 3.10, 4.5, 4.6):** Configure `Flask-CORS` via `FRONTEND_URL`, build shared UI components (`BaseButton`, `BaseBadge`, `BaseModal`), and implement drag-and-drop using the **Native HTML5 Drag and Drop API** inside `hooks/useDragAndDrop.ts`.