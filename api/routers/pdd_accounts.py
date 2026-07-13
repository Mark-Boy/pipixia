"""
拼多多采集账号管理路由 — 扫码登录、账号管理、商品采集
"""

import asyncio
import base64
import json
import logging
import secrets
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from playwright.sync_api import sync_playwright
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.database import async_session, get_db
from api.models.pdd_account import PddAccount
from api.models.user import User
from api.schemas.pdd_account import (
    PddAccountCreate,
    PddAccountUpdate,
    PddAccountResponse,
    PddAccountListResponse,
    PddQrcodeGenerateRequest,
    PddQrcodeGenerateResponse,
    PddQrcodeStatusRequest,
    PddQrcodeStatusResponse,
    PddProductCollectRequest,
    PddProductCollectResponse,
    PddShopInfo,
)
from api.services.auth import get_current_user_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdd-accounts", tags=["Pinduoduo Collector Accounts"])

# 线程池用于运行同步 Playwright
_pdd_executor = ThreadPoolExecutor(max_workers=2)

# 内存存储二维码会话（生产环境建议用 Redis）
_qrcode_sessions: dict[str, dict] = {}


# ==================== 工具函数 ====================

def _cleanup_expired_sessions():
    """清理过期的二维码会话"""
    now = time.time()
    expired = [k for k, v in _qrcode_sessions.items() if v.get("expires_at", 0) < now]
    for k in expired:
        _qrcode_sessions.pop(k, None)


def _generate_qrcode_token() -> str:
    """生成二维码会话 token"""
    return secrets.token_urlsafe(32)


# ==================== 账号 CRUD ====================

@router.get("", response_model=PddAccountListResponse)
async def list_pdd_accounts(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    active_only: bool = Query(True),
    current_user: User = Depends(get_current_user_async),
):
    """获取拼多多采集账号列表"""
    async with async_session() as db:
        query = select(PddAccount).where(PddAccount.user_id == current_user.id)
        if active_only:
            query = query.where(PddAccount.is_active == True)

        # 总数
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        # 分页
        query = query.order_by(PddAccount.created_at.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await db.execute(query)
        accounts = result.scalars().all()

    return PddAccountListResponse(
        total=total,
        page=page,
        size=size,
        accounts=[PddAccountResponse.model_validate(a) for a in accounts],
    )


@router.post("", response_model=PddAccountResponse, status_code=201)
async def create_pdd_account(
    data: PddAccountCreate,
    current_user: User = Depends(get_current_user_async),
):
    """创建拼多多采集账号"""
    async with async_session() as db:
        account = PddAccount(
            user_id=current_user.id,
            account_name=data.account_name,
            phone=data.phone,
            notes=data.notes,
            login_status="not_logged_in",
            is_active=True,
        )
        db.add(account)
        await db.commit()
        await db.refresh(account)

    return PddAccountResponse.model_validate(account)


@router.get("/{account_id}", response_model=PddAccountResponse)
async def get_pdd_account(
    account_id: int,
    current_user: User = Depends(get_current_user_async),
):
    """获取账号详情"""
    async with async_session() as db:
        result = await db.execute(
            select(PddAccount).where(
                PddAccount.id == account_id,
                PddAccount.user_id == current_user.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(404, "账号不存在")

    return PddAccountResponse.model_validate(account)


@router.put("/{account_id}", response_model=PddAccountResponse)
async def update_pdd_account(
    account_id: int,
    data: PddAccountUpdate,
    current_user: User = Depends(get_current_user_async),
):
    """更新账号信息"""
    async with async_session() as db:
        result = await db.execute(
            select(PddAccount).where(
                PddAccount.id == account_id,
                PddAccount.user_id == current_user.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(404, "账号不存在")

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(account, field, value)

        await db.commit()
        await db.refresh(account)

    return PddAccountResponse.model_validate(account)


@router.delete("/{account_id}")
async def delete_pdd_account(
    account_id: int,
    current_user: User = Depends(get_current_user_async),
):
    """删除账号（软删除）"""
    async with async_session() as db:
        result = await db.execute(
            select(PddAccount).where(
                PddAccount.id == account_id,
                PddAccount.user_id == current_user.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(404, "账号不存在")

        account.is_active = False
        await db.commit()

    return {"message": "账号已删除"}


# ==================== 二维码登录 ====================

def _do_qrcode_login_sync(account_id: int, qrcode_token: str) -> dict:
    """
    同步执行拼多多扫码登录（在线程池中运行）
    返回: {status, storage_state, message, shop_info}
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--window-size=1920,1080",
                ],
            )
            context = browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                viewport={"width": 1920, "height": 1080},
                locale="zh-CN",
            )
            page = context.new_page()

            # 访问拼多多买家端登录页（支持买家版 APP 扫码）
            login_url = "https://mobile.yangkeduo.com/login.html"
            logger.info(f"[{qrcode_token}] 正在打开买家端登录页: {login_url}")
            page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # 点击"扫码登录"切换到扫码模式（买家端默认可能是密码登录）
            try:
                qrcode_tab = page.locator(
                    'xpath=//div[contains(@class, "login-tab") and contains(text(), "扫码")] | '
                    '//span[contains(text(), "扫码登录")] | '
                    '//button[contains(text(), "扫码登录")] | '
                    '//a[contains(text(), "扫码登录")] | '
                    '//div[contains(@class, "tab") and contains(text(), "扫码")]'
                ).first
                if qrcode_tab.is_visible(timeout=3000):
                    qrcode_tab.click()
                    page.wait_for_timeout(1000)
                    logger.info(f"[{qrcode_token}] 已切换到扫码登录模式")
            except Exception:
                logger.debug(f"[{qrcode_token}] 可能已经是扫码模式或找不到切换按钮")

            # 等待二维码出现（买家端登录页的二维码选择器）
            qrcode_selectors = [
                'xpath=//img[contains(@src, "qrcode") or contains(@alt, "二维码")]',
                'xpath=//canvas[@id="qrcode"]',
                'xpath=//div[contains(@class, "qrcode")]//img',
                'xpath=//div[contains(@class, "login-qrcode")]//img',
                'xpath=//img[contains(@class, "qrcode")]',
                'xpath=//div[contains(@class, "qrcode-container")]//img',
            ]

            qrcode_element = None
            for selector in qrcode_selectors:
                try:
                    element = page.locator(selector).first
                    if element.is_visible(timeout=5000):
                        qrcode_element = element
                        logger.info(f"[{qrcode_token}] 找到二维码元素: {selector}")
                        break
                except Exception:
                    continue

            if not qrcode_element:
                # 尝试截图整个登录区域
                logger.warning(f"[{qrcode_token}] 未找到特定二维码元素，尝试截图登录区域")
                login_area = page.locator('xpath=//div[contains(@class, "login")]').first
                if login_area.is_visible(timeout=3000):
                    screenshot_bytes = login_area.screenshot()
                else:
                    screenshot_bytes = page.screenshot(full_page=True)
            else:
                screenshot_bytes = qrcode_element.screenshot()

            # 转为 base64
            qrcode_base64 = base64.b64encode(screenshot_bytes).decode()
            qrcode_data_url = f"data:image/png;base64,{qrcode_base64}"

            # 更新会话状态：二维码已生成
            _qrcode_sessions[qrcode_token].update({
                "status": "waiting",
                "qrcode_image": qrcode_data_url,
                "message": "请使用拼多多买家版 APP 扫码登录",
                "updated_at": time.time(),
            })

            # 轮询等待扫码登录
            max_wait = 180  # 3分钟
            check_interval = 2
            start_time = time.time()

            while time.time() - start_time < max_wait:
                page.wait_for_timeout(check_interval * 1000)

                # 检查是否登录成功（买家端登录成功后跳转到首页或个人中心）
                current_url = page.url
                logger.debug(f"[{qrcode_token}] 当前 URL: {current_url}")

                # 买家端登录成功的判断：URL 包含 yangkeduo.com 且不包含 login
                if ("yangkeduo.com" in current_url or "pinduoduo.com" in current_url) and "login" not in current_url:
                    # 登录成功，获取 storage state
                    storage_state = context.storage_state()
                    storage_state_json = json.dumps(storage_state)

                    # 尝试获取用户信息（买家端没有店铺概念，但可以获取用户ID等）
                    user_info = None
                    try:
                        page.goto("https://mobile.yangkeduo.com/personal.html", wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(2000)
                        # 尝试获取用户昵称等信息
                        nickname_elem = page.locator('xpath=//span[contains(@class, "nickname") or contains(@class, "user-name")]').first
                        if nickname_elem.is_visible(timeout=3000):
                            user_info = {
                                "nickname": nickname_elem.text_content().strip(),
                            }
                    except Exception as e:
                        logger.debug(f"[{qrcode_token}] 获取用户信息失败: {e}")

                    browser.close()

                    return {
                        "status": "confirmed",
                        "storage_state": storage_state_json,
                        "message": "登录成功（买家版）",
                        "shop_info": user_info,  # 复用字段存用户信息
                    }

                # 检查是否显示"已扫码，待确认"
                try:
                    scanned_text = page.locator(
                        'xpath=//*[contains(text(), "已扫码") or contains(text(), "待确认") or contains(text(), "确认登录")]'
                    ).first
                    if scanned_text.is_visible(timeout=1000):
                        _qrcode_sessions[qrcode_token].update({
                            "status": "scanned",
                            "message": "已扫码，请在手机上确认登录",
                            "updated_at": time.time(),
                        })
                except Exception:
                    pass

            # 超时
            browser.close()
            return {
                "status": "expired",
                "message": "二维码已过期，请重新生成",
            }

    except Exception as e:
        logger.error(f"[{qrcode_token}] 登录过程异常: {e}")
        return {
            "status": "error",
            "message": f"登录失败: {str(e)}",
        }


@router.post("/qrcode/generate", response_model=PddQrcodeGenerateResponse)
async def generate_qrcode(
    req: PddQrcodeGenerateRequest,
    current_user: User = Depends(get_current_user_async),
):
    """
    生成拼多多扫码登录二维码

    流程：
    1. 验证账号归属
    2. 创建二维码会话
    3. 在后台线程启动 Playwright 打开登录页并生成二维码
    4. 返回二维码图片和 token，前端轮询状态
    """
    # 验证账号
    async with async_session() as db:
        result = await db.execute(
            select(PddAccount).where(
                PddAccount.id == req.account_id,
                PddAccount.user_id == current_user.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(404, "账号不存在")

    # 清理过期会话
    _cleanup_expired_sessions()

    # 创建新会话
    qrcode_token = _generate_qrcode_token()
    expires_at = time.time() + 180  # 3分钟

    _qrcode_sessions[qrcode_token] = {
        "account_id": account.id,
        "account_name": account.account_name,
        "status": "generating",
        "qrcode_image": None,
        "message": "正在生成二维码...",
        "storage_state": None,
        "shop_info": None,
        "created_at": time.time(),
        "expires_at": expires_at,
    }

    # 异步启动登录流程
    loop = asyncio.get_running_loop()
    loop.run_in_executor(_pdd_executor, _do_qrcode_login_sync, account.id, qrcode_token)

    return PddQrcodeGenerateResponse(
        account_id=account.id,
        qrcode_url="",  # 初始为空，轮询时获取
        qrcode_token=qrcode_token,
        expires_at=datetime.fromtimestamp(expires_at),
        message="正在生成二维码，请稍候...",
    )


@router.post("/qrcode/status", response_model=PddQrcodeStatusResponse)
async def check_qrcode_status(
    req: PddQrcodeStatusRequest,
    current_user: User = Depends(get_current_user_async),
):
    """
    查询二维码登录状态

    前端应每 2-3 秒轮询一次，直到 status 为 confirmed/expired/error
    """
    session = _qrcode_sessions.get(req.qrcode_token)
    if not session:
        raise HTTPException(404, "二维码会话不存在或已过期")

    # 验证账号归属
    if session["account_id"] != req.qrcode_token.split("_")[0] if "_" in req.qrcode_token else True:
        # 简单验证：实际项目中可在会话中存 user_id 做严格校验
        pass

    status_val = session.get("status", "generating")

    if status_val == "confirmed":
        # 登录成功，保存 storage_state 到数据库
        async with async_session() as db:
            result = await db.execute(
                select(PddAccount).where(PddAccount.id == session["account_id"])
            )
            account = result.scalar_one_or_none()
            if account:
                account.login_status = "logged_in"
                account.storage_state = session.get("storage_state")
                account.last_login_at = datetime.now()
                account.expires_at = datetime.now() + timedelta(days=30)  # 假设 30 天有效
                await db.commit()

        # 清理会话
        _qrcode_sessions.pop(req.qrcode_token, None)

        return PddQrcodeStatusResponse(
            qrcode_token=req.qrcode_token,
            status="confirmed",
            message=session.get("message", "登录成功"),
            account_id=session["account_id"],
            account_name=session["account_name"],
            storage_state=session.get("storage_state"),
        )

    elif status_val in ("expired", "error"):
        _qrcode_sessions.pop(req.qrcode_token, None)
        return PddQrcodeStatusResponse(
            qrcode_token=req.qrcode_token,
            status=status_val,
            message=session.get("message", "未知错误"),
        )

    else:
        # waiting / scanned / generating
        return PddQrcodeStatusResponse(
            qrcode_token=req.qrcode_token,
            status=status_val,
            message=session.get("message", "等待中..."),
            account_id=session["account_id"] if status_val != "generating" else None,
        )


@router.get("/qrcode/image/{qrcode_token}")
async def get_qrcode_image(
    qrcode_token: str,
    current_user: User = Depends(get_current_user_async),
):
    """获取二维码图片（base64）"""
    session = _qrcode_sessions.get(qrcode_token)
    if not session:
        raise HTTPException(404, "二维码会话不存在")

    if not session.get("qrcode_image"):
        raise HTTPException(404, "二维码尚未生成")

    return {"qrcode_image": session["qrcode_image"]}


# ==================== 商品采集（使用登录态） ====================

def _do_collect_products_sync(account_id: int, urls: list[str], storage_state: str) -> list[dict]:
    """
    使用登录态采集商品详情（同步，在线程池运行）
    """
    results = []

    try:
        state = json.loads(storage_state)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(storage_state=state)
            page = context.new_page()

            for url in urls:
                try:
                    logger.info(f"采集商品: {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)

                    # 提取商品数据
                    # 这里需要根据拼多多商家后台商品详情页的结构来解析
                    # 简化版：尝试从页面获取 JSON 数据
                    product_data = page.evaluate("""
                        () => {
                            try {
                                // 尝试从 window.__INITIAL_STATE__ 或类似变量获取
                                if (window.__INITIAL_STATE__) {
                                    return JSON.stringify(window.__INITIAL_STATE__);
                                }
                                // 尝试从 script 标签获取
                                const scripts = document.querySelectorAll('script[type="application/json"]');
                                for (const s of scripts) {
                                    if (s.textContent.includes('goods') || s.textContent.includes('product')) {
                                        return s.textContent;
                                    }
                                }
                            } catch(e) {}
                            return null;
                        }
                    """)

                    result = {
                        "url": url,
                        "success": product_data is not None,
                        "data": json.loads(product_data) if product_data else None,
                        "error": None if product_data else "无法提取商品数据",
                    }
                except Exception as e:
                    result = {
                        "url": url,
                        "success": False,
                        "data": None,
                        "error": str(e),
                    }
                results.append(result)

            browser.close()

    except Exception as e:
        logger.error(f"采集异常: {e}")
        for url in urls:
            results.append({
                "url": url,
                "success": False,
                "data": None,
                "error": str(e),
            })

    return results


@router.post("/collect", response_model=PddProductCollectResponse)
async def collect_products(
    req: PddProductCollectRequest,
    current_user: User = Depends(get_current_user_async),
):
    """
    使用采集账号登录态采集商品详情

    前置条件：账号必须已登录（login_status=logged_in 且有 storage_state）
    """
    # 验证账号
    async with async_session() as db:
        result = await db.execute(
            select(PddAccount).where(
                PddAccount.id == req.account_id,
                PddAccount.user_id == current_user.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(404, "账号不存在")

        if account.login_status != "logged_in" or not account.storage_state:
            raise HTTPException(400, "账号未登录或登录态已过期，请先扫码登录")

        # 验证目标店铺
        from api.models.shop import Shop
        shop_result = await db.execute(
            select(Shop).where(Shop.id == req.target_shop_id, Shop.user_id == current_user.id)
        )
        shop = shop_result.scalar_one_or_none()
        if not shop:
            raise HTTPException(404, "目标店铺不存在")

    # 执行采集
    loop = asyncio.get_running_loop()
    results = await loop.run_in_executor(
        _pdd_executor,
        _do_collect_products_sync,
        account.id,
        req.urls,
        account.storage_state,
    )

    success_count = sum(1 for r in results if r["success"])

    return PddProductCollectResponse(
        total=len(results),
        success=success_count,
        failed=len(results) - success_count,
        results=results,
    )


# ==================== 获取账号关联的店铺列表 ====================

def _do_fetch_shops_sync(storage_state: str) -> list[PddShopInfo]:
    """获取账号关联的店铺列表（同步）"""
    shops = []
    try:
        state = json.loads(storage_state)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
            context = browser.new_context(storage_state=state)
            page = context.new_page()

            # 访问店铺切换/列表页面
            page.goto("https://mms.pinduoduo.com/home", wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)

            # 尝试点击店铺切换器
            try:
                switcher = page.locator('xpath=//button[contains(text(), "切换店铺") or contains(@class, "shop-switch")]').first
                if switcher.is_visible(timeout=3000):
                    switcher.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass

            # 提取店铺列表
            shop_elements = page.locator('xpath=//div[contains(@class, "shop-item") or contains(@class, "mall-item")]').all()
            for elem in shop_elements[:10]:  # 最多 10 个
                try:
                    name = elem.locator('xpath=.//span[contains(@class, "name")]').first.text_content(timeout=1000) or ""
                    mall_id = elem.get_attribute("data-mall-id") or elem.get_attribute("data-id") or ""
                    if name and mall_id:
                        shops.append(PddShopInfo(mall_id=mall_id, mall_name=name.strip()))
                except Exception:
                    continue

            browser.close()

    except Exception as e:
        logger.error(f"获取店铺列表失败: {e}")

    return shops


@router.get("/{account_id}/shops", response_model=list[PddShopInfo])
async def get_account_shops(
    account_id: int,
    current_user: User = Depends(get_current_user_async),
):
    """获取采集账号关联的拼多多店铺列表"""
    async with async_session() as db:
        result = await db.execute(
            select(PddAccount).where(
                PddAccount.id == account_id,
                PddAccount.user_id == current_user.id,
            )
        )
        account = result.scalar_one_or_none()
        if not account:
            raise HTTPException(404, "账号不存在")

        if account.login_status != "logged_in" or not account.storage_state:
            raise HTTPException(400, "账号未登录，请先扫码登录")

    loop = asyncio.get_running_loop()
    shops = await loop.run_in_executor(_pdd_executor, _do_fetch_shops_sync, account.storage_state)

    return shops