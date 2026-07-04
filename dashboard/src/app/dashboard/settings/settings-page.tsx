"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Save } from "lucide-react";

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">系统设置</h1>
        <p className="text-muted-foreground">
          配置熔断阈值、汇率、定时任务与通知
        </p>
      </div>

      <Tabs defaultValue="circuit">
        <TabsList>
          <TabsTrigger value="circuit">熔断设置</TabsTrigger>
          <TabsTrigger value="exchange">汇率配置</TabsTrigger>
          <TabsTrigger value="schedule">定时任务</TabsTrigger>
          <TabsTrigger value="notify">通知设置</TabsTrigger>
        </TabsList>

        <TabsContent value="circuit" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>利润熔断</CardTitle>
              <CardDescription>
                低于设定的利润率阈值时自动拦截商品上架
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label>最低预估利润率 (%)</Label>
                <Input type="number" defaultValue="15" />
              </div>
              <div className="grid gap-2">
                <Label>最小翻译置信度 (%)</Label>
                <Input type="number" defaultValue="85" />
              </div>
              <div className="grid gap-2">
                <Label>价格偏离阈值 (%)</Label>
                <Input type="number" defaultValue="30" />
              </div>
              <div className="flex items-center justify-between">
                <Label>启用自动熔断</Label>
                <Switch defaultChecked />
              </div>
              <Button>
                <Save className="mr-2 h-4 w-4" />
                保存设置
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="exchange" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>汇率管理</CardTitle>
              <CardDescription>
                CNY → THB 汇率每日自动更新
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label>当前汇率 (CNY→THB)</Label>
                <Input type="number" defaultValue="4.95" />
              </div>
              <div className="grid gap-2">
                <Label>波动告警阈值 (%)</Label>
                <Input type="number" defaultValue="2" />
              </div>
              <div className="flex items-center justify-between">
                <Label>启用汇率告警</Label>
                <Switch defaultChecked />
              </div>
              <Button>
                <Save className="mr-2 h-4 w-4" />
                保存设置
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="schedule" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>定时任务</CardTitle>
              <CardDescription>
                配置自动同步、扫描与报表生成时间
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {[
                { name: "库存同步", cron: "06:00", enabled: true },
                { name: "销量排行扫描", cron: "08:00", enabled: true },
                { name: "搜索趋势更新", cron: "10:00", enabled: true },
                { name: "竞品检查", cron: "12:00", enabled: true },
                { name: "日结对账", cron: "00:00", enabled: true },
                { name: "日报推送", cron: "23:00", enabled: true },
              ].map((task) => (
                <div key={task.name} className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium">{task.name}</p>
                    <p className="text-xs text-muted-foreground">
                      Cron: {task.cron}
                    </p>
                  </div>
                  <Switch defaultChecked={task.enabled} />
                </div>
              ))}
              <Button>
                <Save className="mr-2 h-4 w-4" />
                保存设置
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="notify" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>通知设置</CardTitle>
              <CardDescription>
                配置告警通知渠道
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <Label>Telegram 通知</Label>
                  <p className="text-xs text-muted-foreground">P0/P1 级别告警推送</p>
                </div>
                <Switch defaultChecked />
              </div>
              <div className="grid gap-2">
                <Label>Telegram Bot Token</Label>
                <Input type="password" defaultValue="123456:ABC-DEF..." />
              </div>
              <div className="grid gap-2">
                <Label>Telegram Chat ID</Label>
                <Input defaultValue="@pipixia_alerts" />
              </div>
              <Separator />
              <div className="flex items-center justify-between">
                <div>
                  <Label>邮件通知</Label>
                  <p className="text-xs text-muted-foreground">P0 级别告警 + 日报</p>
                </div>
                <Switch />
              </div>
              <Button>
                <Save className="mr-2 h-4 w-4" />
                保存设置
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
