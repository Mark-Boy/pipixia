"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Separator } from "@/components/ui/separator";
import { mockAudits } from "@/lib/mock-data";
import { CheckCircle, XCircle, Edit, Eye, MessageSquare } from "lucide-react";

export function AuditPage() {
  const [mode, setMode] = useState<"manual" | "auto">("manual");
  const [comment, setComment] = useState("");

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
            variant={mode === "manual" ? "default" : "outline"}
            onClick={() => setMode("manual")}
          >
            人工审核
          </Button>
          <Button
            variant={mode === "auto" ? "default" : "outline"}
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
            <p className="text-2xl font-bold text-amber-600">
              {mockAudits.length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已通过</p>
            <p className="text-2xl font-bold text-green-600">128</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已拒绝</p>
            <p className="text-2xl font-bold text-red-600">3</p>
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

      {/* Audit Queue */}
      <div className="space-y-4">
        {mockAudits.map((audit) => (
          <Card key={audit.id} className="overflow-hidden">
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
              <div className="mt-4">
                <p className="text-sm font-medium mb-2">描述翻译</p>
                <p className="text-sm text-muted-foreground">
                  {audit.descriptionTh}
                </p>
              </div>
              {audit.riskFlag && (
                <div className="mt-3 flex items-center gap-2 text-sm text-red-600">
                  <XCircle className="h-4 w-4" />
                  {audit.riskReason}
                </div>
              )}
              <div className="mt-4 flex gap-2">
                <Button size="sm" className="bg-green-600 hover:bg-green-700">
                  <CheckCircle className="mr-2 h-4 w-4" />
                  通过
                </Button>
                <Button size="sm" variant="outline" className="text-red-600 hover:text-red-700 hover:bg-red-50">
                  <XCircle className="mr-2 h-4 w-4" />
                  拒绝
                </Button>
                <Button size="sm" variant="outline">
                  <MessageSquare className="mr-2 h-4 w-4" />
                  编辑
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
      </div>
    </div>
  );
}
