"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { ListingsPage } from "./listings-page";

export default function Listings() {
  return (
    <DashboardLayout>
      <ListingsPage />
    </DashboardLayout>
  );
}
