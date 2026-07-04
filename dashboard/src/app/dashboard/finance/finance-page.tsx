"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { mockFinancialMetrics } from "@/lib/mock-data";
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
import { reportService } from "@/services";
import { Loader2, RefreshCw } from "lucide-react";

const profitTrend = [
  { date: "7/1", estimated: 2500, actual: 2380 },
  { date: "7/2", estimated: 3200, actual: 3150 },
  { date: "7/3", estimated: 2800, actual: 2720 },
  { date: "7/4", estimated: 3500, actual: 3420 },
];

const categoryProfit = [
  { name: "手机配件", estimated: 28, actual: 26, margin: 28.5 },
  { name: "数码周边", estimated: 22, actual: 21, margin: 22.1 },
  { name: "家居用品", estimated: 19, actual: 18, margin: 18.7 },
];

export function FinancePage() {
  const [financeData, setFinanceData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchFinance = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await reportService.getFinance("2026-07-01");
      setFinanceData(res);
    } catch (err: any) {
      console.error("Failed to fetch finance:", err);
      setError("无法加载财务数据");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFinance();
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">财务看板</h1>
          <p className="text-muted-foreground">
            监控销售额、利润与熔断机制
          </p>
        </div>
        <button
          onClick={fetchFinance}
          className="flex items-center gap-2 px-3 py-2 text-sm rounded-md border hover:bg-muted transition-colors"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          刷新
        </button>
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
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {financeData?.summary?.total_revenue_thb?.toLocaleString() || mockFinancialMetrics.totalSales.toLocaleString()} ฿
            </div>
            <p className="text-xs text-muted-foreground">本月累计</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">总利润</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">
              {financeData?.summary?.gross_profit_thb?.toLocaleString() || mockFinancialMetrics.totalProfit.toLocaleString()} ฿
            </div>
            <p className="text-xs text-muted-foreground">净利润</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">平均利润率</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {financeData?.summary?.profit_margin || mockFinancialMetrics.avgProfitMargin}%
            </div>
            <Progress value={financeData?.summary?.profit_margin || mockFinancialMetrics.avgProfitMargin} className="mt-2" />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">利润校准偏差</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {mockFinancialMetrics.profitDeviation}%
            </div>
            <Badge variant={mockFinancialMetrics.profitDeviation < 0 ? "destructive" : "default"}>
              {mockFinancialMetrics.profitDeviation < 0 ? "偏低" : "正常"}
            </Badge>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>预估利润 vs 实际利润</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={profitTrend}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Area
                  type="monotone"
                  dataKey="estimated"
                  stroke="#8884d8"
                  fill="#8884d8"
                  fillOpacity={0.3}
                  name="预估"
                />
                <Area
                  type="monotone"
                  dataKey="actual"
                  stroke="#82ca9d"
                  fill="#82ca9d"
                  fillOpacity={0.3}
                  name="实际"
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>类目利润排行</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={categoryProfit}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Legend />
                <Bar dataKey="margin" fill="#8884d8" name="利润率 %" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
