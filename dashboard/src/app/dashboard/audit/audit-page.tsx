"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { CheckCircle, XCircle, Loader2, RefreshCw } from "lucide-react";
import { auditService, productService } from "@/services";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

export function AuditPage() {
  const [mode, setMode] = useState<"manual" | "auto">("manual");
  const [audits, setAudits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0 });

  const fetchAudits = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const res = await auditService.getQueue({ status: "pending" });
      const items = (res as any)?.items || [];
      setAudits(items);

      // Also fetch approved/rejected counts
      const [approvedRes, rejectedRes] = await Promise.allSettled([
        auditService.getQueue({ status: "audited" }),
        auditService.getQueue({ status: "rejected" }),
      ]);

      const approved = approvedRes.status === "fulfilled"
        ? ((approvedRes.value as any)?.items?.length ?? 0)
        : 0;
      const rejected = rejectedRes.status === "fulfilled"
        ? ((rejectedRes.value as any)?.items?.length ?? 0)
        : 0;

      setStats({ pending: items.length, approved, rejected });
    } catch (err: any) {
      const msg = err?.message || "未知错误";
      if (!(msg.includes("Network") || msg.includes("timeout"))) {
        setError("无法加载审核队列");
      }
      setAudits([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchAudits();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchAudits(false);
  };

  const handleApprove = async (id: number) => {
    try {
      await auditService.approve(id);
      setAudits((prev) => prev.filter((a) => a.id !== id));
      setStats((s) => ({ ...s, pending: s.pending - 1, approved: s.approved + 1 }));
      setComment("");
    } catch (err: any) {
      toast.error("审核通过失败");
    }
  };

  const handleReject = async (id: number) => {
    if (!comment.trim()) {
      alert("请输入拒绝原因");
      return;
    }
    try {
      await auditService.reject(id, comment);
      setAudits((prev) => prev.filter((a) => a.id !== id));
      setStats((s) => ({ ...s, pending: s.pending - 1, rejected: s.rejected + 1 }));
      setComment("");
    } catch (err: any) {
      toast.error("审核拒绝失败");
    }
  };

  const handleList = async (id: number) => {
    try {
      await auditService.triggerList(id);
      setAudits((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      toast.error("上架失败");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">审核中心</h1>
          <p className="text-muted-foreground">
            审核 AI 翻译优化后的商品信息，确认上架
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            刷新
          </Button>
          <Button
            variant={mode === "manual" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("manual")}
          >
            人工审核
          </Button>
          <Button
            variant={mode === "auto" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("auto")}
          >
            全自动
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">待审核</p>
            <p className="text-2xl font-bold text-amber-600">{stats.pending}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已通过</p>
            <p className="text-2xl font-bold text-green-600">{stats.approved}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已拒绝</p>
            <p className="text-2xl font-bold text-red-600">{stats.rejected}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">审核通过率</p>
            <p className="text-2xl font-bold">
              {stats.pending + stats.approved + stats.rejected > 0
                ? Math.round((stats.approved / (stats.approved + stats.rejected)) * 100)
                : 0}%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Audit Rules */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">审核规则</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">最低预估利润率</span>
            <Badge variant="outline">15%</Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">最小翻译置信度</span>
            <Badge variant="outline">85%</Badge>
          </div>
          <div className="flex justify-between">
            <span className="text-muted-foreground">价格偏离阈值</span>
            <Badge variant="outline">±30%</Badge>
          </div>
        </CardContent>
      </Card>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4 space-y-3">
            <p className="text-sm text-destructive">⚠️ {error}</p>
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              重试
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Audit Queue */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">加载中...</span>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>审核队列 ({audits.length} 条)</CardTitle>
          </CardHeader>
          <CardContent>
            {audits.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                <p className="text-lg font-medium">暂无待审核商品</p>
                <p className="text-sm text-muted-foreground">
                  所有商品已完成审核，或暂无新商品需要审核
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>商品标题</TableHead>
                    <TableHead>泰语标题</TableHead>
                    <TableHead>利润率</TableHead>
                    <TableHead>风控</TableHead>
                    <TableHead>操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {audits.map((item) => (
                    <TableRow key={item.id || item.product_id}>
                      <TableCell className="font-medium max-w-[200px] truncate">
                        {item.title_zh || item.titleZh || "-"}
                      </TableCell>
                      <TableCell className="max-w-[200px] truncate">
                        {item.title_th || item.titleTh || "(待翻译)"}
                      </TableCell>
                      <TableCell>
                        <span
                          className={
                            (item.profit_margin || item.profitMargin || 0) >= 15
                              ? "text-green-600"
                              : "text-red-600"
                          }
                        >
                          {item.profit_margin || item.profitMargin || 0}%
                        </span>
                      </TableCell>
                      <TableCell>
                        {item.risk_flag || item.risk_status === "block" ? (
                          <Badge variant="destructive" className="text-xs">
                            {item.risk_reason || item.risk_detail || "风控拦截"}
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="text-xs bg-green-50 text-green-700 border-green-200">
                            通过
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        <div className="flex gap-1">
                          <Button
                            size="sm"
                            variant="outline"
                            className="bg-green-50 text-green-700 hover:bg-green-100 border-green-200"
                            onClick={() => handleApprove(item.id || item.product_id)}
                          >
                            <CheckCircle className="h-3 w-3 mr-1" />
                            通过
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            className="text-red-600 hover:bg-red-50"
                            onClick={() => handleReject(item.id || item.product_id)}
                          >
                            <XCircle className="h-3 w-3 mr-1" />
                            拒绝
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handleList(item.id || item.product_id)}
                          >
                            <Badge variant="outline" className="text-xs">
                              上架
                            </Badge>
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
