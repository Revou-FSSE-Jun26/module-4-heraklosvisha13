"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { BaseButton } from "@/components/shared/BaseButton";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { UserPublic } from "@/types";

export default function LoginPage() {
  const router = useRouter();
  const { status, login } = useAuth();
  const handleError = useErrorHandler();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (status === "authenticated") router.replace("/");
  }, [status, router]);

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      const res = await apiClient<{ access_token: string; user: UserPublic }>("/api/auth/login", null, {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      login(res.access_token, res.user);
    } catch (err) {
      handleError(err);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="flex flex-1 items-center justify-center bg-gray-50 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 rounded-lg bg-white p-6 shadow">
        <h1 className="text-2xl font-semibold text-gray-900">Log in</h1>
        <label className="block text-sm font-medium text-gray-700">
          Email
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
          />
        </label>
        <BaseButton type="submit" loading={submitting} className="w-full">
          Log in
        </BaseButton>
        <p className="text-center text-sm text-gray-600">
          No account?{" "}
          <Link href="/register" className="font-medium text-blue-600">
            Register
          </Link>
        </p>
      </form>
    </main>
  );
}
