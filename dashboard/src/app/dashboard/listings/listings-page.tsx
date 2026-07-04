"use client";

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
import { RefreshCw, CheckCircle, XCircle, Clock } from "lucide-react";

export function ListingsPage() {
  const mockListings = [
    { id: "1", product: "透明手机壳", status: "success", shopeeId: "SP001", retry: 0 },
    { id: "2", product: "数据线", status: "running", shopeeId: "-", retry: 1 },
    { id: "3", product: "蓝牙耳机", status: "failed", shopeeId: "-", retry: 5 },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">上架记录</h1>
        <p className="text-muted-foreground">
          查看商品上架历史记录与重试状态
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>上架记录</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>商品</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>Shopee ID</TableHead>
                <TableHead>重试次数</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {mockListings.map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="font-medium">{item.product}</TableCell>
                  <TableCell>
                    {item.status === "success" && (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        <CheckCircle className="mr-1 h-3 w-3" />
                        成功
                      </Badge>
                    )}
                    {item.status === "running" && (
                      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                        <Clock className="mr-1 h-3 w-3" />
                        进行中
                      </Badge>
                    )}
                    {item.status === "failed" && (
                      <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                        <XCircle className="mr-1 h-3 w-3" />
                        失败
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>{item.shopeeId}</TableCell>
                  <TableCell>{item.retry}</TableCell>
                  <TableCell>
                    {item.status === "failed" && (
                      <Button variant="ghost" size="sm">
                        <RefreshCw className="mr-2 h-4 w-4" />
                        重试
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
