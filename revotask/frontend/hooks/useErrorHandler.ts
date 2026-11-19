"use client";
import { useCallback } from "react";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthContext";
import { ApiError } from "@/lib/errors";

/** Single place that turns a thrown error into a toast (and handles 401). */
export function useErrorHandler() {
  const { logout } = useAuth();
  return useCallback(
    (err: unknown) => {
      if (err instanceof ApiError) {
        // logout() clears the session and redirects to /login.
        if (err.status === 401) logout();
        toast.error(err.message);
      } else {
        toast.error("Something went wrong");
      }
    },
    [logout],
  );
}
