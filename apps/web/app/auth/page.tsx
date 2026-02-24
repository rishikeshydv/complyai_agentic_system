"use client";

import { Eye, EyeOff, Lock, Mail } from "lucide-react";
import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import { Button } from "@/components/ui/button";

export default function AuthPage() {
  const [category, setCategory] = useState<"returning" | "new">("returning");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const router = useRouter();

  const helperText = useMemo(() => {
    if (category === "new") {
      return "Authentication is disabled in this environment. Creating an account is not required for demo usage.";
    }
    return "Authentication is disabled in this environment. Continue directly to the case workbench.";
  }, [category]);

  return (
    <main className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden px-4">
      <div className="w-full max-w-2xl -mt-16 px-2 sm:px-10">
        <div className="rounded-3xl shadow-lg shadow-gray-400/20">
          <div className="overflow-hidden rounded-3xl p-8 backdrop-blur-sm">
            <div className="flex flex-col items-center">
              <h1 className="mb-2 text-center text-[26px] font-bold tracking-tight">Join Comply AI Today!</h1>

              <div className="mb-6 w-full">
                <div className="grid grid-cols-2 rounded-full border border-gray-400/20 bg-white/5 p-1 shadow-sm backdrop-blur-sm">
                  <button
                    className={`w-full rounded-full px-4 py-3 text-center text-[16px] transition-all ${
                      category === "returning" ? "bg-gray-100 text-gray-900 shadow-sm" : "text-gray-400 hover:bg-white/10"
                    }`}
                    onClick={() => {
                      setCategory("returning");
                      setConfirmPassword("");
                    }}
                  >
                    Returning User
                  </button>
                  <button
                    className={`w-full rounded-full px-4 py-3 text-center text-[16px] transition-all ${
                      category === "new" ? "bg-gray-100 text-gray-900 shadow-sm" : "text-gray-400 hover:bg-white/10"
                    }`}
                    onClick={() => setCategory("new")}
                  >
                    New User
                  </button>
                </div>
              </div>

              <div className="mb-6 w-full space-y-4">
                <div className="relative">
                  <Mail className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-black/50" />
                  <input
                    type="email"
                    placeholder="Enter your e-mail address"
                    className="w-full rounded-full border-none bg-gray-100 py-4 pl-12 pr-4 placeholder:text-black/50 focus:outline-none"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>

                <div className="relative">
                  <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-black/50" />
                  <input
                    type={showPassword ? "text" : "password"}
                    placeholder="Enter your password"
                    className="w-full rounded-full border-none bg-gray-100 py-4 pl-12 pr-12 placeholder:text-black/50 focus:outline-none"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                  <button
                    className="absolute right-4 top-1/2 -translate-y-1/2 text-black"
                    onClick={() => setShowPassword((prev) => !prev)}
                  >
                    {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>

                {category === "new" ? (
                  <div className="relative">
                    <Lock className="absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-black/50" />
                    <input
                      type={showConfirmPassword ? "text" : "password"}
                      placeholder="Confirm your password"
                      className="w-full rounded-full border-none bg-gray-100 py-4 pl-12 pr-12 placeholder:text-black/50 focus:outline-none"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                    />
                    <button
                      className="absolute right-4 top-1/2 -translate-y-1/2 text-black"
                      onClick={() => setShowConfirmPassword((prev) => !prev)}
                    >
                      {showConfirmPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                    </button>
                  </div>
                ) : null}
              </div>

              <div className="w-full space-y-4">
                <Button
                  className="w-full rounded-full py-3 text-[16px]"
                  onClick={() => router.push("/cases")}
                >
                  {category === "new" ? "Create Account" : "Login"}
                </Button>
                <p className="text-center text-sm text-black/70">{helperText}</p>
                <Button
                  variant="outline"
                  className="w-full rounded-full bg-gray-100 py-3 text-[16px]"
                  onClick={() => router.push("/cases")}
                >
                  Continue to Cases
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
