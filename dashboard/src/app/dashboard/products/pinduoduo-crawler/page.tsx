"use client";

import { useState, useEffect, useRef } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";
import {
  Search,
  ExternalLink,
  Download,
  Loader2,
  ShoppingBag,
  Store,
  Globe,
  ArrowLeft,
  Sparkles,
  Check,
  Tag,
  Package,
  AlertTriangle,
  X,
  Link as LinkIcon,
} from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { productService, shopService } from "@/services";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

interface PddProduct {
  item_id: string;
  title_zh: string;
  price_cny: number;
  min_price_cny: number;
  sales: number;
  images: string[];
  shop_name: string;
  item_url: string;
  source_platform: string;
  raw_url: string;
}

interface CrawlResult {
  item_id: string;
  title_zh: string;
  price_cny: number;
  status: "pending" | "success" | "failed";
  message?: string;
  product_id?: number;
}

export default function PinduoduoCrawlerPage() {
  const router = useRouter();
  const [shops, setShops] = useState<any[]>([]);
  const [selectedShopId, setSelectedShopId] = useState("");
  const [shopsLoading, setShopsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchResults, setSearchResults] = useState<PddProduct[]>([]);
  const [crawling, setCrawling] = useState(false);
  const [crawlResults, setCrawlResults] = useState<CrawlResult[]>([]);
  const [selectedProducts, setSelectedProducts] = useState<Set<string>>(new Set());
  const [importing, setImporting] = useState(false);
  const [importResults, setImportResults] = useState<any[]>([]);
  const [importUrl, setImportUrl] = useState("");
  const [browserDialogOpen, setBrowserDialogOpen] = useState(false);
  const [browserUrl, setBrowserUrl] = useState(
    "https://mobile.yangkeduo.com/search.html?search_key=%E6%89%8B%E6%9C%BA"
  );
  const [currentBrowsingGoodsId, setCurrentBrowsingGoodsId] = useState("");
  const [iframeLoading, setIframeLoading] = useState(false);
  const [collecting, setCollecting] = useState(false);
  const [collectResult, setCollectResult] = useState<{ success: boolean; title: string; price?: number } | null>(null);
  const iframeRef = useRef<HTMLIFrameElement>(null);

  useEffect(() => {
    fetchShops();
  }, []);

  const fetchShops = async () => {
    setShopsLoading(true);
    try {
      const res = await shopService.getList({ page: 1, size: 50 });
      const shopList = (res as any)?.shops || (res as any)?.items || [];
      setShops(shopList);
      if (shopList.length > 0) {
        setSelectedShopId(String(shopList[0].id));
      }
    } catch (err) {
      console.error("Failed to fetch shops:", err);
      toast.error("加载店铺列表失败");
    } finally {
      setShopsLoading(false);
    }
  };

  const parsePddPrice = (price: number | string | undefined): number => {
    if (price === undefined || price === null) return 0;
    const num = typeof price === "string" ? parseFloat(price) : price;
    // 拼多多价格为分，需要除以100转为元
    return num > 1000 ? num / 100 : num;
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      toast.error("请输入搜索关键词");
      return;
    }
    setSearchLoading(true);
    try {
      const keyword = encodeURIComponent(searchQuery);
      const response = await fetch(
        `https://mobile.yangkeduo.com/proxy/apis/v5/search/search?keyword=${keyword}&page=1&page_size=20`,
        {
          headers: {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
            "Referer": "https://mobile.yangkeduo.com/",
          },
        }
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}: 搜索请求失败`);

      const text = await response.text();
      // 拼多多的搜索API返回的是嵌入在HTML中的JSON数据
      // 尝试从 text 中解析 searchSSRData
      let items: any[] = [];

      try {
        // 尝试直接解析 JSON（可能是纯 JSON 响应）
        const data = JSON.parse(text);
        items = data.searchSSRData?.goods || data.result?.items || data.goods || [];
      } catch {
        // 如果是 HTML 页面，提取 __INITIAL_STATE__ 或 searchSSRData
        const match = text.match(/searchSSRData[^;]*/);
        if (match) {
          const jsonStr = match[0].replace(/;\s*$/, "").trim();
          const parsed = JSON.parse(jsonStr);
          items = parsed.searchSSRData?.goods || parsed.goods || [];
        }
      }

      if (!items || items.length === 0) {
        toast.info("未找到相关商品，请尝试其他关键词");
        setSearchResults([]);
        setSearchLoading(false);
        return;
      }

      const results: PddProduct[] = items.map((item: any) => {
        const goodsId = String(item.goods_id || item.item_id || "");
        const groupPrice = item.group?.price || 0;
        const normalPrice = item.normal_price || 0;
        const price = groupPrice > 0 ? groupPrice : normalPrice;

        return {
          item_id: goodsId,
          title_zh: item.goods_name || item.item_name || item.title || "",
          price_cny: parsePddPrice(price),
          min_price_cny: parsePddPrice(item.min_group_price || item.min_normal_price || price),
          sales: item.cnt || item.sales_hint || 0,
          images: [item.thumb_url, item.hd_url].filter(Boolean),
          shop_name: "",
          item_url: `https://mobile.yangkeduo.com/goods.html?goods_id=${goodsId}`,
          source_platform: "pdd",
          raw_url: `https://mobile.yangkeduo.com/proxy/apis/v5/item/detail?item_id=${goodsId}`,
        };
      });

      setSearchResults(results);
    } catch (err: any) {
      toast.error(err.message || "搜索失败，请稍后重试");
      setSearchResults([]);
    } finally {
      setSearchLoading(false);
    }
  };

  // 从 URL 中提取商品 ID
  const extractGoodsId = (url: string): string => {
    const match = url.match(/[?&]goods_id=(\d+)/);
    return match ? match[1] : "";
  };

  const openPinduoduoBrowser = (searchKeyword?: string, goodsId?: string) => {
    let url: string;
    if (goodsId) {
      // 直接跳转到商品详情页
      url = `https://mobile.yangkeduo.com/goods.html?goods_id=${goodsId}`;
      setCurrentBrowsingGoodsId(goodsId);
    } else if (searchKeyword) {
      // 搜索商品
      url = `https://mobile.yangkeduo.com/search.html?search_key=${encodeURIComponent(searchKeyword)}`;
      setCurrentBrowsingGoodsId("");
    } else {
      // 首页
      url = "https://mobile.yangkeduo.com";
      setCurrentBrowsingGoodsId("");
    }
    setBrowserUrl(url);
    setIframeLoading(true);
    setBrowserDialogOpen(true);
    setCollectResult(null);
  };

  // 采集当前浏览的商品
  const handleCollectCurrentItem = async () => {
    if (!currentBrowsingGoodsId) {
      toast.error("当前页面不是商品详情页，请进入商品页面后点击采集");
      return;
    }
    if (!selectedShopId) {
      toast.error("请先选择目标店铺");
      return;
    }

    setCollecting(true);
    setCollectResult(null);

    try {
      const detailUrl = `https://mobile.yangkeduo.com/proxy/apis/v5/item/info?item_id=${currentBrowsingGoodsId}`;
      const response = await fetch(detailUrl, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
          "Referer": "https://mobile.yangkeduo.com/",
        },
      });

      if (!response.ok) throw new Error("获取商品详情失败");

      const text = await response.text();
      let data: any;
      try {
        data = JSON.parse(text);
      } catch {
        const m = text.match(/window\.__INITIAL_STATE__\s*=\s*({.*?});\s*document/);
        if (m) {
          data = JSON.parse(m[1]);
        } else {
          throw new Error("无法解析商品详情");
        }
      }

      const item = data.item || data.goods_info || data.goods || {};
      const groupPrice = item.group?.price || 0;
      const price = groupPrice > 0 ? groupPrice : (item.normal_price || 0);

      const productData = {
        source_platform: "pdd",
        source_item_id: currentBrowsingGoodsId,
        raw_url: `https://mobile.yangkeduo.com/goods.html?goods_id=${currentBrowsingGoodsId}`,
        title_zh: item.goods_name || item.item_name || item.title || "",
        price_cny: parsePddPrice(price),
        shop_id: parseInt(selectedShopId),
        description_zh: item.desc || "",
        images: [item.thumb_url, item.hd_url].filter(Boolean),
      };

      const result = await productService.create(productData);

      setCollectResult({
        success: true,
        title: productData.title_zh,
        price: productData.price_cny,
      });

      toast.success(`商品采集成功！${productData.title_zh}`);

      // 3秒后自动关闭浏览器并跳转到商品列表
      setTimeout(() => {
        setBrowserDialogOpen(false);
        window.location.href = "/dashboard/products";
      }, 3000);
    } catch (err: any) {
      setCollectResult({ success: false, title: err.message });
      toast.error(err.message || "采集失败，请稍后重试");
    } finally {
      setCollecting(false);
    }
  };

  const handleImportByUrl = async () => {
    if (!importUrl.trim() || !selectedShopId) {
      toast.error(importUrl.trim() ? "请先选择目标店铺" : "请输入商品链接");
      return;
    }
    setImporting(true);
    try {
      // 从 URL 中提取 goods_id
      let goodsId = "";
      const match = importUrl.match(/[?&]goods_id=(\d+)/);
      if (match) {
        goodsId = match[1];
      } else {
        const pathMatch = importUrl.match(/goods\.html\?goods_id=(\d+)/);
        if (pathMatch) {
          goodsId = pathMatch[1];
        } else {
          toast.error("无法从链接中提取商品 ID，请检查链接格式");
          setImporting(false);
          return;
        }
      }

      const detailUrl = `https://mobile.yangkeduo.com/proxy/apis/v5/item/info?item_id=${goodsId}`;
      const response = await fetch(detailUrl, {
        headers: {
          "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
          "Referer": "https://mobile.yangkeduo.com/",
        },
      });

      if (!response.ok) throw new Error("获取商品详情失败");

      const text = await response.text();
      let data: any;
      try {
        data = JSON.parse(text);
      } catch {
        const m = text.match(/window\.__INITIAL_STATE__\s*=\s*({.*?});\s*document/);
        if (m) {
          data = JSON.parse(m[1]);
        } else {
          throw new Error("无法解析商品详情");
        }
      }

      const item = data.item || data.goods_info || data.goods || {};
      const groupPrice = item.group?.price || 0;
      const price = groupPrice > 0 ? groupPrice : (item.normal_price || 0);

      // 先创建商品记录
      const productData = {
        source_platform: "pdd",
        source_item_id: goodsId,
        raw_url: `https://mobile.yangkeduo.com/goods.html?goods_id=${goodsId}`,
        title_zh: item.goods_name || item.item_name || item.title || "",
        price_cny: parsePddPrice(price),
        shop_id: parseInt(selectedShopId),
        description_zh: item.desc || "",
        images: [item.thumb_url, item.hd_url].filter(Boolean),
      };

      const result = await productService.create(productData);
      setImportResults([
        {
          title_zh: productData.title_zh,
          status: "imported",
          product_id: (result as any)?.data?.product_id || (result as any)?.data?.id,
          price_cny: productData.price_cny,
        },
      ]);

      toast.success(`商品导入成功！`);
      setImportUrl("");

      // 刷新商品列表
      setTimeout(() => {
        window.location.href = "/dashboard/products";
      }, 1000);
    } catch (err: any) {
      toast.error(err.message || "导入失败，请稍后重试");
    } finally {
      setImporting(false);
    }
  };

  const handleCrawlSelected = async () => {
    if (selectedProducts.size === 0) {
      toast.error("请先选择要采集的商品");
      return;
    }
    setCrawling(true);
    const results: CrawlResult[] = [];
    for (const itemId of selectedProducts) {
      const product = searchResults.find(p => p.item_id === itemId);
      if (!product) continue;
      try {
        // 使用商品详情页 API
        const detailUrl = `https://mobile.yangkeduo.com/proxy/apis/v5/item/info?item_id=${itemId}`;
        const response = await fetch(detailUrl, {
          headers: {
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36",
            "Referer": "https://mobile.yangkeduo.com/",
          },
        });
        if (!response.ok) throw new Error("采集失败");

        const text = await response.text();
        let data: any;
        try {
          data = JSON.parse(text);
        } catch {
          // 尝试从 HTML 中提取 JSON
          const match = text.match(/window\.__INITIAL_STATE__\s*=\s*({.*?});\s*document/);
          if (match) {
            data = JSON.parse(match[1]);
          } else {
            throw new Error("无法解析商品详情");
          }
        }

        const item = data.item || data.goods_info || data.goods || {};
        const groupPrice = item.group?.price || 0;
        const price = groupPrice > 0 ? groupPrice : (item.normal_price || 0);

        results.push({
          item_id: itemId,
          title_zh: item.goods_name || item.item_name || item.title || product.title_zh,
          price_cny: parsePddPrice(price),
          status: "success",
          message: "采集成功",
        });
      } catch (err: any) {
        results.push({
          item_id: itemId,
          title_zh: product.title_zh,
          price_cny: product.price_cny,
          status: "failed",
          message: err.message,
        });
      }
    }
    setCrawlResults(results);
    setCrawling(false);
    const successCount = results.filter(r => r.status === "success").length;
    toast.success(`采集完成！成功 ${successCount}/${results.length} 个商品`);
  };

  const handleBatchImport = async () => {
    if (!selectedShopId) {
      toast.error("请选择目标店铺");
      return;
    }
    setImporting(true);
    const importPromises = crawlResults
      .filter(r => r.status === "success")
      .map(result => {
        const product = searchResults.find(p => p.item_id === result.item_id);
        if (!product) return Promise.resolve(null);
        return productService.importByUrl(product.raw_url, parseInt(selectedShopId))
          .then((res: any) => ({
            ...result,
            status: "imported",
            product_id: (res as any)?.data?.product_id,
          }))
          .catch((err: any) => ({
            ...result,
            status: "import_failed",
            message: err.response?.data?.detail || err.message,
          }));
      });
    const results = await Promise.all(importPromises);
    setImportResults(results);
    setImporting(false);
    const importedCount = results.filter(r => r?.status === "imported").length;
    toast.success(`导入完成！成功 ${importedCount} 个商品`);
    setTimeout(() => {
      router.push("/dashboard/products");
    }, 1500);
  };

  const toggleSelectProduct = (itemId: string) => {
    const newSelected = new Set(selectedProducts);
    if (newSelected.has(itemId)) {
      newSelected.delete(itemId);
    } else {
      newSelected.add(itemId);
    }
    setSelectedProducts(newSelected);
  };

  const selectAllProducts = () => {
    if (selectedProducts.size === searchResults.length) {
      setSelectedProducts(new Set());
    } else {
      setSelectedProducts(new Set(searchResults.map(p => p.item_id)));
    }
  };

  return (
    <div className="space-y-6">
      {/* 顶部导航 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => router.push("/dashboard/products")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
              <ShoppingBag className="h-6 w-6 text-red-500" />
              拼多多商品采集器
            </h1>
            <p className="text-muted-foreground">
              搜索、浏览并采集拼多多商品到 pipixia 管理平台
            </p>
          </div>
        </div>
        <Button variant="outline" onClick={() => openPinduoduoBrowser()} disabled={crawling || importing}>
          <Globe className="mr-2 h-4 w-4" />
          打开拼多多浏览器
        </Button>
      </div>

      {/* 店铺选择 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Store className="h-5 w-5 text-primary" />
            目标店铺
          </CardTitle>
        </CardHeader>
        <CardContent>
          {shopsLoading ? (
            <Skeleton className="h-10 w-full" />
          ) : (
            <div className="space-y-2">
              <Label>选择要导入到的店铺</Label>
              <Select value={selectedShopId} onValueChange={setSelectedShopId}>
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
              {!selectedShopId && (
                <p className="text-sm text-muted-foreground">
                  暂无可用店铺，请先在店铺管理中创建店铺
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 搜索框 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Search className="h-5 w-5 text-primary" />
            搜索商品
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="flex-1">
              <Input
                placeholder="输入关键词搜索拼多多商品..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              />
            </div>
            <Button
              onClick={handleSearch}
              disabled={searchLoading || !searchQuery.trim()}
              className="min-w-[120px]"
            >
              {searchLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Search className="mr-2 h-4 w-4" />
              )}
              搜索
            </Button>
            <Button
              variant="outline"
              onClick={() => openPinduoduoBrowser(searchQuery)}
              disabled={!searchQuery.trim()}
            >
              <ExternalLink className="mr-2 h-4 w-4" />
              浏览器搜索
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            支持搜索商品、品牌、类目关键词。搜索结果将在此页面展示。
          </p>
        </CardContent>
      </Card>

      {/* 搜索结果 */}

      {/* 粘贴链接导入 */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <LinkIcon className="h-5 w-5 text-green-500" />
            粘贴链接导入
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <Input
              placeholder="粘贴拼多多商品链接（例如：goods.html?goods_id=xxx）"
              value={importUrl}
              onChange={(e) => setImportUrl(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleImportByUrl()}
            />
            <div className="flex gap-2">
              <Button
                onClick={handleImportByUrl}
                disabled={!importUrl.trim() || importing}
              >
                {importing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    导入中...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    导入
                  </>
                )}
              </Button>
              <Button variant="outline" onClick={() => setImportUrl("")}>
                清空
              </Button>
            </div>
            {importUrl && (
              <p className="text-xs text-muted-foreground">
                支持格式: goods.html?goods_id=xxx 或完整链接
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {searchResults.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-yellow-500" />
              搜索结果 ({searchResults.length})
            </CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={selectAllProducts}>
                {selectedProducts.size === searchResults.length ? "取消全选" : "全选"}
              </Button>
              <Button
                onClick={handleCrawlSelected}
                disabled={selectedProducts.size === 0 || crawling}
              >
                {crawling ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    采集中...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    采集选中 ({selectedProducts.size})
                  </>
                )}
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {searchResults.map((product) => (
                <div
                  key={product.item_id}
                  className={`flex items-start gap-4 p-4 border rounded-lg transition-colors ${
                    selectedProducts.has(product.item_id)
                      ? "bg-blue-50 border-blue-200"
                      : "bg-white hover:bg-gray-50"
                  }`}
                >
                  <div className="pt-1">
                    <div
                      className={`w-5 h-5 border-2 rounded cursor-pointer flex items-center justify-center ${
                        selectedProducts.has(product.item_id)
                          ? "bg-blue-500 border-blue-500"
                          : "border-gray-300"
                      }`}
                      onClick={() => toggleSelectProduct(product.item_id)}
                    >
                      {selectedProducts.has(product.item_id) && (
                        <Check className="h-3 w-3 text-white" />
                      )}
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-medium text-sm line-clamp-2">{product.title_zh}</h3>
                        <div className="flex items-center gap-4 mt-2 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Tag className="h-3 w-3" />
                            ¥{product.price_cny.toFixed(2)}
                          </span>
                          <span>销量: {product.sales}</span>
                          <span className="flex items-center gap-1">
                            <ExternalLink className="h-3 w-3" />
                            <button
                              onClick={() => openPinduoduoBrowser(undefined, product.item_id)}
                              className="text-blue-500 hover:underline"
                            >
                              查看商品详情
                            </button>
                          </span>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => toggleSelectProduct(product.item_id)}
                      >
                        {selectedProducts.has(product.item_id) ? "已选" : "选择"}
                      </Button>
                    </div>
                    <div className="mt-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-xs h-7 px-2"
                        onClick={() => openPinduoduoBrowser(undefined, product.item_id)}
                      >
                        <Globe className="mr-1 h-3 w-3" />
                        在浏览器中查看
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 采集结果 */}
      {crawlResults.length > 0 && (
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Package className="h-5 w-5 text-primary" />
              采集结果 ({crawlResults.length})
            </CardTitle>
            <Button
              onClick={handleBatchImport}
              disabled={importing || crawlResults.filter(r => r.status === "success").length === 0}
            >
              {importing ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  导入中...
                </>
              ) : (
                <>
                  <Download className="mr-2 h-4 w-4" />
                  批量导入到店铺
                </>
              )}
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {crawlResults.map((result) => (
                <div key={result.item_id} className="flex items-center gap-3 p-3 rounded-lg border">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{result.title_zh}</p>
                    <p className="text-xs text-muted-foreground">¥{result.price_cny.toFixed(2)}</p>
                  </div>
                  <Badge variant={result.status === "success" ? "outline" : "destructive"}>
                    {result.status === "success" ? "采集成功" : "采集失败"}
                  </Badge>
                  {result.message && (
                    <p className="text-xs text-muted-foreground">{result.message}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 导入结果 */}
      {importResults.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Check className="h-5 w-5 text-green-500" />
              导入结果
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {importResults.map((result, idx) => (
                <div key={idx} className="flex items-center gap-3 p-3 rounded-lg border">
                  <div className="flex-1">
                    <p className="font-medium text-sm">{result.title_zh}</p>
                  </div>
                  {result.status === "imported" ? (
                    <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                      <Check className="mr-1 h-3 w-3" />
                      已导入
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                      <AlertTriangle className="mr-1 h-3 w-3" />
                      导入失败
                    </Badge>
                  )}
                  {result.message && (
                    <p className="text-xs text-muted-foreground">{result.message}</p>
                  )}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* 拼多多浏览器对话框 */}
      <Dialog open={browserDialogOpen} onOpenChange={setBrowserDialogOpen}>
        <DialogContent className="max-w-[95vw] max-h-[95vh] w-[1400px] h-[900px] p-0 flex flex-col">
          {/* 浏览器工具栏 */}
          <div className="border-b bg-muted/50 px-4 py-3 flex items-center gap-3">
            <div className="flex items-center gap-2 flex-1">
              <Globe className="h-5 w-5 text-red-500 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-foreground truncate">
                  拼多多商品浏览器
                  {currentBrowsingGoodsId && (
                    <Badge variant="outline" className="ml-2 bg-green-50 text-green-700 border-green-200">
                      <Check className="mr-1 h-3 w-3" />
                      商品详情页
                    </Badge>
                  )}
                </div>
                <div className="text-xs text-muted-foreground truncate mt-1 flex items-center gap-2">
                  <span className="truncate">{browserUrl}</span>
                  {currentBrowsingGoodsId && (
                    <>
                      <span className="shrink-0">|</span>
                      <span className="text-primary font-mono shrink-0">ID: {currentBrowsingGoodsId}</span>
                    </>
                  )}
                </div>
              </div>
            </div>

            {/* 采集按钮 */}
            {currentBrowsingGoodsId ? (
              <Button
                onClick={handleCollectCurrentItem}
                disabled={collecting}
                className="bg-green-600 hover:bg-green-700 text-white shadow-md"
              >
                {collecting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    采集中...
                  </>
                ) : (
                  <>
                    <Download className="mr-2 h-4 w-4" />
                    采集当前商品
                  </>
                )}
              </Button>
            ) : (
              <Button
                variant="outline"
                disabled
                className="text-muted-foreground"
              >
                <Download className="mr-2 h-4 w-4" />
                采集当前商品
              </Button>
            )}

            {/* 关闭按钮 */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setBrowserDialogOpen(false)}
              className="shrink-0"
            >
              <X className="h-4 w-4" />
              <span className="sr-only">关闭</span>
            </Button>
          </div>

          {/* 采集结果提示 */}
          {collectResult && (
            <div className={`px-6 py-3 border-b flex items-center gap-3 ${
              collectResult.success
                ? "bg-green-50 border-green-200"
                : "bg-red-50 border-red-200"
            }`}>
              {collectResult.success ? (
                <Check className="h-5 w-5 text-green-600 shrink-0" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-600 shrink-0" />
              )}
              <div className="flex-1 min-w-0">
                <p className={`font-medium text-sm ${
                  collectResult.success ? "text-green-700" : "text-red-700"
                }`}>
                  {collectResult.success ? "采集成功！" : "采集失败"}
                </p>
                <p className={`text-xs truncate ${
                  collectResult.success ? "text-green-600" : "text-red-600"
                }`}>
                  {collectResult.success
                    ? `${collectResult.title} (¥${collectResult.price?.toFixed(2)}) - 3秒后自动跳转到商品列表`
                    : collectResult.title}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className={`shrink-0 ${collectResult.success ? "text-green-700 hover:text-green-800" : "text-red-700 hover:text-red-800"}`}
                onClick={() => {
                  setCollectResult(null);
                  if (collectResult.success) {
                    setBrowserDialogOpen(false);
                    window.location.href = "/dashboard/products";
                  }
                }}
              >
                立即前往
              </Button>
            </div>
          )}

          {/* iframe 浏览器区域 */}
          <div className="flex-1 relative">
            {iframeLoading && (
              <div className="absolute inset-0 flex items-center justify-center bg-background">
                <div className="text-center">
                  <Loader2 className="h-12 w-12 animate-spin text-muted-foreground mx-auto" />
                  <p className="text-sm text-muted-foreground mt-4">正在加载拼多多...</p>
                </div>
              </div>
            )}
            <iframe
              src={browserUrl}
              className="w-full h-full border-0"
              sandbox="allow-same-origin allow-scripts allow-popups allow-forms allow-modals"
              title="拼多多浏览器"
              onLoad={() => {
                setIframeLoading(false);
                // 尝试从 iframe 获取当前 URL
                try {
                  const currentUrl = (iframeRef.current as HTMLIFrameElement)?.contentWindow?.location?.href || "";
                  if (currentUrl) {
                    const goodsId = extractGoodsId(currentUrl);
                    if (goodsId && goodsId !== currentBrowsingGoodsId) {
                      setCurrentBrowsingGoodsId(goodsId);
                      setBrowserUrl(currentUrl);
                    }
                  }
                } catch {
                  // Cross-origin, use the src URL
                }
              }}
              onError={() => {
                setIframeLoading(false);
                toast.error("拼多多页面加载失败，请检查网络");
              }}
              ref={(el) => {
                if (el) {
                  iframeRef.current = el;
                }
              }}
            />
            {/* 新窗口打开按钮 */}
            <a
              href={browserUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="absolute bottom-4 right-4 bg-background/90 backdrop-blur-sm text-foreground border border-border px-4 py-2 rounded-md text-sm shadow-md hover:bg-background transition-opacity"
            >
              <ExternalLink className="mr-2 h-4 w-4 inline" />
              新窗口打开
            </a>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
