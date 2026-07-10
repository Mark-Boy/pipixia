"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Store,
  Plus,
  TestTube,
  Settings,
  Loader2,
  RefreshCw,
  Trash2,
  Eye,
  EyeOff,
  AlertTriangle,
} from "lucide-react";
import { shopService } from "@/services";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

interface Shop {
  id: number;
  user_id: number;
  shop_name: string;
  platform: string;
  is_active: boolean;
  config: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export function ShopsPage() {
  const [shops, setShops] = useState<Shop[]>([]);
  const [platforms, setPlatforms] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [showToken, setShowToken] = useState<Record<number, boolean>>({});
  const [formData, setFormData] = useState({
    shop_name: "",
    platform: "shopee_th",
    shop_token: "",
    config: "{}",
  });

  const fetchShops = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await shopService.getList({
        credentials_str: `Bearer ${token}`,
        page: 1,
        size: 50,
      });
      setShops(Array.isArray(res) ? res : ((res as any)?.shops || (res as any)?.items || []));
    } catch (err: any) {
      const msg = err?.message || "未知错误";
      if (!(msg.includes("Network") || msg.includes("timeout"))) {
        setError("无法加载店铺列表");
      }
      setShops([]);
    } finally {
      setLoading(false);
    }
  };

  const fetchPlatforms = async () => {
    try {
      const res = await shopService.getPlatforms();
      setPlatforms((res as any)?.platforms || []);
    } catch (err: any) {
      console.error("Failed to fetch platforms:", err);
      setPlatforms([
        { id: "shopee_th", name: "THB", market_id: 146 },
        { id: "shopee_vn", name: "VND", market_id: 1 },
        { id: "shopee_sg", name: "SGD", market_id: 2 },
        { id: "shopee_my", name: "MYR", market_id: 3 },
        { id: "shopee_id", name: "IDR", market_id: 12420 },
        { id: "shopee_ph", name: "PHP", market_id: 6 },
      ]);
    }
  };

  useEffect(() => {
    fetchShops();
    fetchPlatforms();
  }, []);

  const handleCreate = async () => {
    try {
      const token = localStorage.getItem("access_token");
      await shopService.create({
        ...formData,
        config: JSON.parse(formData.config || "{}"),
      });
      setDialogOpen(false);
      setFormData({ shop_name: "", platform: "shopee_th", shop_token: "", config: "{}" });
      fetchShops();
    } catch (err: any) {
      toast.error("创建店铺失败");
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm("确定要删除这个店铺吗？")) return;
    try {
      const token = localStorage.getItem("access_token");
      await shopService.delete(id);
      fetchShops();
    } catch (err: any) {
      toast.error("删除失败");
    }
  };

  const toggleTokenVisibility = (id: number) => {
    setShowToken((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">店铺管理</h1>
          <p className="text-muted-foreground">
            管理 Shopee 店铺连接与 API 配置
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchShops}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            刷新
          </Button>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                添加店铺
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>添加店铺</DialogTitle>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="shop_name">店铺名称</Label>
                  <Input
                    id="shop_name"
                    placeholder="我的泰国店"
                    value={formData.shop_name}
                    onChange={(e) => setFormData({ ...formData, shop_name: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="platform">平台</Label>
                  <select
                    id="platform"
                    className="w-full rounded-md border px-3 py-2"
                    value={formData.platform}
                    onChange={(e) => setFormData({ ...formData, platform: e.target.value })}
                  >
                    {platforms.map((p: any) => (
                      <option key={p.id} value={p.id}>
                        {p.name} - {p.id.replace("shopee_", "").toUpperCase()}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="shop_token">Shop Token</Label>
                  <Input
                    id="shop_token"
                    type="password"
                    placeholder="粘贴 Shopee OAuth Token"
                    value={formData.shop_token}
                    onChange={(e) => setFormData({ ...formData, shop_token: e.target.value })}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="config">配置（JSON）</Label>
                  <textarea
                    id="config"
                    className="w-full rounded-md border px-3 py-2 min-h-[80px]"
                    placeholder='{"shipping_template": "free", ...}'
                    value={formData.config}
                    onChange={(e) => setFormData({ ...formData, config: e.target.value })}
                  />
                </div>
                <Button onClick={handleCreate} className="w-full">
                  创建店铺
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </div>
            <p className="text-xs text-muted-foreground">
              请确保后端 API 服务正在运行（http://localhost:8000）
            </p>
            <Button variant="outline" size="sm" onClick={fetchShops}>
              <RefreshCw className="mr-2 h-4 w-4" />
              重试
            </Button>
          </CardContent>
        </Card>
      )}

      {loading && shops.length === 0 && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">加载中...</span>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {shops.map((shop) => (
          <Card key={shop.id}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Store className="h-5 w-5" />
                {shop.shop_name}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">平台</span>
                <span>{shop.platform === "shopee_th" ? "Shopee Thailand" : shop.platform}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">状态</span>
                <Badge variant="outline" className={shop.is_active ? "bg-green-50 text-green-700 border-green-200" : "bg-red-50 text-red-700 border-red-200"}>
                  {shop.is_active ? "✅ 已连接" : "❌ 已禁用"}
                </Badge>
              </div>
              <div className="flex justify-between text-sm items-center">
                <span className="text-muted-foreground">Token</span>
                <div className="flex items-center gap-1">
                  <span className="font-mono text-xs">
                    {showToken[shop.id] ? "eyJ..." : "••••••••"}
                  </span>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6"
                    onClick={() => toggleTokenVisibility(shop.id)}
                  >
                    {showToken[shop.id] ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
                  </Button>
                </div>
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
                <Button
                  variant="outline"
                  size="sm"
                  className="ml-auto text-red-500"
                  onClick={() => handleDelete(shop.id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}

        {/* Empty State */}
        {!loading && shops.length === 0 && !error && (
          <Card className="col-span-2">
            <CardContent className="flex flex-col items-center justify-center py-12 text-center">
              <Store className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">暂无店铺</p>
              <p className="text-sm text-muted-foreground">
                点击「添加店铺」按钮开始配置你的 Shopee 店铺
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
