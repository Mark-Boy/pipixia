"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
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
import { reportService, settingService } from "@/services";
import { Loader2, RefreshCw, TrendingUp, TrendingDown } from "lucide-react";

export function FinancePage() {
  const [financeData, setFinanceData] = useState<any>(null);
  const [circuitStatus, setCircuitStatus] = useState<any>(null);
  const [exchangeRate, setExchangeRate] = useState<number>(5.0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchData = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const [financeRes, circuitRes, exchangeRes] = await Promise.allSettled([
        reportService.getFinance("2026-07-01"),
        settingService.getCircuitBreakerStatus(),
        settingService.getExchangeRate(),
      ]);

      if (financeRes.status === "fulfilled") {
        setFinanceData(financeRes.value);
      }
      if (circuitRes.status === "fulfilled") {
        setCircuitStatus(circuitRes.value);
      }
      if (exchangeRes.status === "fulfilled") {
        setExchangeRate(exchangeRes.value.rate || 5.0);
      }
    } catch (err: any) {
      console.error("Failed to fetch finance data:", err);
      setError("无法加载财务数据");
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

  // Derived stats
  const totalRevenue = financeData?.summary?.total_revenue_thb || 0;
  const totalCost = financeData?.summary?.total_cost_thb || 0;
  const grossProfit = financeData?.summary?.gross_profit_thb || 0;
  const profitMargin = financeData?.summary?.profit_margin || 0;
  const totalProducts = financeData?.summary?.total_products || 0;

  const blockedCount = circuitStatus?.summary?.total_blocked || 0;
  const lowProfitCount = circuitStatus?.summary?.total_low_profit || 0;

  // Generate chart data from blocked products
  const blockedChartData = (circuitStatus?.blocked_products || []).slice(0, 8).map((p: any) => ({
    name: (p.title || "").slice(0, 10) + "...",
    margin: p.profit_margin || 0,
  }));

  // Low profit chart
  const lowProfitChartData = (circuitStatus?.low_profit_products || []).slice(0, 8).map((p: any) => ({
    name: (p.title || "").slice(0, 10) + "...",
    margin: p.profit_margin || 0,
    threshold: p.threshold || 10,
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">财务看板</h1>
          <p className="text-muted-foreground">
            监控销售额、利润与熔断机制
          </p>
        </div>
        <div className="flex gap-2 items-center">
          <Badge variant="outline" className="text-xs">
            汇率: 1 CNY = {exchangeRate} THB
          </Badge>
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
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4">
            <p className="text-sm text-destructive">⚠️ {error}</p>
          </CardContent>
        </Card>
      )}

      {/* Key Metrics */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总销售额</CardTitle>
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {totalRevenue.toLocaleString()} ฿
            </div>
            <p className="text-xs text-muted-foreground">
              {totalProducts} 个商品
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总利润</CardTitle>
            <TrendingUp className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {grossProfit.toLocaleString()} ฿
            </div>
            <p className="text-xs text-muted-foreground">净利润</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均利润率</CardTitle>
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{profitMargin}%</div>
            <Progress value={profitMargin} className="mt-2 h-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">熔断拦截</CardTitle>
            <Badge variant="destructive" className="text-xs">
              {blockedCount}
            </Badge>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-orange-600">
              {blockedCount}
            </div>
            <p className="text-xs text-muted-foreground">
              低利润预警: {lowProfitCount}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Blocked Products Margin Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">已拦截商品利润率</CardTitle>
            <p className="text-xs text-muted-foreground">
              利润率低于安全阈值的商品
            </p>
          </CardHeader>
          <CardContent>
            {blockedChartData.length === 0 ? (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
                暂无拦截数据
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={blockedChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" fontSize={10} />
                  <YAxis fontSize={10} />
                  <Tooltip />
                  <Bar
                    dataKey="margin"
                    fill="#ef4444"
                    name="利润率 %"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Low Profit Warning Chart */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">低利润预警</CardTitle>
            <p className="text-xs text-muted-foreground">
              利润率低于 10% 的已审核商品
            </p>
          </CardHeader>
          <CardContent>
            {lowProfitChartData.length === 0 ? (
              <div className="flex items-center justify-center h-[200px] text-muted-foreground text-sm">
                暂无预警数据
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={lowProfitChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" fontSize={10} />
                  <YAxis fontSize={10} />
                  <Tooltip />
                  <Bar
                    dataKey="margin"
                    fill="#f59e0b"
                    name="利润率 %"
                    radius={[2, 2, 0, 0]}
                  />
                  <Bar
                    dataKey="threshold"
                    fill="#94a3b8"
                    name="阈值 %"
                    radius={[2, 2, 0, 0]}
                  />
                </BarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Detailed Breakdown */}
      {circuitStatus && (
        <div className="grid gap-4 md:grid-cols-2">
          {/* Blocked Products List */}
          {circuitStatus.blocked_products?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Badge variant="destructive">已拦截</Badge>
                  <span>{circuitStatus.blocked_products.length} 个商品</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[250px] overflow-y-auto">
                  {circuitStatus.blocked_products.map((p: any) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">
                          {p.title}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          ID: #{p.id}
                        </p>
                      </div>
                      <Badge variant="destructive" className="ml-2 shrink-0">
                        拦截
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Low Profit List */}
          {circuitStatus.low_profit_products?.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                    预警
                  </Badge>
                  <span>{circuitStatus.low_profit_products.length} 个商品</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 max-h-[250px] overflow-y-auto">
                  {circuitStatus.low_profit_products.map((p: any) => (
                    <div
                      key={p.id}
                      className="flex items-center justify-between rounded-lg border p-3"
                    >
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-medium truncate">
                          {p.title}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          利润率: {p.profit_margin}%（阈值: {p.threshold}%）
                        </p>
                      </div>
                      <Badge
                        variant="outline"
                        className="bg-amber-50 text-amber-700 border-amber-200 shrink-0"
                      >
                        {p.profit_margin}%
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}
