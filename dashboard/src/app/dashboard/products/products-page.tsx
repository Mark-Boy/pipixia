"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
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
  mockProducts,
} from "@/lib/mock-data";
import {
  Search,
  Plus,
  Filter,
  Download,
  Eye,
  Edit,
  Trash2,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export function ProductsPage() {
  const [search, setSearch] = useState("");
  const [platform, setPlatform] = useState("all");
  const [status, setStatus] = useState("all");

  const filteredProducts = mockProducts.filter((p) => {
    const matchSearch =
      !search ||
      p.titleZh.toLowerCase().includes(search.toLowerCase()) ||
      p.titleTh.toLowerCase().includes(search.toLowerCase());
    const matchPlatform =
      platform === "all" || p.sourcePlatform === platform;
    const matchStatus = status === "all" || p.status === status;
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
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              导入商品
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem>📋 粘贴 1688 链接</DropdownMenuItem>
            <DropdownMenuItem>📋 粘贴 拼多多 链接</DropdownMenuItem>
            <DropdownMenuItem>📁 CSV 批量导入</DropdownMenuItem>
            <DropdownMenuItem>🔗 Shopee 热销品采集</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

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
              {filteredProducts.filter((p) => p.status === "listed").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">审核中</p>
            <p className="text-2xl font-bold text-blue-600">
              {filteredProducts.filter((p) => p.status === "auditing").length}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">已拦截</p>
            <p className="text-2xl font-bold text-red-600">
              {filteredProducts.filter((p) => p.status === "blocked").length}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Product Table */}
      <Card>
        <CardHeader>
          <CardTitle>商品列表</CardTitle>
        </CardHeader>
        <CardContent>
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
                  <TableCell className="font-medium">{product.titleZh}</TableCell>
                  <TableCell>
                    <Badge variant="outline">
                      {product.sourcePlatform === "1688" ? "1688" : "拼多多"}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {product.status === "listed" && (
                      <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                        已上架
                      </Badge>
                    )}
                    {product.status === "auditing" && (
                      <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                        审核中
                      </Badge>
                    )}
                    {product.status === "blocked" && (
                      <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200">
                        已拦截
                      </Badge>
                    )}
                    {product.status === "pending" && (
                      <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                        待处理
                      </Badge>
                    )}
                  </TableCell>
                  <TableCell>
                    <span
                      className={
                        product.profitMargin >= 15
                          ? "text-green-600 font-medium"
                          : "text-red-600 font-medium"
                      }
                    >
                      {product.profitMargin}%
                    </span>
                  </TableCell>
                  <TableCell className="max-w-[200px] truncate text-muted-foreground">
                    {product.titleTh}
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
        </CardContent>
      </Card>
    </div>
  );
}
