"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  Package,
  Shield,
  Wallet,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  Legend,
} from "recharts";
import { reportService, productService, settingService } from "@/services";
import { Skeleton } from "@/components/ui/skeleton";

export function OverviewPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<any>(null);
  const [dailyReport, setDailyReport] = useState<any>(null);
  const [products, setProducts] = useState<any[]>([]);
  const [exchangeRate, setExchangeRate] = useState<number>(5.0);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const [summaryRes, dailyRes, productsRes, exchangeRes] = await Promise.allSettled([
        reportService.getSummary(),
        reportService.getDaily(),
        productService.getList({ page: 1, size: 10 }),
        settingService.getExchangeRate(),
      ]);

      if (summaryRes.status === "fulfilled") {
        setSummary(summaryRes.value as any);
      }
      if (dailyRes.status === "fulfilled") {
        setDailyReport(dailyRes.value as any);
      }
      if (productsRes.status === "fulfilled") {
        setProducts(((productsRes.value as any)?.products) as any || []);
      }
      if (exchangeRes.status === "fulfilled") {
        setExchangeRate(((exchangeRes.value as any)?.rate as number) || 5.0);
      }
    } catch (err: any) {
      setError(err.message || "加载数据失败");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchData(false);
  };

  const pendingAudits = products.filter(
    (p: any) => p.status === "pending" || p.status === "auditing"
  ).length;
  const blockedProducts = products.filter(
    (p: any) => p.status === "blocked" || p.risk_status === "block"
  ).length;
  const listedCount = products.filter(
    (p: any) => p.status === "listed" || p.status === "active"
  ).length;

  // Build weekly trend from products data (last 7 days)
  const weeklyData = (() => {
    const days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];
    const now = new Date();
    return days.map((day, i) => {
      const date = new Date(now);
      date.setDate(date.getDate() - ((now.getDay() + 7 - (i + 1)) % 7));
      const dateStr = date.toISOString().split("T")[0];
      const dayProducts = products.filter((p: any) => {
        const created = p.created_at?.split("T")[0];
        return created === dateStr;
      });
      return {
        day,
        imported: dayProducts.length,
        listed: dayProducts.filter((p: any) => p.status === "listed" || p.status === "active").length,
        failed: dayProducts.filter((p: any) => p.status === "blocked" || p.status === "rejected").length,
      };
    });
  })();

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <Skeleton className="h-8 w-40" />
            <Skeleton className="h-4 w-64" />
          </div>
          <Skeleton className="h-9 w-20" />
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <Card key={i}>
              <CardContent className="pt-6 space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-7 w-16" />
                <Skeleton className="h-3 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardContent className="pt-6"><Skeleton className="h-[250px] w-full" /></CardContent></Card>
          <Card><CardContent className="pt-6"><Skeleton className="h-[250px] w-full" /></CardContent></Card>
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card><CardContent className="pt-6"><Skeleton className="h-[200px] w-full" /></CardContent></Card>
          <Card><CardContent className="pt-6"><Skeleton className="h-[200px] w-full" /></CardContent></Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">数据看板</h1>
          <p className="text-muted-foreground">
            实时监控商品上架、审核、财务与风控数据
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-xs">
            汇率: 1 CNY = {exchangeRate} THB
          </Badge>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-3 py-2 text-sm rounded-md border hover:bg-muted transition-colors"
          >
            {refreshing ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            刷新
          </button>
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">⚠️ {error}</p>
          </CardContent>
        </Card>
      )}

      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">在售商品</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{listedCount}</div>
            <p className="text-xs text-muted-foreground">
              总计 {products.length} 个商品
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">待审核</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{pendingAudits}</div>
            <p className="text-xs text-muted-foreground">
              需要人工确认
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总销售额</CardTitle>
            <Wallet className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dailyReport?.statistics?.total_products
                ? (dailyReport.statistics.total_products * 150).toLocaleString()
                : "0"}{" "}
              ฿
            </div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 text-green-600" /> 估算值
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均利润率</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {products.length > 0
                ? (products.reduce((sum, p) => sum + (p.profit_margin || 0), 0) / products.length).toFixed(1)
                : "0"}
              %
            </div>
            <Progress
              value={products.length > 0
                ? products.reduce((sum, p) => sum + (p.profit_margin || 0), 0) / products.length
                : 0}
              className="mt-2 h-2"
            />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">风控拦截</CardTitle>
            <Shield className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{blockedProducts}</div>
            <p className="text-xs text-muted-foreground">
              当前拦截数
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>近7日上架趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={weeklyData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="imported"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.3}
                  name="导入数"
                />
                <Area
                  type="monotone"
                  dataKey="listed"
                  stroke="#82ca9d"
                  fill="#82ca9d"
                  fillOpacity={0.3}
                  name="成功上架"
                />
                <Area
                  type="monotone"
                  dataKey="failed"
                  stroke="#ff7300"
                  fill="#ff7300"
                  fillOpacity={0.3}
                  name="失败"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>商品利润率分布</CardTitle>
          </CardHeader>
          <CardContent>
            {products.length === 0 ? (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
                暂无商品数据
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <BarChart data={products.slice(0, 10).map((p: any) => ({
                  name: (p.title_zh || p.titleZh || "").slice(0, 8) + "...",
                  margin: p.profit_margin || 0,
                }))}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" fontSize={10} />
                  <YAxis fontSize={10} />
                  <Tooltip />
                  <Bar
                    dataKey="margin"
                    fill="#8884d8"
                    name="利润率 %"
                    radius={[4, 4, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Alerts & Recent Activity */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Alerts */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-amber-500" />
              告警与待办
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between rounded-lg border-l-4 border-blue-500 bg-blue-50 p-3">
              <div>
                <p className="text-sm font-medium">待审核商品</p>
                <p className="text-xs text-muted-foreground">
                  有 {pendingAudits} 件商品等待人工审核
                </p>
              </div>
              <Badge variant="outline">{pendingAudits}</Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border-l-4 border-red-500 bg-red-50 p-3">
              <div>
                <p className="text-sm font-medium">风控拦截</p>
                <p className="text-xs text-muted-foreground">
                  当前 {blockedProducts} 个商品被拦截
                </p>
              </div>
              <Badge variant="destructive">{blockedProducts}</Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border-l-4 border-amber-500 bg-amber-50 p-3">
              <div>
                <p className="text-sm font-medium">汇率信息</p>
                <p className="text-xs text-muted-foreground">
                  当前 1 CNY = {exchangeRate} THB
                </p>
              </div>
              <Badge variant="secondary">{exchangeRate.toFixed(2)}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Recent Products */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              最近商品
              <Badge variant="outline" className="text-xs">
                共 {products.length} 条
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {products.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-8 text-center text-muted-foreground text-sm">
                  <Package className="h-8 w-8 mb-2 opacity-50" />
                  <p>暂无商品数据</p>
                  <p className="text-xs">请先导入商品</p>
                </div>
              ) : (
                products.slice(0, 5).map((product: any) => (
                  <div
                    key={product.id}
                    className="flex items-center justify-between rounded-lg border p-3"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {product.title_zh || product.titleZh}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {(product.source_platform || product.sourcePlatform || "") === "1688" ? "1688" : "拼多多"} ·{" "}
                        利润率 {(product.profit_margin || product.profitMargin || 0).toFixed(1)}%
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-2 shrink-0">
                      {(product.status === "listed" || product.status === "active") && (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 text-xs">
                          <CheckCircle className="mr-1 h-3 w-3" />
                          已上架
                        </Badge>
                      )}
                      {(product.status === "auditing" || product.status === "pending") && (
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200 text-xs">
                          <Clock className="mr-1 h-3 w-3" />
                          审核中
                        </Badge>
                      )}
                      {(product.status === "blocked" || product.risk_status === "block") && (
                        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 text-xs">
                          <XCircle className="mr-1 h-3 w-3" />
                          拦截
                        </Badge>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
