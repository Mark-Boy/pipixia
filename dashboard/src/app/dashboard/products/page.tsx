"use client";

import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { ProductsPage } from "./products-page";

export default function Products() {
  return (
    <DashboardLayout>
      <ProductsPage />
    </DashboardLayout>
  );
}
