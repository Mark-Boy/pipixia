"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  ShieldAlert,
  Filter,
  RefreshCw,
  Loader2,
  Download,
  AlertTriangle,
} from "lucide-react";
import { settingService } from "@/services";
import { Skeleton } from "@/components/ui/skeleton";

export function RiskPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [riskTypeFilter, setRiskTypeFilter] = useState<string>("all");
  const [logs, setLogs] = useState<any[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [circuitStatus, setCircuitStatus] = useState<any>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const [logsRes, circuitRes] = await Promise.allSettled([
        settingService.getRiskLogs({
          page,
          size: 50,
          ...(riskTypeFilter !== "all" ? { risk_type: riskTypeFilter } : {}),
        }),
        settingService.getCircuitBreakerStatus(),
      ]);

      if (logsRes.status === "fulfilled") {
        setLogs((logsRes.value as any)?.logs || []);
        setTotal((logsRes.value as any)?.total || 0);
      }
      if (circuitRes.status === "fulfilled") {
        setCircuitStatus(circuitRes.value as any);
      }
    } catch (err: any) {
      const msg = err?.message || "未知错误";
      if (!(msg.includes("Network") || msg.includes("timeout"))) {
        setError("无法加载风控数据");
      }
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, [page, riskTypeFilter]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData(false);
  };

  const blockedCount = circuitStatus?.summary?.total_blocked || 0;
  const lowProfitCount = circuitStatus?.summary?.total_low_profit || 0;

  const riskTypeLabels: Record<string, string> = {
    brand: "品牌侵权",
    prohibited: "违禁词",
    profit: "利润不足",
    category: "类目错放",
  };

  const riskTypeColors: Record<string, string> = {
    brand: "bg-red-50 text-red-700 border-red-200",
    prohibited: "bg-orange-50 text-orange-700 border-orange-200",
    profit: "bg-amber-50 text-amber-700 border-amber-200",
    category: "bg-blue-50 text-blue-700 border-blue-200",
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">风控中心</h1>
          <p className="text-muted-foreground">
            查看拦截记录、熔断状态与管理敏感词库
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
          <Button variant="outline" size="sm">
            <Download className="mr-2 h-4 w-4" />
            导出
          </Button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </div>
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              重试
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">今日拦截</p>
            <p className="text-2xl font-bold text-red-600">
              {logs.filter((l) => {
                const d = new Date(l.created_at);
                const today = new Date();
                return d.toDateString() === today.toDateString();
              }).length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">累计拦截</p>
            <p className="text-2xl font-bold">{total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">熔断商品</p>
            <p className="text-2xl font-bold text-orange-600">
              {blockedCount}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">低利润预警</p>
            <p className="text-2xl font-bold text-amber-600">
              {lowProfitCount}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex gap-4">
            <select
              className="rounded-md border px-3 py-2 text-sm"
              value={riskTypeFilter}
              onChange={(e) => setRiskTypeFilter(e.target.value)}
            >
              <option value="all">全部类型</option>
              <option value="brand">品牌侵权</option>
              <option value="prohibited">违禁词</option>
              <option value="profit">利润不足</option>
              <option value="category">类目错放</option>
            </select>
            <div className="flex-1" />
            <span className="text-sm text-muted-foreground self-center">
              第 {page} 页，共 {Math.ceil(total / 50) || 1} 页
            </span>
          </div>
        </CardContent>
      </Card>

      {/* Loading State */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">加载中...</span>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ShieldAlert className="h-5 w-5 text-red-500" />
              风控日志
            </CardTitle>
          </CardHeader>
          <CardContent>
            {logs.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <ShieldAlert className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">暂无风控记录</p>
                <p className="text-sm text-muted-foreground">
                  所有商品均通过风控检测，或暂无拦截记录
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>商品 ID</TableHead>
                    <TableHead>风险类型</TableHead>
                    <TableHead>详情</TableHead>
                    <TableHead>处理操作</TableHead>
                    <TableHead>时间</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {logs.map((log) => (
                    <TableRow key={log.id}>
                      <TableCell className="font-mono text-sm">
                        #{log.product_id}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant="outline"
                          className={
                            riskTypeColors[log.risk_type] ||
                            "bg-gray-50 text-gray-700 border-gray-200"
                          }
                        >
                          {riskTypeLabels[log.risk_type] || log.risk_type}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[300px] truncate">
                        {log.risk_detail}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {log.action_taken || "-"}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground whitespace-nowrap">
                        {log.created_at
                          ? new Date(log.created_at).toLocaleString("zh-CN")
                          : "-"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      )}

      {/* Circuit Breaker Details */}
      {circuitStatus && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Blocked Products */}
          {circuitStatus.blocked_products?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Badge variant="destructive">已拦截</Badge>
                  <span>{circuitStatus.blocked_products.length} 个商品</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {circuitStatus.blocked_products.slice(0, 10).map((p: any) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div>
                        <p className="text-sm font-medium">{p.title}</p>
                        <p className="text-xs text-muted-foreground">
                          利润率: {p.profit_margin ?? "N/A"}%
                        </p>
                      </div>
                      <Badge variant="destructive" className="text-xs">
                        拦截
                      </Badge>
                    </div>
                  ))}
                  {circuitStatus.blocked_products.length > 10 && (
                    <p className="text-xs text-muted-foreground text-center">
                      还有 {circuitStatus.blocked_products.length - 10} 个...
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Low Profit Warning */}
          {circuitStatus.low_profit_products?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                    低利润预警
                  </Badge>
                  <span>{circuitStatus.low_profit_products.length} 个商品</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[300px] overflow-y-auto">
                  {circuitStatus.low_profit_products.slice(0, 10).map((p: any) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div>
                        <p className="text-sm font-medium">{p.title}</p>
                        <p className="text-xs text-muted-foreground">
                          利润率: {p.profit_margin}%（阈值: {p.threshold}%）
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className="bg-amber-50 text-amber-700 border-amber-200"
                      >
                        预警
                      </Badge>
                    </div>
                  ))}
                  {circuitStatus.low_profit_products.length > 10 && (
                    <p className="text-xs text-muted-foreground text-center">
                      还有 {circuitStatus.low_profit_products.length - 10} 个...
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
