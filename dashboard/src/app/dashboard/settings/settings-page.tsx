"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Save, Loader2, RefreshCw, AlertTriangle, Globe } from "lucide-react";
import { settingService } from "@/services";
import { toast } from "sonner";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

export function SettingsPage() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [riskWords, setRiskWords] = useState<{ brand_keywords: string[]; prohibited_words: string[] }>({
    brand_keywords: [],
    prohibited_words: [],
  });
  const [newWord, setNewWord] = useState("");
  const [wordType, setWordType] = useState<"brand" | "prohibited">("brand");
  const [exchangeRate, setExchangeRate] = useState<number>(5.0);
  const [rateSource, setRateSource] = useState<string>("缓存");
  const [refreshingRate, setRefreshingRate] = useState(false);

  const fetchExchangeRate = async () => {
    try {
      const data = await settingService.getExchangeRate();
      setExchangeRate((data as any)?.rate || 5.0);
      setRateSource((data as any)?.cached ? "已缓存" : "实时");
    } catch (err: any) {
      console.error("Failed to fetch exchange rate:", err);
    }
  };

  const fetchRiskWords = async () => {
    setLoading(true);
    try {
      const data = await settingService.getRiskWords();
      setRiskWords(data as any);
    } catch (err: any) {
      console.error("Failed to fetch risk words:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRiskWords();
    fetchExchangeRate();
  }, []);

  if (loading) {
    return (
      <div className="space-y-6">
        <Skeleton className="h-8 w-40" />
        <Skeleton className="h-4 w-64" />
        <Skeleton className="h-10 w-96" />
        <div className="grid gap-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-[250px] w-full" />
          ))}
        </div>
      </div>
    );
  }

  const handleAddWord = async () => {
    if (!newWord.trim()) return;
    setSaving(true);
    try {
      await settingService.addRiskWord(newWord.trim(), wordType);
      setNewWord("");
      fetchRiskWords();
    } catch (err: unknown) {
      toast.error("添加失败");
    } finally {
      setSaving(false);
    }
  };

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
          <TabsTrigger value="risk">风控词库</TabsTrigger>
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
                CNY → THB 汇率每日自动更新，缓存 TTL 1 小时
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-2">
                <Label>当前汇率 (CNY→THB)</Label>
                <div className="flex items-center gap-2">
                  <Input
                    type="number"
                    value={exchangeRate.toFixed(4)}
                    readOnly
                    className="font-mono"
                  />
                  <Badge variant="outline" className="shrink-0">
                    {rateSource}
                  </Badge>
                  <Button
                    variant="outline"
                    size="icon"
                    onClick={async () => {
                      setRefreshingRate(true);
                      try {
                        await settingService.getExchangeRate(true);
                        fetchExchangeRate();
                        toast.success("汇率已刷新");
                      } catch (err: any) {
                        toast.error("刷新汇率失败");
                      } finally {
                        setRefreshingRate(false);
                      }
                    }}
                    disabled={refreshingRate}
                    title="强制刷新汇率"
                  >
                    {refreshingRate ? <Loader2 className="h-4 w-4 animate-spin" /> : <Globe className="h-4 w-4" />}
                  </Button>
                </div>
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

        <TabsContent value="risk" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>风控词库管理</CardTitle>
              <CardDescription>
                管理品牌词和违禁词，用于翻译后风控检测
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex gap-2">
                <select
                  className="rounded-md border px-3 py-2"
                  value={wordType}
                  onChange={(e) => setWordType(e.target.value as "brand" | "prohibited")}
                >
                  <option value="brand">品牌词</option>
                  <option value="prohibited">违禁词</option>
                </select>
                <Input
                  placeholder="输入新词汇..."
                  value={newWord}
                  onChange={(e) => setNewWord(e.target.value)}
                  className="flex-1"
                  onKeyDown={(e) => e.key === "Enter" && handleAddWord()}
                />
                <Button onClick={handleAddWord} disabled={saving || !newWord.trim()}>
                  {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                  添加
                </Button>
              </div>

              <Separator />

              <div>
                <h3 className="text-sm font-medium mb-2">品牌词 ({riskWords.brand_keywords.length})</h3>
                <div className="flex flex-wrap gap-2">
                  {riskWords.brand_keywords.map((word, i) => (
                    <Badge key={i} variant="outline" className="bg-red-50 text-red-700 border-red-200">
                      {word}
                    </Badge>
                  ))}
                  {riskWords.brand_keywords.length === 0 && (
                    <p className="text-sm text-muted-foreground">暂无品牌词</p>
                  )}
                </div>
              </div>

              <div>
                <h3 className="text-sm font-medium mb-2">违禁词 ({riskWords.prohibited_words.length})</h3>
                <div className="flex flex-wrap gap-2">
                  {riskWords.prohibited_words.map((word, i) => (
                    <Badge key={i} variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                      {word}
                    </Badge>
                  ))}
                  {riskWords.prohibited_words.length === 0 && (
                    <p className="text-sm text-muted-foreground">暂无违禁词</p>
                  )}
                </div>
              </div>

              <Button onClick={fetchRiskWords} variant="outline" className="w-full">
                <RefreshCw className="mr-2 h-4 w-4" />
                刷新词库
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
