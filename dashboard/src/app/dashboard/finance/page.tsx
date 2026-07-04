"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { FinancePage } from "./finance-page";

export default function Finance() {
  return (
    <DashboardLayout>
      <FinancePage />
    </DashboardLayout>
  );
}
