import { Suspense } from "react";

import { LoginForm } from "@/app/login/LoginForm";

export default function LoginPage() {
  return (
    <Suspense fallback={<p className="p-8 text-center text-neutral-600">Loading…</p>}>
      <LoginForm />
    </Suspense>
  );
}
