"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  mockFinancialMetrics,
  mockProducts,
  mockAudits,
  mockRiskLogs,
} from "@/lib/mock-data";
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

// Mock chart data
const weeklyData = [
  { day: "周一", imported: 45, listed: 38, failed: 7 },
  { day: "周二", imported: 52, listed: 44, failed: 8 },
  { day: "周三", imported: 38, listed: 35, failed: 3 },
  { day: "周四", imported: 67, listed: 55, failed: 12 },
  { day: "周五", imported: 58, listed: 50, failed: 8 },
  { day: "周六", imported: 23, listed: 20, failed: 3 },
  { day: "周日", imported: 15, listed: 12, failed: 3 },
];

const profitData = [
  { name: "手机配件", margin: 28.5, volume: 156 },
  { name: "数码周边", margin: 22.1, volume: 98 },
  { name: "家居用品", margin: 18.7, volume: 67 },
  { name: "服装配饰", margin: 15.2, volume: 45 },
  { name: "运动户外", margin: 24.8, volume: 32 },
];

export function OverviewPage() {
  const pendingAudits = mockAudits.filter((a) => a.status === "pending").length;
  const blockedProducts = mockProducts.filter(
    (p) => p.status === "blocked"
  ).length;
  const todayListed = mockProducts.filter((p) => p.status === "listed").length;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">数据看板</h1>
        <p className="text-muted-foreground">
          实时监控商品上架、审核、财务与风控数据
        </p>
      </div>

      {/* Key Metrics Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">今日上架</CardTitle>
            <Package className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{todayListed}</div>
            <p className="text-xs text-muted-foreground">
              <span className="text-green-600 font-medium">↑ 12%</span>{" "}
              较昨日
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
              {mockFinancialMetrics.totalSales.toLocaleString()} ฿
            </div>
            <p className="text-xs text-muted-foreground">
              <TrendingUp className="inline h-3 w-3 text-green-600" /> 本月累计
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
              {mockFinancialMetrics.avgProfitMargin}%
            </div>
            <Progress
              value={mockFinancialMetrics.avgProfitMargin}
              className="mt-2"
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
              今日拦截数
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
            <CardTitle>类目利润排行</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={profitData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis />
                <Tooltip />
                <Bar
                  dataKey="margin"
                  fill="#8884d8"
                  name="利润率 %"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
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
            <div className="flex items-center justify-between rounded-lg border-l-4 border-amber-500 bg-amber-50 p-3 dark:bg-amber-950/20">
              <div>
                <p className="text-sm font-medium">汇率波动告警</p>
                <p className="text-xs text-muted-foreground">
                  CNY→THB 波动 2.3%，已暂停自动上架
                </p>
              </div>
              <Badge variant="secondary" className="bg-amber-100 text-amber-800">
                P0
              </Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border-l-4 border-blue-500 bg-blue-50 p-3 dark:bg-blue-950/20">
              <div>
                <p className="text-sm font-medium">待审核商品</p>
                <p className="text-xs text-muted-foreground">
                  有 {pendingAudits} 件商品等待人工审核
                </p>
              </div>
              <Badge variant="outline">{pendingAudits}</Badge>
            </div>

            <div className="flex items-center justify-between rounded-lg border-l-4 border-red-500 bg-red-50 p-3 dark:bg-red-950/20">
              <div>
                <p className="text-sm font-medium">风控拦截</p>
                <p className="text-xs text-muted-foreground">
                  今日 {mockRiskLogs.length} 条拦截记录
                </p>
              </div>
              <Badge variant="destructive">{mockRiskLogs.length}</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Recent Products */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              最近商品
              <Badge variant="outline" className="text-xs">
                共 {mockProducts.length} 条
              </Badge>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {mockProducts.slice(0, 4).map((product) => (
                <div
                  key={product.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex-1">
                    <p className="text-sm font-medium">{product.titleZh}</p>
                    <p className="text-xs text-muted-foreground">
                      {product.sourcePlatform === "1688" ? "1688" : "拼多多"} ·{" "}
                      利润率 {product.profitMargin}%
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    {product.status === "listed" && (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        <CheckCircle className="mr-1 h-3 w-3" />
                        已上架
                      </Badge>
                    )}
                    {product.status === "auditing" && (
                      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                        <Clock className="mr-1 h-3 w-3" />
                        审核中
                      </Badge>
                    )}
                    {product.status === "blocked" && (
                      <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                        <XCircle className="mr-1 h-3 w-3" />
                        拦截
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
