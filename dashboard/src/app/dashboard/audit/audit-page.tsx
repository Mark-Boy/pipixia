"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { mockAudits } from "@/lib/mock-data";
import { CheckCircle, XCircle, Edit, Eye, MessageSquare, Loader2, RefreshCw } from "lucide-react";
import { auditService } from "@/services";

export function AuditPage() {
  const [mode, setMode] = useState<"manual" | "auto">("manual");
  const [audits, setAudits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [comment, setComment] = useState("");
  const [refreshing, setRefreshing] = useState(false);

  const fetchAudits = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await auditService.getQueue({
        status: "pending",
        credentials_str: `Bearer ${token}`,
      });
      // 后端返回的是 Product 列表，转换为 AuditItem 格式
      const items = (res || []).map((p: any) => ({
        id: String(p.id),
        productId: String(p.id),
        titleZh: p.title_zh || p.titleZh,
        titleTh: p.title_th || p.titleTh || "(待翻译)",
        descriptionTh: p.description_th || p.descriptionTh || "",
        profitMargin: p.profit_margin || p.profitMargin || 0,
        confidenceScore: 0.9,
        riskFlag: p.risk_status === "block",
        riskReason: p.risk_detail || "风控拦截",
        status: "pending" as const,
        createdAt: p.created_at,
      }));
      setAudits(items.length > 0 ? items : mockAudits);
    } catch (err: any) {
      console.error("Failed to fetch audits:", err);
      setAudits(mockAudits);
      setError("无法加载审核队列，已使用模拟数据");
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

  const handleApprove = async (id: string) => {
    try {
      const token = localStorage.getItem("access_token");
      await auditService.approve(id, `Bearer ${token}`);
      setAudits((prev) => prev.filter((a) => a.id !== id));
      setComment("");
    } catch (err: any) {
      alert("审核通过失败: " + (err.message || "未知错误"));
    }
  };

  const handleReject = async (id: string) => {
    if (!comment.trim()) {
      alert("请输入拒绝原因");
      return;
    }
    try {
      const token = localStorage.getItem("access_token");
      await auditService.reject(id, comment, `Bearer ${token}`);
      setAudits((prev) => prev.filter((a) => a.id !== id));
      setComment("");
    } catch (err: any) {
      alert("审核拒绝失败: " + (err.message || "未知错误"));
    }
  };

  const handleList = async (id: string) => {
    try {
      const token = localStorage.getItem("access_token");
      await auditService.triggerList(Number(id), `Bearer ${token}`);
      setAudits((prev) => prev.filter((a) => a.id !== id));
    } catch (err: any) {
      alert("上架失败: " + (err.message || "未知错误"));
    }
  };

  const pendingCount = audits.filter((a) => a.status === "pending").length;
  const totalApproved = 128;
  const totalRejected = 3;

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
          <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
            {refreshing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
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
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">待审核</p>
            <p className="text-2xl font-bold text-amber-600">{pendingCount}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已通过</p>
            <p className="text-2xl font-bold text-green-600">{totalApproved}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已拒绝</p>
            <p className="text-2xl font-bold text-red-600">{totalRejected}</p>
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
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">⚠️ {error}</p>
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
        <div className="space-y-4">
          {audits.map((audit) => (
            <Card key={audit.id} className={`overflow-hidden ${selectedId === audit.id ? "ring-2 ring-primary" : ""}`}>
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{audit.titleZh}</CardTitle>
                    <p className="text-sm text-muted-foreground mt-1">
                      利润: {audit.profitMargin}% | 置信度:{" "}
                      {(audit.confidenceScore * 100).toFixed(0)}%
                      {audit.riskFlag && (
                        <Badge variant="destructive" className="ml-2">
                          {audit.riskReason}
                        </Badge>
                      )}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon">
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon">
                      <Edit className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <Separator />
              <CardContent className="pt-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <p className="text-sm font-medium mb-2">中文原文</p>
                    <p className="text-sm text-muted-foreground">
                      {audit.titleZh}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm font-medium mb-2">泰语翻译</p>
                    <p className="text-sm">{audit.titleTh}</p>
                  </div>
                </div>
                {audit.descriptionTh && (
                  <div className="mt-4">
                    <p className="text-sm font-medium mb-2">描述翻译</p>
                    <p className="text-sm text-muted-foreground">
                      {audit.descriptionTh}
                    </p>
                  </div>
                )}
                {audit.riskFlag && (
                  <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
                    <XCircle className="h-4 w-4" />
                    {audit.riskReason}
                  </div>
                )}
                <div className="mt-4 flex gap-2">
                  <Button
                    size="sm"
                    className="bg-green-600 hover:bg-green-700"
                    onClick={() => handleApprove(audit.id)}
                  >
                    <CheckCircle className="mr-2 h-4 w-4" />
                    通过
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    className="text-red-600 hover:text-red-700 hover:bg-red-50"
                    onClick={() => handleReject(audit.id)}
                  >
                    <XCircle className="mr-2 h-4 w-4" />
                    拒绝
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => handleList(audit.id)}
                  >
                    <Eye className="mr-2 h-4 w-4" />
                    上架
                  </Button>
                </div>
                <div className="mt-3">
                  <Textarea
                    placeholder="添加审核备注..."
                    value={comment}
                    onChange={(e) => setComment(e.target.value)}
                    className="min-h-[60px]"
                  />
                </div>
              </CardContent>
            </Card>
          ))}

          {audits.length === 0 && (
            <Card>
              <CardContent className="flex flex-col items-center justify-center py-12 text-center">
                <CheckCircle className="h-12 w-12 text-green-500 mb-4" />
                <p className="text-lg font-medium">暂无待审核商品</p>
                <p className="text-sm text-muted-foreground">
                  所有商品已完成审核，或暂无新商品需要审核
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
