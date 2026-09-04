"""从官方终末地 Wiki 页面读取 Shumei 生成的设备标识。"""

import asyncio
import json
import sys

from playwright.async_api import async_playwright


WIKI_URL = "https://wiki.skland.com/endfield"
STORAGE_KEY = "SK_SHUMEI_DEVICE_ID_KEY"


async def read_device_id() -> str:
    """加载官方页面并返回 localStorage 中的设备标识。"""
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        try:
            page = await browser.new_page()
            await page.goto(WIKI_URL, wait_until="domcontentloaded", timeout=30_000)
            for _ in range(10):
                value = await page.evaluate(
                    "key => window.localStorage.getItem(key)", STORAGE_KEY
                )
                if value:
                    try:
                        device_id = str((json.loads(value) or {}).get("id") or "").strip()
                    except (TypeError, json.JSONDecodeError):
                        device_id = ""
                    if device_id:
                        return device_id
                await page.wait_for_timeout(1_000)
            return ""
        finally:
            await browser.close()


def main() -> int:
    try:
        device_id = asyncio.run(read_device_id())
    except Exception as error:  # noqa: BLE001 - CI 中回退到 Secret
        print(f"自动获取终末地设备标识失败，将使用备用 Secret：{error}", file=sys.stderr)
        return 1
    if not device_id:
        print("官方页面未生成终末地设备标识，将使用备用 Secret", file=sys.stderr)
        return 1
    # 标准输出只输出标识，供工作流写入 GITHUB_ENV；禁止输出其他页面内容。
    print(device_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
