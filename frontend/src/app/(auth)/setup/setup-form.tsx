"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { PasswordInput } from "@/components/ui/password-input";
import { ApiError, apiClient } from "@/lib/api-client";

type SetupStatus = {
  setupRequired: boolean;
  setupTokenRequired: boolean;
};

type SetupFormState = {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
  setupToken: string;
};

const initialState: SetupFormState = {
  fullName: "",
  email: "",
  password: "",
  confirmPassword: "",
  setupToken: "",
};

export function SetupForm() {
  const router = useRouter();
  const [form, setForm] = useState(initialState);
  const [status, setStatus] = useState<SetupStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    let isMounted = true;
    apiClient
      .get<SetupStatus>("/identity/setup/status")
      .then((nextStatus) => {
        if (isMounted) setStatus(nextStatus);
      })
      .catch(() => {
        if (isMounted) setError("Unable to check installation status. Please try again.");
      })
      .finally(() => {
        if (isMounted) setIsLoading(false);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  function updateField(field: keyof SetupFormState, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);

    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post("/identity/setup", {
        full_name: form.fullName,
        email: form.email,
        password: form.password,
        confirm_password: form.confirmPassword,
        ...(status?.setupTokenRequired ? { setup_token: form.setupToken } : {}),
      });
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to complete setup. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (!isLoading && status && !status.setupRequired) {
    return (
      <Card className="border-[#d4a373]/25 bg-[#f6f1e9] shadow-2xl shadow-black/20">
        <CardHeader>
          <CardTitle className="text-[#10231f]">Setup already completed</CardTitle>
          <CardDescription className="text-[#52645c]">
            This installation already has a Super Administrator.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Button className="w-full bg-[#10231f] text-[#f6f1e9] hover:bg-[#19362f]" onClick={() => router.push("/login")}>
            Continue to sign in
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-[#d4a373]/25 bg-[#f6f1e9] shadow-2xl shadow-black/20">
      <CardHeader className="gap-3 pb-6">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[#a36632]">First installation</p>
        <CardTitle className="text-3xl text-[#10231f]">Create Super Administrator</CardTitle>
        <CardDescription className="max-w-md leading-6 text-[#52645c]">
          Establish the platform account that controls access, security, and future administration.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form className="flex flex-col gap-4" onSubmit={handleSubmit}>
          <div className="flex flex-col gap-2">
            <Label htmlFor="full-name">Full Name</Label>
            <Input id="full-name" autoComplete="name" required value={form.fullName} onChange={(event) => updateField("fullName", event.target.value)} />
          </div>
          <div className="flex flex-col gap-2">
            <Label htmlFor="setup-email">Email</Label>
            <Input id="setup-email" type="email" autoComplete="email" required value={form.email} onChange={(event) => updateField("email", event.target.value)} />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="flex flex-col gap-2">
              <Label htmlFor="setup-password">Password</Label>
              <PasswordInput id="setup-password" autoComplete="new-password" minLength={12} required value={form.password} onChange={(event) => updateField("password", event.target.value)} />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="confirm-password">Confirm Password</Label>
              <PasswordInput id="confirm-password" autoComplete="new-password" minLength={12} required value={form.confirmPassword} onChange={(event) => updateField("confirmPassword", event.target.value)} />
            </div>
          </div>
          {status?.setupTokenRequired ? (
            <div className="flex flex-col gap-2">
              <Label htmlFor="setup-token">Setup Token</Label>
              <PasswordInput id="setup-token" autoComplete="off" showLabel="Show setup token" hideLabel="Hide setup token" required value={form.setupToken} onChange={(event) => updateField("setupToken", event.target.value)} />
            </div>
          ) : null}
          {error ? <p className="text-sm text-destructive" role="alert">{error}</p> : null}
          <Button className="mt-2 h-10 bg-[#10231f] text-[#f6f1e9] hover:bg-[#19362f]" type="submit" disabled={isLoading || isSubmitting}>
            {isSubmitting ? "Creating account..." : "Create administrator"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
