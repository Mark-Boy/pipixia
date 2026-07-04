"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { mockRiskLogs } from "@/lib/mock-data";
import { ShieldAlert, Filter, Upload } from "lucide-react";

export function RiskPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">风控日志</h1>
          <p className="text-muted-foreground">
            查看拦截记录与管理敏感词库
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline">
            <Filter className="mr-2 h-4 w-4" />
            筛选
          </Button>
          <Button variant="outline">
            <Upload className="mr-2 h-4 w-4" />
            上传词库
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">今日拦截</p>
            <p className="text-2xl font-bold text-red-600">5</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">累计拦截</p>
            <p className="text-2xl font-bold">128</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">拦截率</p>
            <p className="text-2xl font-bold">3.8%</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-red-500" />
            拦截记录
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {mockRiskLogs.map((log) => (
              <div
                key={log.id}
                className="flex items-center justify-between rounded-lg border p-4"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{log.productTitle}</span>
                    <Badge
                      variant="outline"
                      className={
                        log.riskType === "brand"
                          ? "border-red-200 bg-red-50 text-red-700"
                          : log.riskType === "profit"
                          ? "border-amber-200 bg-amber-50 text-amber-700"
                          : "border-blue-200 bg-blue-50 text-blue-700"
                      }
                    >
                      {log.riskType === "brand"
                        ? "品牌侵权"
                        : log.riskType === "profit"
                        ? "利润不足"
                        : "类目错放"}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">
                    {log.riskDetail}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    操作: {log.actionTaken}
                  </p>
                </div>
                <span className="text-xs text-muted-foreground ml-4">
                  {new Date(log.createdAt).toLocaleString("zh-CN")}
                </span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
