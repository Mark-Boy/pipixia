"""
Shopee 自动采集 + 自动上传服务

流程:
1. 从 1688 / 拼多多 采集商品
2. AI 翻译标题/描述到泰语
3. 类目映射 (中文 -> Shopee TH 类目)
4. 价格换算 (CNY -> THB) + 利润计算
5. 上传图片到 Shopee
6. 创建/更新 Shopee 商品
7. 记录上架结果

不包含报关功能
"""

import logging
import time
from typing import Optional
from datetime import datetime
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from api.models.product import Product
from api.models.shop import Shop
from api.models.listing import Listing
from api.models.translate import Translate
from api.services.shopee_v2 import ShopeeV2Client, create_shopee_client
from api.services.translator import translate_title, translate_description
from api.services.crypto import decrypt_aes256
from api.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class ShopeeSyncService:
    """Shopee 自动采集 + 上传服务"""

    def __init__(self, db: Session):
        self.db = db

    # ==================== 1. 采集待上架商品 ====================

    def fetch_pending_products(self, limit: int = 50) -> list[Product]:
        """获取待上架商品 (status = 'pending')"""
        result = self.db.execute(
            select(Product).where(
                Product.status == "pending",
                Product.price_cny > 0,
                Product.price_thb > 0,
            ).limit(limit).order_by(Product.created_at.asc())
        )
        products = result.scalars().all()
        logger.info(f"找到 {len(products)} 个待上架商品")
        return list(products)

    # ==================== 2. 翻译 + 类目映射 ====================

    def prepare_listing_data(self, product: Product, shop_token: str, marketplace: str = "shopee_th") -> dict:
        """
        准备 Shopee 上架数据

        包含:
        - 泰语翻译标题/描述
        - 类目映射
        - 规格信息
        - 图片处理
        """
        # 翻译 (优先用缓存)
        th_title = product.title_th
        th_description = product.description_th

        if not th_title:
            th_title = translate_title(product.title_zh)
            product.title_th = th_title

        if not th_description:
            th_description = translate_description(product.description_zh or "")
            product.description_th = th_description

        # 准备上架数据
        listing_data = {
            "name": th_title or product.title_zh,
            "description": th_description or product.description_zh or "",
            "price": int((product.price_thb or 0) * 1000),  # 转换为泰铢最小单位
            "quantity": product.cost_cny and int(product.cost_cny * 10) or 100,
            "categories": [],
            "models": [],
            "images": [],
            "wholesale_prices": [],
        }

        # 图片 (从 OSS 获取)
        if product.images_oss_keys:
            listing_data["images"] = product.images_oss_keys

        # 规格 (variants)
        if hasattr(product, 'variations') and product.variations:
            for v in product.variations:
                listing_data["models"].append({
                    "name": f"{v.name}",
                    "price": int((v.price_thb or product.price_thb or 0) * 1000),
                    "stock": v.stock or 100,
                    "sku": v.sku or f"SKU-{product.id}-{v.id}",
                    "weight": v.weight or 500,
                    "dimensions": {
                        "length": v.dim_l or 10,
                        "width": v.dim_w or 10,
                        "height": v.dim_h or 10,
                    },
                })

        logger.info(f"商品 {product.id} 上架数据准备完成: {listing_data['name']}")
        return listing_data

    # ==================== 3. 上传图片 ====================

    def upload_product_images(self, client: ShopeeV2Client, image_urls: list[str]) -> list[str]:
        """上传图片到 Shopee，返回 image_id 列表"""
        if not image_urls:
            return []

        image_ids = []
        for url in image_urls:
            try:
                result = client.upload_image(url)
                if result.get("image_id"):
                    image_ids.append(result["image_id"])
                time.sleep(0.5)  # 限流
            except Exception as e:
                logger.error(f"图片上传失败 {url}: {e}")

        return image_ids

    # ==================== 4. 上架商品 ====================

    def list_product(self, client: ShopeeV2Client, product: Product, listing_data: dict) -> dict:
        """
        将商品上架到 Shopee

        Returns:
            {"item_id": "...", "status": "success/failed", "error": "..."}
        """
        # 上传图片
        if listing_data.get("images"):
            image_ids = self.upload_product_images(client, listing_data["images"])
            listing_data["images"] = image_ids  # 替换为 image_id

        try:
            # 创建商品
            result = client.create_product(listing_data)
            item_id = result.get("item_id")

            logger.info(f"商品上架成功: product_id={product.id}, shopee_item_id={item_id}")

            # 更新 product 状态
            product.status = "listed"
            product.updated_at = datetime.utcnow()

            # 创建 listing 记录
            listing = Listing(
                product_id=product.id,
                shop_id=product.shop_id,
                shopee_item_id=item_id,
                shopee_status="active",
                listing_price_thb=product.price_thb,
                stock=listing_data.get("quantity", 0),
                listing_mode="auto",
                audit_status="auto_approved",
            )
            self.db.add(listing)

            # 翻译记录
            if product.title_th and product.title_zh:
                translate_record = Translate(
                    product_id=product.id,
                    source_text=product.title_zh,
                    translated_text=product.title_th,
                    source_lang="zh",
                    target_lang="th",
                )
                self.db.add(translate_record)

            self.db.commit()

            return {"item_id": item_id, "status": "success"}

        except Exception as e:
            logger.error(f"商品上架失败 product_id={product.id}: {e}")
            self.db.rollback()

            product.status = "failed"
            self.db.commit()

            return {"item_id": None, "status": "failed", "error": str(e)}

    # ==================== 5. 批量自动上架 ====================

    def auto_list_all(self, max_products: int = 100, marketplace: str = "shopee_th") -> dict:
        """
        批量自动上架

        流程:
        1. 获取待上架商品
        2. 获取店铺 Token
        3. 创建 Shopee 客户端
        4. 逐一批量上架

        Returns:
            汇总统计
        """
        start_time = time.time()
        logger.info(f"========== 开始批量自动上架 (max={max_products}) ==========")

        # 获取待上架商品
        products = self.fetch_pending_products(limit=max_products)
        if not products:
            logger.info("没有待上架商品")
            return {"total": 0, "success": 0, "failed": 0, "skipped": 0, "elapsed": 0}

        # 获取第一个活跃店铺的 token
        shop_result = self.db.execute(select(Shop).where(Shop.is_active == True).limit(1))  # noqa
        shop = shop_result.scalar_one_or_none()

        if not shop:
            logger.error("没有活跃店铺，请先添加店铺")
            return {"total": len(products), "success": 0, "failed": 0, "skipped": len(products), "error": "No active shop", "elapsed": 0}

        shop_token = decrypt_aes256(shop.shop_token_encrypted)
        client = create_shopee_client(
            shop_id=shop.id,
            token=shop_token,
            marketplace=marketplace,
            sandbox=True,  # 沙盒测试
        )

        # 获取店铺信息 (验证连接)
        try:
            shop_detail = client.get_shop_detail()
            logger.info(f"店铺连接成功: {shop_detail.get('shop_name', 'unknown')}")
        except Exception as e:
            logger.error(f"店铺连接失败: {e}")
            return {"total": len(products), "success": 0, "failed": 0, "skipped": len(products), "error": f"Shop connection failed: {e}", "elapsed": 0}

        # 批量上架
        results = {
            "total": len(products),
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "errors": [],
        }

        for product in products:
            try:
                listing_data = self.prepare_listing_data(product, shop_token, marketplace)
                result = self.list_product(client, product, listing_data)

                if result["status"] == "success":
                    results["success"] += 1
                else:
                    results["failed"] += 1
                    results["errors"].append({
                        "product_id": product.id,
                        "error": result.get("error", "Unknown"),
                    })

                # 限流: 每个商品间隔 2 秒
                time.sleep(2)

            except Exception as e:
                logger.error(f"商品 {product.id} 处理异常: {e}")
                results["failed"] += 1
                results["errors"].append({"product_id": product.id, "error": str(e)})

        elapsed = time.time() - start_time
        results["elapsed"] = round(elapsed, 2)
        logger.info(f"批量上架完成: {results['success']}/{results['total']} 成功, 耗时 {elapsed:.1f}s")

        return results

    # ==================== 6. 更新库存 ====================

    def auto_update_stock(self, shop_id: int, marketplace: str = "shopee_th") -> dict:
        """
        自动同步库存到 Shopee

        从本地 listings 获取 shopee_item_id，同步 stock
        """
        listing_result = self.db.execute(
            select(Listing).where(
                Listing.shop_id == shop_id,
                Listing.shopee_item_id.isnot(None),
                Listing.listing_mode == "auto",
            )
        )
        listings = listing_result.scalars().all()

        if not listings:
            return {"total": 0, "updated": 0, "errors": []}

        shop_result = self.db.execute(select(Shop).where(Shop.id == shop_id).limit(1))
        shop = shop_result.scalar_one_or_none()
        if not shop:
            return {"total": 0, "updated": 0, "errors": ["Shop not found"]}

        shop_token = decrypt_aes256(shop.shop_token_encrypted)
        client = create_shopee_client(shop_id, shop_token, marketplace, sandbox=True)

        updates = []
        for listing in listings:
            if listing.stock is not None:
                updates.append({"item_id": listing.shopee_item_id, "stock": listing.stock})

        if not updates:
            return {"total": 0, "updated": 0, "errors": []}

        result = client.bulk_update_stock(updates)
        return result

    # ==================== 7. 同步商品列表 ====================

    def sync_product_list(self, shop_id: int, marketplace: str = "shopee_th") -> dict:
        """
        从 Shopee 同步商品列表到本地

        定期调用，保持本地商品列表与 Shopee 一致
        """
        shop_result = self.db.execute(select(Shop).where(Shop.id == shop_id).limit(1))
        shop = shop_result.scalar_one_or_none()
        if not shop:
            return {"error": "Shop not found"}

        shop_token = decrypt_aes256(shop.shop_token_encrypted)
        client = create_shopee_client(shop_id, shop_token, marketplace, sandbox=True)

        page = 1
        total_synced = 0
        all_items = []

        while True:
            result = client.list_products(page=page, size=100)
            items = result.get("items", [])
            all_items.extend(items)
            total_synced += len(items)

            if len(items) < 100 or page >= 10:  # 最多拉 1000 条
                break
            page += 1
            time.sleep(1)

        logger.info(f"同步商品列表完成: {total_synced} 个商品")
        return {"shop_id": shop_id, "total_synced": total_synced, "items": all_items[:50]}  # 返回前 50 条

    # ==================== 8. 状态查询 ====================

    def get_sync_status(self) -> dict:
        """获取同步状态汇总"""
        pending_result = self.db.execute(select(Product).where(Product.status == "pending"))
        pending_count = len(pending_result.scalars().all())

        listed_result = self.db.execute(select(Product).where(Product.status == "listed"))
        listed_count = len(listed_result.scalars().all())

        failed_result = self.db.execute(select(Product).where(Product.status == "failed"))
        failed_count = len(failed_result.scalars().all())

        shop_result = self.db.execute(select(Shop).where(Shop.is_active == True))  # noqa
        active_shops = len(shop_result.scalars().all())

        return {
            "pending_products": pending_count,
            "listed_products": listed_count,
            "failed_products": failed_count,
            "active_shops": active_shops,
            "timestamp": datetime.utcnow().isoformat(),
        }


# ==================== 同步上下文管理器 ====================
def get_sync_service(db: Session) -> ShopeeSyncService:
    return ShopeeSyncService(db)
