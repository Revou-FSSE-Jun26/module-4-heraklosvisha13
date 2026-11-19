// Types mirror the backend JSON payloads (specs/design.md section 4.2).
// Keys are snake_case because apiClient returns `data` unchanged (D-02).

export type Role = "member" | "admin";

export interface ApiResponse<T> {
  data: T;
}

export interface ApiErrorBody {
  error: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  created_at: string;
}

/** Shape returned by login and register, and embedded elsewhere. */
export type UserPublic = Pick<User, "id" | "name" | "email">;

export interface Board {
  id: string;
  name: string;
  role: Role;
  created_at: string;
  updated_at: string;
}

export interface BoardMember {
  user_id: string;
  name: string;
  email: string;
  role: Role;
}

export interface Column {
  id: string;
  board_id: string;
  name: string;
  order: number;
  created_at: string;
  updated_at: string;
}

export interface Card {
  id: string;
  column_id: string;
  board_id: string;
  title: string;
  description: string | null;
  assignee_id: string | null;
  assignee: { id: string; name: string } | null;
  due_date: string | null;
  order: number;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface Comment {
  id: string;
  card_id: string;
  author_id: string;
  author_name: string;
  body: string;
  created_at: string;
  updated_at: string;
}

export interface Notification {
  id: string;
  type: "card_assigned" | "comment_added" | "board_member_added";
  message: string;
  board_id: string;
  card_id: string | null;
  read_at: string | null;
  created_at: string;
}

export interface BoardAnalytics {
  cards_per_column: { column_id: string; name: string; count: number }[];
  completed_this_week: { count: number; week_start: string };
  member_activity: {
    user_id: string;
    name: string;
    assigned_count: number;
    completed_this_week: number;
    comments_count: number;
  }[];
}
export interface BoardDetail extends Board {
  columns: (Column & { cards: Card[] })[];
}
export interface ActivityEntry {
  type: "card_created" | "card_completed" | "comment_added";
  actor_id: string | null;
  actor_name: string | null;
  created_at: string;
}
export interface CardDetail extends Card {
  comments: Comment[];
  activity: ActivityEntry[];
}
export interface TaskItem {
  id: string;
  title: string;
  board_id: string;
  board_name: string;
  column_name: string;
  due_date: string | null;
  completed_at: string | null;
}
export interface TaskList {
  items: TaskItem[];
  total: number;
  completed: number;
  open: number;
}
