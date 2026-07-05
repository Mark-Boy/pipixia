"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Package2 } from "lucide-react";
import { toast } from "sonner";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

      if (mode === "login") {
        // 登录
        const response = await fetch(`${API_URL}/api/v1/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
          credentials: "include",
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "登录失败");
        }

        const data = await response.json();
        localStorage.setItem("access_token", data.access_token);
        toast.success("登录成功！");
        router.push("/dashboard/overview");
      } else {
        // 注册
        const response = await fetch(`${API_URL}/api/v1/auth/register`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username,
            email,
            password,
            role: "operator",
          }),
        });

        if (!response.ok) {
          const data = await response.json();
          throw new Error(data.detail || "注册失败");
        }

        const data = await response.json();
        localStorage.setItem("access_token", data.access_token);
        toast.success("注册成功！");
        router.push("/dashboard/overview");
      }
    } catch (error: any) {
      toast.error(error.message || "操作失败");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-muted/40 p-4">
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-primary">
            <Package2 className="h-6 w-6 text-primary-foreground" />
          </div>
          <CardTitle className="text-2xl">pipixia</CardTitle>
          <CardDescription>
            跨境电商自动上架工具
          </CardDescription>
        </CardHeader>
        <CardContent>
          {/* 切换登录/注册 */}
          <div className="flex gap-2 mb-6">
            <Button
              variant={mode === "login" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("login")}
              className="flex-1"
            >
              登录
            </Button>
            <Button
              variant={mode === "register" ? "default" : "outline"}
              size="sm"
              onClick={() => setMode("register")}
              className="flex-1"
            >
              注册
            </Button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === "register" && (
              <div className="space-y-2">
                <Label htmlFor="username">用户名</Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="your_username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  minLength={3}
                  maxLength={50}
                />
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input
                id="email"
                type="email"
                placeholder="admin@pipixia.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? "处理中..." : mode === "login" ? "登录" : "注册"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
