import asyncio
import random
from playwright.async_api import Playwright, async_playwright
from lxml import etree
from urllib.parse import unquote
import re
import os
from ddddocr import DdddOcr


class Sougou(object):
    def __init__(self):
        self.search_key = ''
        self.urls = []
        self.yzm = False
        self.ocr = DdddOcr(old=True, show_ad=False)
        self.code = ''

    async def parser(self, response):
        res = response.replace('<em>', '').replace('</em>', '').replace("<!--red_beg-->", "").replace("<!--red_end-->",
                                                                                                      "")
        html = etree.HTML(res)
        name = html.xpath(
            '//ul[@class="news-list2"]/li/div/div[2]/p/a/text()')
        wexin = html.xpath('//ul[@class="news-list2"]/li/div/div[2]/p[@class="info"]/label/text()')
        if name and wexin:
            for na, wx in zip(name, wexin):
                result = {
                    "公众号名称": na,
                    "微信号": wx
                }
                print(result)

    async def on_response(self, response):
        url = unquote(response.url, 'utf-8')
        if url.startswith(f'https://weixin.sogou.com/weixin') and response.status == 200:
            print(f"当前解析界面{url}")
            try:
                html = await response.text()
                await self.parser(html)
            except Exception as e:
                print("e", e)
        elif "https://weixin.sogou.com/antispider/util/seccode.php" in response.url:
            # 触发验证码请求
            try:
                self.code = self.ocr.classification(await response.body())
            except Exception as e:
                print("验证码报错")
            print("验证码已验证")

    async def search(self, page, key):
        self.search_key = key
        page.on('response', self.on_response)
        try:
            # await page.goto(f'https://weixin.sogou.com/weixin?query={key}&type=1&ie=utf8')
            await page.goto(
                f'https://weixin.sogou.com/antispider/?from=%2fweixin%3Fquery%3d%E9%A5%BF%E4%BA%86%E4%B9%88%26hp%3d54%26sut%3d5706%26lkt%3d3%2C1686713591614%2C1686713596186%26_sug_%3dy%26sst0%3d1686713596290%26oq%3d%E9%A5%BF%E4%BA%86%26stj0%3d0%26stj1%3d6%26stj%3d0%3B6%3B1%3B0%26stj2%3d0%26hp1%3d%26_sug_type_%3d%26s_from%3dinput%26ri%3d0%26type%3d1%26page%3d4%26ie%3dutf8%26w%3d01015002%26dr%3d1&antip=wx_hb')
            self.yzm = True
            await page.wait_for_load_state('networkidle')
        except Exception as e:
            print(f"Failed to load: {e}")
        while self.yzm:
            print("等待验证码通过")
            if self.code:
                await page.fill("#seccodeInput", self.code)
                # 验证成功
                await page.click('#submit')
                print("验证成功")
                await page.wait_for_timeout(3000)
                self.yzm = False

        print("开始翻页")
        delay = random.uniform(1, 1)
        await asyncio.sleep(delay)
        while self.yzm != True:
            try:
                await page.click('text=下一页', timeout=5000)
                await page.wait_for_load_state('networkidle')
            except Exception as e:
                break

    async def run(self, playwright: Playwright, key) -> None:

        browser = await playwright.chromium.launch(headless=False, args=["--no-sandbox"])
        context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.150 Safari/537.36",
            "viewport": {"width": 1440, "height": 900},
            "ignore_https_errors": True,
            "permissions": ["geolocation", "midi", "microphone", "camera"],
        }
        context = await browser.new_context(**context_options)
        page = await context.new_page()
        await context.add_init_script(path='stealth.min.js')

        await self.search(page, key)

        print(f"{len(self.urls)} URLs found:\n{sorted(self.urls)}")
        await browser.close()

    async def main(self, key) -> None:
        async with async_playwright() as playwright:
            await self.run(playwright, key)


if __name__ == '__main__':
    data = Sougou()
    asyncio.run(data.main('饿了么'))
