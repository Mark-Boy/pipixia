"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { AuditPage } from "./audit-page";

export default function Audit() {
  return (
    <DashboardLayout>
      <AuditPage />
    </DashboardLayout>
  );
}
