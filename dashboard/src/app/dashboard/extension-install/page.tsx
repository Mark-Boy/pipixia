"use client";

/// <reference types="chrome" />

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {  
  Download,  
  CheckCircle,  
  AlertCircle,  
  Settings,
  Puzzle,
  ExternalLink,
  Copy,
  Loader2,
  ChevronDown,
  MousePointerClick,
  Shield,
  Zap,
  Mail,
  Package,
  ChevronRight,
  X,
  Monitor,
} from "lucide-react";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { toast } from "sonner";

interface ExtensionInfo {
  name: string;
  version: string;
  crxSize: string;
  id?: string;
}

interface Step {
  num: number;
  title: string;
  desc: string;
  action: React.ReactNode;
}

export default function ExtensionInstallPage() {
  const [step, setStep] = useState(1);
  const [extensionInfo, setExtensionInfo] = useState<ExtensionInfo | null>(null);
  const [downloading, setDownloading] = useState(false);
  const [installed, setInstalled] = useState(false);
  const [checking, setChecking] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  useEffect(() => {
    fetch('/api/extension/info')
      .then(r => r.json())
      .then(data => setExtensionInfo(data))
      .catch(() => setExtensionInfo({
        name: 'pipixia 采集助手',
        version: '1.0.0',
        crxSize: '509 KB'
      }));

    checkInstalled();
  }, []);

  const checkInstalled = async () => {
    setChecking(true);
    try {
      await chrome.runtime.sendMessage(
        'pipixia-extension-id-placeholder',
        { type: 'PING' }
      );
      setInstalled(true);
    } catch {
      // not installed
    } finally {
      setChecking(false);
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const res = await fetch('/pipixia-extension.crx');
      if (!res.ok) throw new Error('下载失败');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pipixia-extension-v${extensionInfo?.version || '1.0.0'}.crx`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success('扩展安装包已下载');
    } catch (e) {
      toast.error('下载失败，请刷新重试');
    } finally {
      setDownloading(false);
    }
  };

  const copyExtensionId = () => {
    const id = extensionInfo?.id || '待安装后获取';
    navigator.clipboard.writeText(id);
    setCopied(id);
    setTimeout(() => setCopied(null), 2000);
  };

  const openChromeExtensions = () => {
    window.open('chrome://extensions/', '_blank');
  };

  const steps: Step[] = [
    { 
      num: 1, 
      title: '下载安装包', 
      desc: '点击下载 .crx 文件，约 509 KB',
      action: (
        <Button onClick={handleDownload} disabled={downloading} className="w-full" size="lg">
          {downloading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
          下载 pipixia-extension.crx
        </Button>
      )
    },
    { 
      num: 2, 
      title: '打开扩展管理页', 
      desc: '在浏览器地址栏输入 chrome://extensions/ 并开启"开发者模式"',
      action: (
        <Button onClick={openChromeExtensions} variant="outline" className="w-full" size="lg">
          <Monitor className="mr-2 h-4 w-4" />
          打开 chrome://extensions/
        </Button>
      )
    },
    { 
      num: 3, 
      title: '拖拽安装', 
      desc: '将下载的 .crx 文件直接拖拽到扩展管理页面中，点击"添加扩展程序"确认',
      action: (
        <div className="space-y-2">
          <div className="p-4 border-2 border-dashed border-primary/50 rounded-lg bg-primary/5 text-center">
            <MousePointerClick className="mx-auto h-8 w-8 text-primary/50 mb-2" />
            <p className="text-sm text-muted-foreground">将 .crx 文件拖到这里（模拟演示）</p>
          </div>
          <p className="text-xs text-muted-foreground text-center">
            实际操作：在 chrome://extensions/ 页面拖入下载的 .crx 文件
          </p>
        </div>
      )
    },
    { 
      num: 4, 
      title: '验证安装', 
      desc: '安装成功后，工具栏会出现 pipixia 图标，访问拼多多商品页自动显示采集按钮',
      action: (
        <div className="flex gap-2">
          <Button onClick={checkInstalled} disabled={checking} variant="outline" className="flex-1">
            {checking ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <CheckCircle className="mr-2 h-4 w-4" />}
            检查安装状态
          </Button>
          <Button onClick={copyExtensionId} disabled={!extensionInfo?.id} variant="outline" className="flex-1">
            <Copy className="mr-2 h-4 w-4" />
            复制扩展 ID
          </Button>
        </div>
      )
    },
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-8 px-4">
      {/* Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-primary/10">
          <Puzzle className="h-8 w-8 text-primary" />
        </div>
        <h1 className="text-3xl font-bold tracking-tight">pipixia 采集助手</h1>
        <p className="text-muted-foreground max-w-2xl mx-auto">
          Chrome 扩展程序 — 在拼多多、1688、淘宝等电商页面一键采集商品到 pipixia 后台，
          自动同步标题、价格、图片、SKU，支持单品/批量采集。
        </p>
        <div className="flex items-center justify-center gap-4 text-sm text-muted-foreground">
          <Badge variant="outline" className="gap-1">
            <CheckCircle className="h-3 w-3 text-green-500" />
            Manifest V3
          </Badge>
          <Badge variant="outline" className="gap-1">
            <Shield className="h-3 w-3 text-blue-500" />
            最小权限
          </Badge>
          <Badge variant="outline" className="gap-1">
            <Zap className="h-3 w-3 text-yellow-500" />
            离线可用
          </Badge>
        </div>
      </div>

      {/* Progress Steps */}
      <div className="space-y-4">
        {steps.map((s, i) => (
          <Card key={s.num} className={`relative overflow-hidden transition-all ${
            step > i ? 'bg-green-50 border-green-200' : step === i + 1 ? 'border-primary ring-2 ring-primary/20' : ''
          }`}>
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="flex-shrink-0 relative">
                  <div className={`flex items-center justify-center w-10 h-10 rounded-full text-sm font-bold ${
                    step > i ? 'bg-green-500 text-white' : step === i + 1 ? 'bg-primary text-white' : 'bg-muted text-muted-foreground'
                  }`}>
                    {step > i ? <CheckCircle className="h-5 w-5" /> : s.num}
                  </div>
                  {i < steps.length - 1 && (
                    <div className="absolute left-4 top-10 bottom-10 w-0.5 bg-muted" />
                  )}
                </div>
                <div className="flex-1 min-w-0 pt-1">
                  <div className="flex items-center gap-2">
                    <span className={`font-semibold ${step > i ? 'text-green-700' : step === i + 1 ? 'text-primary' : ''}`}>
                      步骤 {s.num}：{s.title}
                    </span>
                    {step > i && <CheckCircle className="h-5 w-5 text-green-500" />}
                  </div>
                  <p className="text-sm text-muted-foreground mt-1">{s.desc}</p>
                  <div className="mt-4">{s.action}</div>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Usage Guide */}
      <Separator className="my-8" />
      <div className="space-y-6">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <Settings className="h-5 w-5" />
          使用指南
        </h2>

        <div className="space-y-4">
          <Collapsible open={openFaq === 0} onOpenChange={(open) => setOpenFaq(open ? 0 : null)} className="border rounded-lg">
            <CollapsibleTrigger className="flex items-center justify-between p-4 bg-muted/50 hover:bg-muted transition-colors">
              <span className="font-medium">单品采集：商品详情页「采集到 pipixia」</span>
              <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent className="p-4 space-y-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-4 w-4" /> 访问拼多多商品详情页（URL 含 goods.html?goods_id=）
              </div>
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-4 w-4" /> 页面右下角/侧边栏自动出现「采集到 pipixia」绿色按钮
              </div>
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-4 w-4" /> 点击按钮 → 选择目标店铺 → 确认 → 自动入库并触发翻译
              </div>
              <div className="flex items-center gap-2 text-green-600">
                <CheckCircle className="h-4 w-4" /> 采集成功后 3 秒自动跳转商品列表页查看
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Collapsible open={openFaq === 1} onOpenChange={(open) => setOpenFaq(open ? 1 : null)} className="border rounded-lg">
            <CollapsibleTrigger className="flex items-center justify-between p-4 bg-muted/50 hover:bg-muted transition-colors">
              <span className="font-medium">批量采集：列表/搜索页「采集本页」/「采集选中」</span>
              <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent className="p-4 space-y-3 text-sm text-muted-foreground">
              <div className="flex items-center gap-2 text-blue-600">
                <CheckCircle className="h-4 w-4" /> 进入拼多多搜索结果页、分类页、店铺商品列表页
              </div>
              <div className="flex items-center gap-2 text-blue-600">
                <CheckCircle className="h-4 w-4" /> 每个商品卡片右上角出现圆形勾选圈，点击选中多个
              </div>
              <div className="flex items-center gap-2 text-blue-600">
                <CheckCircle className="h-4 w-4" /> 底部工具栏显示「采集选中 (N)」「采集本页」「获取链接」
              </div>
              <div className="flex items-center gap-2 text-blue-600">
                <CheckCircle className="h-4 w-4" /> 点击批量采集 → 选择店铺 → 后台并发入库
              </div>
              <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                <p className="font-medium text-blue-800 mb-1">💡 进阶技巧</p>
                <ul className="text-xs text-blue-700 space-y-1 list-disc list-inside">
                  <li>工具栏「获取链接」可批量导出当前页所有商品链接为 CSV</li>
                  <li>「翻页采集」可自动滚动翻页并累积采集（需在设置开启）</li>
                  <li>已采集商品会显示绿色「已采集」标记，避免重复</li>
                </ul>
              </div>
            </CollapsibleContent>
          </Collapsible>

          <Collapsible open={openFaq === 2} onOpenChange={(open) => setOpenFaq(open ? 2 : null)} className="border rounded-lg">
            <CollapsibleTrigger className="flex items-center justify-between p-4 bg-muted/50 hover:bg-muted transition-colors">
              <span className="font-medium">账号与店铺绑定：扩展弹窗配置 pipixia 后台凭据</span>
              <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent className="p-4 space-y-3 text-sm text-muted-foreground">
              <ol className="list-decimal list-inside space-y-2">
                <li>点击浏览器工具栏 pipixia 图标打开弹窗</li>
                <li>点击「登录 pipixia」→ 新标签打开后台登录页 → 登录成功后自动返回</li>
                <li>弹窗显示已绑定店铺列表，勾选默认采集目标店铺</li>
                <li>采集时若未选店铺，会弹窗让你临时选择</li>
              </ol>
            </CollapsibleContent>
          </Collapsible>

          <Collapsible open={openFaq === 3} onOpenChange={(open) => setOpenFaq(open ? 3 : null)} className="border rounded-lg">
            <CollapsibleTrigger className="flex items-center justify-between p-4 bg-muted/50 hover:bg-muted transition-colors">
              <span className="font-medium">常见问题排查</span>
              <ChevronDown className="h-5 w-5 text-muted-foreground transition-transform data-[state=open]:rotate-180" />
            </CollapsibleTrigger>
            <CollapsibleContent className="p-4 space-y-3 text-sm text-muted-foreground">
              <div className="grid gap-4 md:grid-cols-2">
                <div className="p-3 bg-red-50 rounded-lg border border-red-100">
                  <p className="font-medium text-red-800 mb-1">❌ 点击采集没反应 / 按钮不显示</p>
                  <ul className="text-xs text-red-700 list-disc list-inside space-y-1">
                    <li>刷新页面重试（扩展需重新注入）</li>
                    <li>确认在商品详情页（URL 含 goods_id）</li>
                    <li>检查 chrome://extensions/ 扩展是否启用</li>
                    <li>拼多多可能更新了页面结构，反馈给开发者</li>
                  </ul>
                </div>
                <div className="p-3 bg-yellow-50 rounded-lg border border-yellow-100">
                  <p className="font-medium text-yellow-800 mb-1">⚠️ 采集提示"账号异常/频率过快"</p>
                  <ul className="text-xs text-yellow-700 list-disc list-inside space-y-1">
                    <li>拼多多反爬触发，降低采集频率</li>
                    <li>在拼多多网页端手动登录买家账号</li>
                    <li>更换 IP 或稍后再试</li>
                  </ul>
                </div>
                <div className="p-3 bg-blue-50 rounded-lg border border-blue-100">
                  <p className="font-medium text-blue-800 mb-1">🔐 批量采集需登录</p>
                  <ul className="text-xs text-blue-700 list-disc list-inside space-y-1">
                    <li>列表页采集需在拼多多网页端登录</li>
                    <li>扩展会复用浏览器 Cookie，无需额外登录</li>
                    <li>若提示未登录，打开 yangkeduo.com 手动登录</li>
                  </ul>
                </div>
                <div className="p-3 bg-green-50 rounded-lg border border-green-100">
                  <p className="font-medium text-green-800 mb-1">✅ 数据同步到后台</p>
                  <ul className="text-xs text-green-700 list-disc list-inside space-y-1">
                    <li>采集成功 → 后台「商品管理」自动出现</li>
                    <li>自动触发翻译、风控、利润核算</li>
                    <li>支持一键上架到 Shopee/跨境店铺</li>
                  </ul>
                </div>
              </div>
            </CollapsibleContent>
          </Collapsible>
        </div>
      </div>

      {/* Footer */}
      <Separator className="my-8" />
      <div className="text-center text-sm text-muted-foreground space-y-2">
        <p>pipixia 采集助手 v{extensionInfo?.version || '1.0.0'} · Manifest V3 · 开源协议 MIT</p>
        <div className="flex items-center justify-center gap-4">
          <a href="/api/extension/source" target="_blank" rel="noopener" className="flex items-center gap-1 hover:text-primary transition-colors">
            <ExternalLink className="h-3 w-3" /> 查看源码
          </a>
          <a href="mailto:support@pipixia.com" className="flex items-center gap-1 hover:text-primary transition-colors">
            <Mail className="h-3 w-3" /> 反馈问题
          </a>
        </div>
      </div>
    </div>
  );
}