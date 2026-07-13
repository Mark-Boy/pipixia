"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import { Loader2, QrCode, Trash2, RefreshCw, LogIn, LogOut, Package, Eye, Copy, CheckCircle, AlertCircle, Clock, Smartphone } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogTrigger } from "@/components/ui/dialog";
import { shopService, pddAccountService } from "@/services";

interface PddAccount {
  id: number;
  user_id: number;
  account_name: string;
  phone: string | null;
  notes: string | null;
  login_status: "pending" | "logged_in" | "expired" | "error";
  last_login_at: string | null;
  expires_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface QrcodeSession {
  qrcode_token: string;
  status: "generating" | "waiting" | "scanned" | "confirmed" | "success" | "failed" | "expired" | "error";
  qrcode_image: string | null;
  message: string;
  account_id: number | null;
}

const STATUS_CONFIG = {
  pending: { label: "待登录", color: "bg-gray-100 text-gray-700 border-gray-300" },
  logged_in: { label: "已登录", color: "bg-green-100 text-green-700 border-green-300" },
  expired: { label: "已过期", color: "bg-yellow-100 text-yellow-700 border-yellow-300" },
  error: { label: "异常", color: "bg-red-100 text-red-700 border-red-300" },
};

const QRCODE_STATUS_CONFIG = {
  generating: { label: "生成中...", icon: Loader2, color: "text-blue-500 animate-spin" },
  waiting: { label: "待扫码", icon: Smartphone, color: "text-blue-500" },
  scanned: { label: "已扫码，待确认", icon: CheckCircle, color: "text-yellow-500" },
  confirmed: { label: "已确认，登录中...", icon: Loader2, color: "text-blue-500 animate-spin" },
  success: { label: "登录成功", icon: CheckCircle, color: "text-green-500" },
  failed: { label: "登录失败", icon: AlertCircle, color: "text-red-500" },
  expired: { label: "二维码过期", icon: Clock, color: "text-gray-500" },
  error: { label: "错误", icon: AlertCircle, color: "text-red-500" },
};

export default function PddAccountsPage() {
  const router = useRouter();
  const [accounts, setAccounts] = useState<PddAccount[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 创建账号对话框
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState({ account_name: "", phone: "", notes: "" });
  const [creating, setCreating] = useState(false);

  // 二维码登录相关
  const [qrcodeDialogOpen, setQrcodeDialogOpen] = useState(false);
  const [currentQrcodeAccount, setCurrentQrcodeAccount] = useState<PddAccount | null>(null);
  const [qrcodeSession, setQrcodeSession] = useState<QrcodeSession | null>(null);
  const [pollingInterval, setPollingInterval] = useState<NodeJS.Timeout | null>(null);

  // 获取账号列表
  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await pddAccountService.getList({ page: 1, size: 50 });
      const list = (res as any)?.accounts || (res as any)?.items || [];
      setAccounts(list);
    } catch (err: any) {
      const msg = err?.message || "加载账号列表失败";
      setError(msg);
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // 创建账号
  const handleCreate = async () => {
    if (!createForm.account_name.trim()) {
      toast.error("请输入账号备注名");
      return;
    }
    setCreating(true);
    try {
      await pddAccountService.create(createForm);
      toast.success("账号创建成功");
      setCreateDialogOpen(false);
      setCreateForm({ account_name: "", phone: "", notes: "" });
      fetchAccounts();
    } catch (err: any) {
      toast.error(err?.message || "创建失败");
    } finally {
      setCreating(false);
    }
  };

  // 删除账号
  const handleDelete = async (id: number) => {
    if (!confirm("确定要删除这个采集账号吗？")) return;
    try {
      await pddAccountService.delete(id);
      toast.success("已删除");
      fetchAccounts();
    } catch (err: any) {
      toast.error(err?.message || "删除失败");
    }
  };

  // 生成二维码
  const handleGenerateQrcode = async (account: PddAccount) => {
    setCurrentQrcodeAccount(account);
    setQrcodeDialogOpen(true);
    setQrcodeSession({
      qrcode_token: "",
      status: "generating",
      qrcode_image: null,
      message: "正在生成二维码...",
      account_id: null,
    });

    try {
      const res = await pddAccountService.generateQrcode(account.id);
      const data = res as any;
      setQrcodeSession({
        qrcode_token: data.qrcode_token,
        status: "waiting",
        qrcode_image: data.qrcode_image,
        message: "请使用拼多多买家版 APP 扫码登录",
        account_id: data.account_id,
      });

      // 开始轮询
      startPolling(data.qrcode_token);
    } catch (err: any) {
      setQrcodeSession(prev => prev ? {
        ...prev,
        status: "error",
        message: err?.message || "生成二维码失败",
      } : null);
      toast.error(err?.message || "生成二维码失败");
    }
  };

  // 轮询二维码状态
  const startPolling = (token: string) => {
    if (pollingInterval) clearInterval(pollingInterval);

    const interval = setInterval(async () => {
      try {
        const res = await pddAccountService.checkQrcodeStatus(token);
        const data = res as any;

        setQrcodeSession(prev => prev ? {
          ...prev,
          status: data.status,
          qrcode_image: data.qrcode_image || prev.qrcode_image,
          message: data.message,
          account_id: data.account_id || prev.account_id,
        } : null);

        if (data.status === "success" || data.status === "confirmed") {
          clearInterval(interval);
          setPollingInterval(null);
          toast.success("登录成功！");
          // 3秒后关闭对话框并刷新列表
          setTimeout(() => {
            setQrcodeDialogOpen(false);
            setQrcodeSession(null);
            fetchAccounts();
          }, 3000);
        } else if (data.status === "failed" || data.status === "expired" || data.status === "error") {
          clearInterval(interval);
          setPollingInterval(null);
          toast.error(data.message || "登录失败");
        }
      } catch (err: any) {
        // 忽略轮询错误，继续轮询
        console.error("Polling error:", err);
      }
    }, 3000);

    setPollingInterval(interval);
  };

  // 清理轮询
  useEffect(() => {
    return () => {
      if (pollingInterval) clearInterval(pollingInterval);
    };
  }, [pollingInterval]);

  // 登出账号
  const handleLogout = async (account: PddAccount) => {
    if (!confirm(`确定要登出账号 "${account.account_name}" 吗？`)) return;
    try {
      await pddAccountService.logout(account.id);
      toast.success("已登出");
      fetchAccounts();
    } catch (err: any) {
      toast.error(err?.message || "登出失败");
    }
  };

  // 复制二维码 token（用于调试）
  const copyToken = (token: string) => {
    navigator.clipboard.writeText(token);
    toast.success("已复制到剪贴板");
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "-";
    return new Date(dateStr).toLocaleString("zh-CN");
  };

  return (
    <div className="space-y-6">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard/products")}>
            <Package className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <QrCode className="h-6 w-6 text-purple-500" />
              拼多多商家采集账号
            </h1>
            <p className="text-muted-foreground">
              管理拼多多买家版扫码登录账号，用于采集店铺商品
            </p>
          </div>
        </div>
        <Button onClick={() => setCreateDialogOpen(true)} disabled={creating}>
          {creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <LogIn className="mr-2 h-4 w-4" />}
          添加采集账号
        </Button>
      </div>

      {/* 错误提示 */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
            <Button variant="outline" size="sm" onClick={fetchAccounts}>
              <RefreshCw className="mr-2 h-4 w-4" />
              重试
            </Button>
          </CardContent>
        </Card>
      )}

      {/* 账号列表 */}
      {!loading && !error && (
        <Card>
          <CardContent className="pt-0">
            {accounts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16">
                <QrCode className="h-16 w-16 text-muted-foreground/50 mb-4" />
                <p className="text-lg font-medium">暂无采集账号</p>
                <p className="text-sm text-muted-foreground">点击「添加采集账号」创建第一个账号</p>
                <Button className="mt-4" onClick={() => setCreateDialogOpen(true)}>
                  <LogIn className="mr-2 h-4 w-4" />
                  添加采集账号
                </Button>
              </div>
            ) : (
              <div className="divide-y">
                {accounts.map((account) => (
                  <div key={account.id} className="p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                    <div className="flex items-center gap-4 flex-1 min-w-0">
                      <div className="p-3 bg-purple-50 rounded-lg">
                        <QrCode className="h-6 w-6 text-purple-600" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-medium truncate">{account.account_name}</p>
                        <p className="text-sm text-muted-foreground">
                          {account.phone ? `手机: ${account.phone}` : "未绑定手机"}
                          {account.notes && ` · 备注: ${account.notes}`}
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 flex-wrap">
                      <Badge
                        variant="outline"
                        className={`gap-1 ${STATUS_CONFIG[account.login_status]?.color || "bg-gray-100 text-gray-700"}`}
                      >
                        {account.login_status === "logged_in" && <CheckCircle className="h-3 w-3" />}
                        {account.login_status === "expired" && <Clock className="h-3 w-3" />}
                        {account.login_status === "error" && <AlertCircle className="h-3 w-3" />}
                        {STATUS_CONFIG[account.login_status]?.label || account.login_status}
                      </Badge>

                      {account.last_login_at && (
                        <span className="text-xs text-muted-foreground">
                          最后登录: {formatDate(account.last_login_at)}
                        </span>
                      )}

                      <div className="flex items-center gap-2">
                        {account.login_status !== "logged_in" ? (
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => handleGenerateQrcode(account)}
                            disabled={loading}
                          >
                            <QrCode className="mr-1 h-3 w-3" />
                            扫码登录
                          </Button>
                        ) : (
                          <>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => handleLogout(account)}
                              disabled={loading}
                              className="text-orange-600 hover:text-orange-700"
                            >
                              <LogOut className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => copyToken(`account_${account.id}`)}
                              className="text-muted-foreground hover:text-foreground"
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          </>
                        )}

                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDelete(account.id)}
                          disabled={loading}
                          className="text-red-600 hover:text-red-700"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* 加载骨架屏 */}
      {loading && (
        <Card>
          <CardContent className="pt-0">
            <div className="space-y-4">
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 p-4">
                  <div className="h-10 w-10 rounded-lg bg-muted animate-pulse" />
                  <div className="flex-1 space-y-2">
                    <div className="h-4 w-48 bg-muted animate-pulse rounded" />
                    <div className="h-3 w-64 bg-muted animate-pulse rounded" />
                  </div>
                  <div className="h-6 w-24 bg-muted animate-pulse rounded" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 创建账号对话框 */}
      <Dialog open={createDialogOpen} onOpenChange={setCreateDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>添加拼多多采集账号</DialogTitle>
            <DialogDescription>
              输入账号备注信息，创建后可通过扫码登录拼多多买家版
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="account_name">账号备注名 *</Label>
              <Input
                id="account_name"
                placeholder="例如：主店铺、测试店铺、分店A"
                value={createForm.account_name}
                onChange={(e) => setCreateForm({ ...createForm, account_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="phone">手机号（可选）</Label>
              <Input
                id="phone"
                type="tel"
                placeholder="13800138000"
                value={createForm.phone}
                onChange={(e) => setCreateForm({ ...createForm, phone: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="notes">备注（可选）</Label>
              <textarea
                id="notes"
                className="w-full rounded-md border px-3 py-2 min-h-[80px] focus:outline-none focus:ring-2 focus:ring-ring"
                placeholder="备注信息..."
                value={createForm.notes}
                onChange={(e) => setCreateForm({ ...createForm, notes: e.target.value })}
              />
            </div>
            <div className="flex gap-2 justify-end pt-4">
              <Button variant="outline" onClick={() => setCreateDialogOpen(false)} disabled={creating}>
                取消
              </Button>
              <Button onClick={handleCreate} disabled={creating}>
                {creating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                创建账号
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* 二维码登录对话框 */}
      <Dialog open={qrcodeDialogOpen} onOpenChange={(open) => {
        if (!open) {
          if (pollingInterval) clearInterval(pollingInterval);
          setPollingInterval(null);
          setQrcodeSession(null);
          setCurrentQrcodeAccount(null);
        }
        setQrcodeDialogOpen(open);
      }}>
        <DialogContent className="max-w-lg max-h-[90vh]">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <QrCode className="h-5 w-5 text-purple-500" />
              扫码登录拼多多买家版
            </DialogTitle>
            <DialogDescription>
              账号: {currentQrcodeAccount?.account_name} · 请使用<strong> 拼多多买家版 APP </strong>扫描下方二维码
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            {qrcodeSession && (
              <>
                {/* 状态指示器 */}
                <div className="flex items-center gap-3 p-3 rounded-lg bg-muted/50">
                  {(() => {
                    const cfg = QRCODE_STATUS_CONFIG[qrcodeSession.status as keyof typeof QRCODE_STATUS_CONFIG];
                    if (!cfg) return null;
                    return (
                      <div className="flex items-center gap-2">
                        <cfg.icon className={`h-5 w-5 ${cfg.color}`} />
                        <span className="font-medium">{cfg.label}</span>
                      </div>
                    );
                  })()}
                </div>

                {/* 二维码图片 */}
                {qrcodeSession.qrcode_image && (
                  <div className="flex flex-col items-center gap-3">
                    <img
                      src={qrcodeSession.qrcode_image}
                      alt="拼多多登录二维码"
                      className="rounded-lg border p-4 bg-white max-w-xs"
                    />
                    <p className="text-sm text-muted-foreground text-center">
                      二维码 3 分钟有效 · 请在拼多多买家版 APP 中「扫一扫」登录
                    </p>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToken(qrcodeSession.qrcode_token)}
                      className="w-full sm:w-auto"
                    >
                      <Copy className="mr-1 h-3 w-3" />
                      复制 Token
                    </Button>
                  </div>
                )}

                {/* 生成中加载态 */}
                {qrcodeSession.status === "generating" && (
                  <div className="flex flex-col items-center gap-4 py-8">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <p className="text-muted-foreground">正在打开拼多多登录页并生成二维码...</p>
                  </div>
                )}

                {/* 成功/失败状态 */}
                {(qrcodeSession.status === "success" || qrcodeSession.status === "failed" ||
                  qrcodeSession.status === "expired" || qrcodeSession.status === "error") && (
                  <div className={`p-4 rounded-lg text-center ${
                    qrcodeSession.status === "success" ? "bg-green-50 text-green-700" :
                    qrcodeSession.status === "failed" ? "bg-red-50 text-red-700" :
                    "bg-yellow-50 text-yellow-700"
                  }`}>
                    <p className="font-medium">{qrcodeSession.message}</p>
                    {qrcodeSession.status === "success" && (
                      <p className="text-sm mt-1">即将自动关闭并刷新账号列表...</p>
                    )}
                  </div>
                )}

                {/* 调试信息 */}
                {process.env.NODE_ENV === "development" && qrcodeSession.qrcode_token && (
                  <details className="text-xs text-muted-foreground">
                    <summary>调试信息</summary>
                    <pre className="mt-2 p-2 bg-muted rounded overflow-auto">
                      Token: {qrcodeSession.qrcode_token}
                      <br />
                      Account ID: {qrcodeSession.account_id}
                    </pre>
                  </details>
                )}
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}