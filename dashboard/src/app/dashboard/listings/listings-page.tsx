"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { RefreshCw, CheckCircle, XCircle, Clock, Loader2, AlertTriangle } from "lucide-react";
import { listingService } from "@/services";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

export function ListingsPage() {
  const [listings, setListings] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchListings = async () => {
    setLoading(true);
    setError(null);
    try {
      const token = localStorage.getItem("access_token");
      const res = await listingService.getList({
        credentials_str: `Bearer ${token}`,
        page: 1,
        size: 50,
      });
      setListings(Array.isArray(res) ? res : []);
    } catch (err: any) {
      const msg = err?.message || "未知错误";
      if (!(msg.includes("Network") || msg.includes("timeout"))) {
        setError("无法加载上架记录");
      }
      setListings([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchListings();
  }, []);

  const handleRetry = async (id: string) => {
    try {
      await listingService.retry(Number(id));
      fetchListings();
    } catch (err: any) {
      toast.error("重试失败");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">上架记录</h1>
          <p className="text-muted-foreground">
            查看商品上架历史记录与重试状态
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={fetchListings}>
          <RefreshCw className="mr-2 h-4 w-4" />
          刷新
        </Button>
      </div>

      {error && (
        <Card className="border-destructive">
          <CardContent className="pt-4 space-y-3">
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertTriangle className="h-4 w-4" />
              <span>{error}</span>
            </div>
            <Button variant="outline" size="sm" onClick={fetchListings}>
              <RefreshCw className="mr-2 h-4 w-4" />
              重试
            </Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="space-y-4">
          <Skeleton className="h-9 w-48" />
          <Card>
            <CardHeader><Skeleton className="h-5 w-32" /></CardHeader>
            <CardContent className="space-y-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex gap-4">
                  <Skeleton className="h-10 flex-1" />
                  <Skeleton className="h-10 w-20" />
                  <Skeleton className="h-10 w-16" />
                  <Skeleton className="h-10 w-16" />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle>上架记录 ({listings.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>商品 ID</TableHead>
                  <TableHead>Shopee ID</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>上架模式</TableHead>
                  <TableHead>重试次数</TableHead>
                  <TableHead>错误信息</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {listings.length > 0 ? (
                  listings.map((item) => (
                    <TableRow key={item.id}>
                      <TableCell className="font-medium">{item.product_id}</TableCell>
                      <TableCell>{item.shopee_item_id || "-"}</TableCell>
                      <TableCell>
                        {item.shopee_status === "success" && (
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                            <CheckCircle className="mr-1 h-3 w-3" />
                            成功
                          </Badge>
                        )}
                        {item.shopee_status === "running" || item.shopee_status === "pending" ? (
                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                            <Clock className="mr-1 h-3 w-3" />
                            进行中
                          </Badge>
                        ) : item.shopee_status === "failed" ? (
                          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                            <XCircle className="mr-1 h-3 w-3" />
                            失败
                          </Badge>
                        ) : (
                          <Badge variant="outline">
                            {item.shopee_status || "未知"}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>{item.listing_mode || "manual"}</TableCell>
                      <TableCell>{item.retry_count ?? 0}</TableCell>
                      <TableCell className="max-w-[200px] truncate text-muted-foreground">
                        {item.last_error || "-"}
                      </TableCell>
                      <TableCell>
                        {item.shopee_status === "failed" && (
                          <Button variant="ghost" size="sm" onClick={() => handleRetry(item.id)}>
                            <RefreshCw className="mr-2 h-4 w-4" />
                            重试
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))
                ) : (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                      暂无上架记录
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
