"use client";
import { useEffect, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";
import { Navbar } from "@/components/layout/Navbar";
import { BaseButton } from "@/components/shared/BaseButton";
import { useAuth } from "@/context/AuthContext";
import { useErrorHandler } from "@/hooks/useErrorHandler";
import { apiClient } from "@/lib/apiClient";
import type { User } from "@/types";

export default function ProfilePage() {
  const router = useRouter();
  const { status, token, user, setUser } = useAuth();
  const handleError = useErrorHandler();
  // null means "untouched": the field shows the current user's value.
  const [name, setName] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  if (status !== "authenticated" || !user) {
    return <p className="p-8 text-center text-gray-500">Loading…</p>;
  }

  const nameValue = name ?? user.name;
  const emailValue = email ?? user.email;
  const dirty = nameValue !== user.name || emailValue !== user.email;

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await apiClient<User>("/api/users/me", token, {
        method: "PATCH",
        body: JSON.stringify({ name: nameValue.trim(), email: emailValue.trim() }),
      });
      setUser(updated);
      setName(null);
      setEmail(null);
      toast.success("Profile updated");
    } catch (err) {
      handleError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <>
      <Navbar />
      <main className="mx-auto w-full max-w-md flex-1 p-4">
        <form onSubmit={onSubmit} className="space-y-4 rounded-lg bg-white p-6 shadow">
          <h1 className="text-2xl font-semibold text-gray-900">Profile</h1>
          <label className="block text-sm font-medium text-gray-700">
            Name
            <input
              required
              maxLength={120}
              value={nameValue}
              onChange={(e) => setName(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
          <label className="block text-sm font-medium text-gray-700">
            Email
            <input
              type="email"
              required
              value={emailValue}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2"
            />
          </label>
          <BaseButton type="submit" loading={saving} disabled={!dirty} className="w-full">
            Save changes
          </BaseButton>
        </form>
      </main>
    </>
  );
}
