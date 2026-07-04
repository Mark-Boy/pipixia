export interface Product {
  id: string;
  titleZh: string;
  titleTh: string;
  sourcePlatform: "1688" | "pdd";
  sourceItemId: string;
  priceCny: number;
  priceThb: number;
  profitMargin: number;
  riskStatus: "pass" | "block" | "pending";
  status: "listed" | "pending" | "auditing" | "blocked";
  thumbnail?: string;
  createdAt: string;
}

export interface AuditItem {
  id: string;
  productId: string;
  titleZh: string;
  titleTh: string;
  descriptionTh: string;
  profitMargin: number;
  confidenceScore: number;
  riskFlag: boolean;
  riskReason?: string;
  status: "pending" | "approved" | "rejected";
  createdAt: string;
}

export interface FinancialMetrics {
  totalSales: number;
  totalProfit: number;
  avgProfitMargin: number;
  profitDeviation: number;
}

export interface RiskLog {
  id: string;
  productId: string;
  productTitle: string;
  riskType: "brand" | "prohibited" | "profit" | "category";
  riskDetail: string;
  actionTaken: string;
  createdAt: string;
}
