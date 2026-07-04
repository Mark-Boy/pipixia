"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Store, Plus, TestTube, Settings } from "lucide-react";

export function ShopsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">店铺管理</h1>
          <p className="text-muted-foreground">
            管理 Shopee 店铺连接与 API 配置
          </p>
        </div>
        <Button>
          <Plus className="mr-2 h-4 w-4" />
          添加店铺
        </Button>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Store className="h-5 w-5" />
              泰国Shop_01
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">平台</span>
              <span>Shopee Thailand</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">状态</span>
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                ✅ 已连接
              </Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">商品数</span>
              <span>128</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">最后同步</span>
              <span>2分钟前</span>
            </div>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm">
                <TestTube className="mr-2 h-4 w-4" />
                测试连接
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="mr-2 h-4 w-4" />
                配置
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Store className="h-5 w-5" />
              泰国Shop_02
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">平台</span>
              <span>Shopee Thailand</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">状态</span>
              <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                ⚠️ Token即将过期
              </Badge>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">商品数</span>
              <span>56</span>
            </div>
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">最后同步</span>
              <span>1小时前</span>
            </div>
            <div className="flex gap-2 pt-2">
              <Button variant="outline" size="sm">
                <TestTube className="mr-2 h-4 w-4" />
                测试连接
              </Button>
              <Button variant="outline" size="sm">
                <Settings className="mr-2 h-4 w-4" />
                配置
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
