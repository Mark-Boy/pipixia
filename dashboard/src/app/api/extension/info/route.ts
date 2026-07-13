import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.json({
    name: "pipixia 采集助手",
    version: "1.0.0",
    crxSize: "509 KB",
    id: "pipixia-extension-id-placeholder",
    description: "在拼多多、1688、淘宝等电商页面一键采集商品到 pipixia 后台",
    permissions: ["activeTab", "storage", "scripting", "host_permissions"],
    hosts: ["*://*.yangkeduo.com/*", "*://mobile.yangkeduo.com/*"],
    updateUrl: "https://your-domain.com/api/extension/update.xml",
  });
}