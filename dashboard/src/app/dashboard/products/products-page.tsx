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
  DialogDescription,
} from "@/components/ui/dialog";
import { toast } from "sonner";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  Plus,
  Filter,
  Download,
  Eye,
  Edit,
  Trash2,
  Loader2,
  RefreshCw,
  Package,
  ExternalLink,
  Store as StoreIcon,
  Link as LinkIcon,
  Sparkles,
  AlertTriangle,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { productService, shopService } from "@/services";
import { Skeleton } from "@/components/ui/skeleton";

export function ProductsPage() {
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("all");
  const [status, setStatus] = useState("all");
  const [products, setProducts] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [shops, setShops] = useState<Record<string, unknown>[]>([]);
  const [shopsLoading, setShopsLoading] = useState(false);
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [importLoading, setImportLoading] = useState(false);

  const fetchProducts = async (showLoading = true) => {
    if (showLoading) setLoading(true);
    setError(null);
    try {
      const params: Record<string, any> = { page: 1, size: 50 };
      if (platform !== "all") params.source_platform = platform;
      if (status !== "all") params.status = status;
      
      const res = await productService.getList(params);
      setProducts((res as any)?.products || []);
    } catch (err: any) {
      const msg = err?.message || "未知错误";
      if (!(msg.includes("Network") || msg.includes("timeout"))) {
        setError("无法连接后端 API，请确认服务已启动");
      }
      setProducts([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchProducts(false);
  };

  const fetchShops = async () => {
    setShopsLoading(true);
    try {
      const res = await shopService.getList({ page: 1, size: 50 });
      setShops((res as any)?.shops || (res as any)?.items || []);
    } catch (err: any) {
      console.error("Failed to fetch shops:", err);
    } finally {
      setShopsLoading(false);
    }
  };

  const [importForm, setImportForm] = useState({
    url: "",
    shopId: "",
  });

  const handleImportByUrl = async () => {
    if (!importForm.url.trim()) {
      toast.error("请输入商品链接");
      return;
    }
    if (!importForm.shopId) {
      toast.error("请选择目标店铺");
      return;
    }
    setImportLoading(true);
    try {
      const res = await productService.importByUrl(importForm.url, parseInt(importForm.shopId));
      toast.success("商品导入成功");
      setImportDialogOpen(false);
      setImportForm({ url: "", shopId: "" });
      fetchProducts(false);
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || "导入失败，请检查网络连接");
    } finally {
      setImportLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
    fetchShops();
  }, []);

  const filteredProducts = products.filter((p) => {
    const titleZh = p.title_zh || p.titleZh || "";
    const titleTh = p.title_th || p.titleTh || "";
    const matchSearch =
      !search ||
      titleZh.toLowerCase().includes(search.toLowerCase()) ||
      titleTh.toLowerCase().includes(search.toLowerCase());
    const matchPlatform =
      platform === "all" || (p.source_platform || p.sourcePlatform) === platform;
    const matchStatus =
      status === "all" || p.status === status;
    return matchSearch && matchPlatform && matchStatus;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">商品管理</h1>
          <p className="text-muted-foreground">
            管理从 1688/拼多多 采集的商品，查看翻译、财务与风控状态
          </p>
        </div>
        <div className="flex gap-2">
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button>
                <Plus className="mr-2 h-4 w-4" />
                导入商品
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              <DropdownMenuItem onClick={() => setImportDialogOpen(true)}>
                <LinkIcon className="mr-2 h-4 w-4" />
                粘贴 1688/拼多多 链接
              </DropdownMenuItem>
              <DropdownMenuItem>📁 CSV 批量导入</DropdownMenuItem>
              <DropdownMenuItem>🔗 Shopee 热销品采集</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Import Dialog */}
          <Dialog open={importDialogOpen} onOpenChange={setImportDialogOpen}>
            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5 text-primary" />
                  导入商品
                </DialogTitle>
                <DialogDescription>
                  粘贴商品链接并选择目标店铺，系统将自动抓取商品信息
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                {/* Shop Selection */}
                <div className="space-y-2">
                  <Label htmlFor="shopId">选择店铺</Label>
                  {shopsLoading ? (
                    <div className="flex items-center gap-2 text-sm text-muted-foreground">
                      <Loader2 className="h-4 w-4 animate-spin" />
                      加载中...
                    </div>
                  ) : shops.length === 0 ? (
                    <div className="text-sm text-muted-foreground p-3 border rounded-md bg-muted/50">
                      <StoreIcon className="h-4 w-4 inline-block mr-2" />
                      暂无可用店铺
                    </div>
                  ) : (
                    <Select value={importForm.shopId} onValueChange={(v) => setImportForm({ ...importForm, shopId: v })}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择目标店铺" />
                      </SelectTrigger>
                      <SelectContent>
                        {shops.map((shop: any) => (
                          <SelectItem key={shop.id} value={String(shop.id)}>
                            {shop.shop_name || shop.name || `店铺 #${shop.id}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  )}
                </div>
                {/* URL Input */}
                <div className="space-y-2">
                  <Label htmlFor="productUrl">商品链接</Label>
                  <Input
                    id="productUrl"
                    placeholder="粘贴 1688 或拼多多商品链接"
                    value={importForm.url}
                    onChange={(e) => setImportForm({ ...importForm, url: e.target.value })}
                    disabled={importLoading || shops.length === 0}
                  />
                  <p className="text-xs text-muted-foreground">
                    支持 1688、拼多多商品详情页链接
                  </p>
                </div>
                {/* Submit */}
                <Button
                  onClick={handleImportByUrl}
                  disabled={importLoading || !importForm.url.trim() || !importForm.shopId || shops.length === 0}
                  className="w-full"
                >
                  {importLoading ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      正在导入...
                    </>
                  ) : (
                    <>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      开始导入
                    </>
                  )}
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
            <Button variant="outline" size="sm" onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
              重试
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-wrap gap-4">
            <div className="relative flex-1 min-w-[200px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="搜索商品标题..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
              />
            </div>
            <Select value={platform} onValueChange={setPlatform}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="平台" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部平台</SelectItem>
                <SelectItem value="1688">1688</SelectItem>
                <SelectItem value="pdd">拼多多</SelectItem>
              </SelectContent>
            </Select>
            <Select value={status} onValueChange={setStatus}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="状态" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">全部状态</SelectItem>
                <SelectItem value="listed">已上架</SelectItem>
                <SelectItem value="auditing">审核中</SelectItem>
                <SelectItem value="pending">待处理</SelectItem>
                <SelectItem value="blocked">已拦截</SelectItem>
              </SelectContent>
            </Select>
            <Button variant="outline">
              <Filter className="mr-2 h-4 w-4" />
              更多筛选
            </Button>
            <Button variant="outline">
              <Download className="mr-2 h-4 w-4" />
              导出
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Summary */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">总计</p>
            <p className="text-2xl font-bold">{filteredProducts.length}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已上架</p>
            <p className="text-2xl font-bold text-green-600">
              {filteredProducts.filter((p: any) => p.status === "listed" || p.status === "active").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">审核中</p>
            <p className="text-2xl font-bold text-blue-600">
              {filteredProducts.filter((p: any) => p.status === "auditing" || p.status === "pending").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已拦截</p>
            <p className="text-2xl font-bold text-red-600">
              {filteredProducts.filter((p: any) => p.status === "blocked" || p.risk_status === "block").length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <span className="ml-3 text-muted-foreground">加载中...</span>
        </div>
      )}

      {/* Product Table */}
      {!loading && (
        <Card>
          <CardHeader>
            <CardTitle>商品列表</CardTitle>
          </CardHeader>
          <CardContent>
            {filteredProducts.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 text-center">
                <Package className="h-12 w-12 text-muted-foreground mb-4" />
                <p className="text-lg font-medium">暂无商品</p>
                <p className="text-sm text-muted-foreground">
                  请先导入商品或创建商品记录
                </p>
              </div>
            ) : (
              <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12">
                    <Checkbox />
                  </TableHead>
                  <TableHead>商品标题</TableHead>
                  <TableHead>来源</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>利润率</TableHead>
                  <TableHead>泰语标题</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredProducts.map((product) => (
                  <TableRow key={product.id}>
                    <TableCell>
                      <Checkbox />
                    </TableCell>
                    <TableCell className="font-medium">
                      {product.title_zh || product.titleZh}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">
                        {(product.source_platform || product.sourcePlatform) === "1688" ? "1688" : "拼多多"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {product.status === "listed" || product.status === "active" ? (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          已上架
                        </Badge>
                      ) : product.status === "auditing" ? (
                        <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                          审核中
                        </Badge>
                      ) : product.status === "blocked" || product.risk_status === "block" ? (
                        <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                          已拦截
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                          待处理
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      <span
                        className={
                          (product.profit_margin || product.profitMargin) >= 15
                            ? "text-green-600 font-medium"
                            : "text-red-600 font-medium"
                        }
                      >
                        {product.profit_margin || product.profitMargin}%
                      </span>
                    </TableCell>
                    <TableCell className="max-w-[200px] truncate text-muted-foreground">
                      {product.title_th || product.titleTh || "-"}
                    </TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8">
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-8 w-8 text-red-500">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
