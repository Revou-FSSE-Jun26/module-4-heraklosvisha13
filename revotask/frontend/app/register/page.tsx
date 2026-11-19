"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import toast from "react-hot-toast";
import { BaseButton } from "@/components/shared/BaseButton";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { UserPublic } from "@/types";

export default function RegisterPage() {
  const router = useRouter();
  const { status } = useAuth();
  const handleError = useErrorHandler();
  const [name, setName] = useState("");
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
      await apiClient<UserPublic>("/api/auth/register", null, {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      toast.success("Account created. Please log in.");
      router.push("/login");
    } catch (err) {
      handleError(err);
    } finally {
      setSubmitting(false);
    }
  };

  const inputClass = "mt-1 block w-full rounded-md border border-gray-300 px-3 py-2";

  return (
    <main className="flex flex-1 items-center justify-center bg-gray-50 p-4">
      <form onSubmit={onSubmit} className="w-full max-w-sm space-y-4 rounded-lg bg-white p-6 shadow">
        <h1 className="text-2xl font-semibold text-gray-900">Create account</h1>
        <label className="block text-sm font-medium text-gray-700">
          Name
          <input
            required
            minLength={1}
            maxLength={120}
            autoComplete="name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Email
          <input
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className={inputClass}
          />
        </label>
        <label className="block text-sm font-medium text-gray-700">
          Password (8 to 128 characters)
          <input
            type="password"
            required
            minLength={8}
            maxLength={128}
            autoComplete="new-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className={inputClass}
          />
        </label>
        <BaseButton type="submit" loading={submitting} className="w-full">
          Register
        </BaseButton>
        <p className="text-center text-sm text-gray-600">
          Already registered?{" "}
          <Link href="/login" className="font-medium text-blue-600">
            Log in
          </Link>
        </p>
      </form>
    </main>
  );
}
