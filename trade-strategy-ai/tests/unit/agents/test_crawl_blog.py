from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, UTC
from types import SimpleNamespace

from src.agents.data_agent.skills import crawl_blog as crawl_blog_module
from src.agents.data_agent.skills.crawl_blog import (
    ExistingArticleIndex,
    ClassifiedComment,
    classify_comment,
    should_stop_incremental_scan,
    compute_content_hash,
    load_existing_raw_article_index_from_db,
    LOW_VALUE_COMMENTS,
)
from src.agents.data_agent.sites.base import AuthProvider
from src.agents.data_agent.sites.tgb import TgbCrawler


def test_classify_comment_marks_author_and_filters_low_value_text() -> None:
    comment = classify_comment(
        raw_text="谢谢[em_01]",
        comment_author="javxsp",
        article_author="javxsp",
        parent_comment_id=None,
        root_comment_id=None,
        reply_to_user=None,
    )

    assert comment.is_author is True
    assert comment.clean_text == "谢谢"
    assert comment.is_filtered is True
    assert "low_value" in comment.filter_reasons


def test_classify_comment_normal_comment() -> None:
    """普通评论不被过滤。"""
    comment = classify_comment(
        raw_text="这篇文章分析得很有道理",
        comment_author="reader",
        article_author="author",
        parent_comment_id=None,
        root_comment_id=None,
        reply_to_user=None,
    )
    assert comment.is_filtered is False
    assert comment.filter_reasons == []


def test_classify_comment_short_text_filtered() -> None:
    """太短的评论被过滤。"""
    comment = classify_comment(
        raw_text="好",
        comment_author="reader",
        article_author="author",
        parent_comment_id=None,
        root_comment_id=None,
        reply_to_user=None,
    )
    assert comment.is_filtered is True


def test_classify_comment_image_only_filtered() -> None:
    """只有图片无文字的评论被过滤。"""
    comment = classify_comment(
        raw_text="",
        comment_author="reader",
        article_author="author",
        parent_comment_id=None,
        root_comment_id=None,
        reply_to_user=None,
    )
    assert comment.is_filtered is True
    assert "image_only" in comment.filter_reasons


def test_should_stop_incremental_scan_when_url_already_seen() -> None:
    index = ExistingArticleIndex(
        seen_urls={"https://www.tgb.cn/a/2qxp6lHUymO"},
        seen_hashes=set(),
        last_seen_article_url=None,
        last_seen_published_at=None,
    )

    assert (
        should_stop_incremental_scan(
            source_url="https://www.tgb.cn/a/2qxp6lHUymO",
            content_hash="abc",
            published_at=None,
            index=index,
        )
        is True
    )


def test_should_stop_incremental_scan_no_match() -> None:
    """未匹配的 URL 继续。"""
    index = ExistingArticleIndex(
        seen_urls={"https://www.tgb.cn/a/old"},
        seen_hashes=set(),
        last_seen_article_url=None,
        last_seen_published_at=None,
    )
    result = should_stop_incremental_scan(
        source_url="https://www.tgb.cn/a/new",
        content_hash="new_hash",
        published_at=None,
        index=index,
    )
    assert result is False


def test_should_stop_incremental_scan_by_hash() -> None:
    """已见过的 hash 停止。"""
    index = ExistingArticleIndex(
        seen_urls=set(),
        seen_hashes={"abc123"},
        last_seen_article_url=None,
        last_seen_published_at=None,
    )
    result = should_stop_incremental_scan(
        source_url="https://www.tgb.cn/a/new",
        content_hash="abc123",
        published_at=None,
        index=index,
    )
    assert result is True


def test_should_stop_incremental_scan_by_published_at() -> None:
    """发布时间早于最后时间停止。"""
    index = ExistingArticleIndex(
        seen_urls=set(),
        seen_hashes=set(),
        last_seen_article_url=None,
        last_seen_published_at="2026-04-11T10:00:00",
    )
    result = should_stop_incremental_scan(
        source_url="https://www.tgb.cn/a/new",
        content_hash=None,
        published_at=datetime.fromisoformat("2026-04-10T10:00:00"),
        index=index,
    )
    assert result is True


def test_compute_content_hash() -> None:
    """compute_content_hash 正确计算哈希。"""
    h1 = compute_content_hash("test content")
    h2 = compute_content_hash("test content")
    assert h1 == h2
    assert len(h1) == 64  # SHA256 hex length


def test_compute_content_hash_different() -> None:
    """不同内容产生不同哈希。"""
    h1 = compute_content_hash("content1")
    h2 = compute_content_hash("content2")
    assert h1 != h2


def test_low_value_comments_set() -> None:
    """LOW_VALUE_COMMENTS 包含常见低价值评论。"""
    assert "谢谢" in LOW_VALUE_COMMENTS
    assert "感谢" in LOW_VALUE_COMMENTS
    assert "打卡" in LOW_VALUE_COMMENTS
    assert "点赞" in LOW_VALUE_COMMENTS
    assert "666" in LOW_VALUE_COMMENTS


def test_tgb_crawler_parses_article_detail_and_comments() -> None:
    crawler = TgbCrawler(
        auth_provider=AuthProvider(site="tgb.cn", cookie="cookie-value"),
        list_url="https://www.tgb.cn/user/blog/moreTopic",
        author_id="10461311",
    )
    html = """
    <html>
      <body>
        <h1>教你看懂市场内力与外力的本质</h1>
        <div class="p_wenz">
          <p>很多人亏损，就是看不透市场本质。</p>
          <p>今天在这里跟大家讲一个关键理解。</p>
        </div>
        <div class="comment">
          <a href="/user">Makaz</a>
          <span>2026-03-28 20:10</span>
          <div>[微笑][微笑][鲜花]</div>
          <span>第5楼 · 淘股吧</span>
        </div>
        <div class="comment reply">
          <a href="/user">javxsp</a>
          <span class="badge">楼主</span>
          <span>2026-03-28 20:46</span>
          <div>上面回复了</div>
        </div>
      </body>
    </html>
    """

    detail = crawler.parse_article_detail(html, "https://www.tgb.cn/a/2qxp6lHUymO")
    comments = crawler.parse_comments(html)

    assert detail["title"] == "教你看懂市场内力与外力的本质"
    assert "很多人亏损" in detail["content_text"]
    assert comments[0]["author_name"] == "Makaz"
    assert comments[0]["raw_text"] == "[微笑][微笑][鲜花]"
    assert comments[1]["author_name"] == "javxsp"


def test_tgb_crawler_parses_article_list_with_relative_a_links() -> None:
    crawler = TgbCrawler(
        auth_provider=AuthProvider(site="tgb.cn", cookie="cookie-value"),
        list_url="https://www.tgb.cn/user/blog/moreTopic",
        author_id="10461311",
    )
    html = """
    <html>
      <body>
        <a href="a/2qxp6lHUymO">教你看懂市场内力与外力的本质</a>
        <a href="a/2qxp6lHUymO">重复链接</a>
      </body>
    </html>
    """

    articles = crawler.parse_article_list(html)

    assert articles == [
        {
            "source_url": "https://www.tgb.cn/a/2qxp6lHUymO",
            "source_article_id": "2qxp6lHUymO",
            "title": "教你看懂市场内力与外力的本质",
        }
    ]


def test_tgb_crawler_parses_comments_from_comment_data_blocks() -> None:
    crawler = TgbCrawler(
        auth_provider=AuthProvider(site="tgb.cn", cookie="cookie-value"),
        list_url="https://www.tgb.cn/user/blog/moreTopic",
        author_id="10461311",
    )
    html = """
    <html>
      <body>
        <div class="comment-lists">
          <div class="comment-data user_10461311" id="reply_10461311_1">
            <div class="comment-data-right right">
              <div class="comment-data-user">
                <a class="user-name" href="/blog/10461311">javxsp</a>
                <span class="pcyclspan">2026-03-28 19:40</span>
              </div>
              <div class="comment-data-text" id="reply97111259">
                新的下周思路新帖已分享
                <img src="https://css.tgb.cn/images/face/024.png"/>
              </div>
            </div>
          </div>
          <div class="comment-data user_9940855" id="reply_9940855_2">
            <div class="comment-data-right right">
              <div class="comment-data-user">
                <a class="user-name" href="/blog/9940855">Makaz</a>
                <span class="pcyclspan">2026-03-28 20:10</span>
              </div>
              <div class="comment-data-text" id="reply97111565">
                <img src="https://css.tgb.cn/images/face/001.png"/>
                <img src="https://css.tgb.cn/images/face/024.png"/>
              </div>
            </div>
          </div>
        </div>
      </body>
    </html>
    """

    comments = crawler.parse_comments(html)

    assert len(comments) == 2
    assert comments[0]["author_name"] == "javxsp"
    assert comments[0]["raw_text"] == "新的下周思路新帖已分享"
    assert comments[0]["published_at"] == "2026-03-28 19:40"
    assert comments[1]["author_name"] == "Makaz"
    assert comments[1]["raw_text"] == ""


def test_tgb_crawler_parses_comments_from_text_blocks() -> None:
    crawler = TgbCrawler(
        auth_provider=AuthProvider(site="tgb.cn", cookie="cookie-value"),
        list_url="https://www.tgb.cn/user/blog/moreTopic",
        author_id="10461311",
    )
    html = """
    <html>
      <body>
        <div>查看所有跟帖</div>
        <div>javxsp</div>
        <div>楼主 2026-03-28 19:40</div>
        <div>新的下周思路新帖已分享</div>
        <div>沙发 · 淘股吧</div>
        <div>Makaz</div>
        <div>2026-03-28 20:10</div>
        <div>[微笑][微笑][鲜花][鲜花]</div>
        <div>板凳 · 淘股吧</div>
        <div>javxsp</div>
        <div>楼主 2026-03-28 20:46</div>
        <div>Makaz 2026-03-28 20:10</div>
        <div>[微笑][微笑][鲜花][鲜花]</div>
        <div>第5楼 · 淘股吧</div>
      </body>
    </html>
    """

    comments = crawler.parse_comments(html)

    assert len(comments) == 3
    assert comments[0]["author_name"] == "javxsp"
    assert comments[1]["author_name"] == "Makaz"
    assert comments[2]["author_name"] == "javxsp"
    assert comments[2]["raw_text"] == "[微笑][微笑][鲜花][鲜花]"


def test_tgb_crawler_uses_rendered_html_when_render_js_enabled(monkeypatch) -> None:
    crawler = TgbCrawler(
        auth_provider=AuthProvider(site="tgb.cn", cookie="cookie-value"),
        list_url="https://www.tgb.cn/user/blog/moreTopic",
        author_id="10461311",
        render_js=True,
    )
    rendered_html = """
    <html>
      <body>
        <h1>动态页面标题</h1>
        <div class="p_wenz"><p>动态渲染后的正文内容。</p></div>
      </body>
    </html>
    """

    monkeypatch.setattr(
        "src.agents.data_agent.sites.tgb.render_page_html",
        lambda *args, **kwargs: rendered_html,
    )
    monkeypatch.setattr(crawler, "_throttle", lambda: None)

    detail = crawler.fetch_article_detail("https://www.tgb.cn/a/2qxp6lHUymO")

    assert detail["title"] == "动态页面标题"
    assert "动态渲染后的正文内容" in detail["content_text"]


def test_crawl_source_to_db_reports_pending_crawl_totals(monkeypatch) -> None:
    """主进度应围绕待抓取的新文章数，并只上报待抓取文章。"""

    class _FakeCrawler:
        def fetch_article_list(self):
            return [
                {"source_url": "https://example.com/a1", "source_article_id": "a1", "title": "A1", "published_at": None},
                {"source_url": "https://example.com/a2", "source_article_id": "a2", "title": "A2", "published_at": None},
                {"source_url": "https://example.com/a3", "source_article_id": "a3", "title": "A3", "published_at": None},
            ]

        def fetch_article_detail(self, article_url: str):
            return {
                "title": article_url.rsplit("/", 1)[-1],
                "content_text": "content",
                "content_html": "<p>content</p>",
                "full_html": "<html></html>",
                "topic_id": "1",
            }

        def fetch_comments(self, **kwargs):
            return []

    class _FakeSession:
        async def commit(self):
            return None

    @asynccontextmanager
    async def _fake_session_scope():
        yield _FakeSession()

    async def _fake_upsert_raw_article(**kwargs):
        return True

    async def _fake_save_crawl_state_to_db(**kwargs):
        return None

    progress_events: list[dict] = []
    monkeypatch.setattr(crawl_blog_module, "session_scope", _fake_session_scope)
    monkeypatch.setattr(crawl_blog_module, "upsert_raw_article", _fake_upsert_raw_article)
    monkeypatch.setattr(crawl_blog_module, "save_crawl_state_to_db", _fake_save_crawl_state_to_db)

    result = asyncio.run(
        crawl_blog_module.crawl_source_to_db(
            source_cfg=SimpleNamespace(
                source="tgb",
                site="tgb.cn",
                trader_id="trader_a",
                author_id="10461311",
                author_name="author",
            ),
            crawler=_FakeCrawler(),
            index=ExistingArticleIndex(
                seen_urls={"https://example.com/a1"},
                seen_hashes=set(),
                last_seen_article_url=None,
                last_seen_published_at=None,
            ),
            max_articles=None,
            progress_callback=progress_events.append,
        )
    )

    assert result == 2
    assert progress_events[0]["candidate_total"] == 3
    assert progress_events[0]["existing_total"] == 1
    assert progress_events[0]["current"] == 0
    assert progress_events[0]["total"] == 2
    assert progress_events[1]["current"] == 0
    assert progress_events[1]["total"] == 2
    assert progress_events[1]["current_step"] == "fetch:https://example.com/a2"
    assert progress_events[2]["current"] == 1
    assert progress_events[2]["total"] == 2
    assert progress_events[2]["current_step"] == "store:https://example.com/a2"
    assert progress_events[3]["current_step"] == "fetch:https://example.com/a3"
    assert progress_events[-1]["current"] == 2
    assert progress_events[-1]["total"] == 2


def test_load_existing_raw_article_index_from_db_reads_real_raw_articles() -> None:
    """真实已存在数量应来自 raw_articles，而不是只依赖 crawl_state。"""

    class _FakeResult:
        def all(self):
            return [
                ("https://example.com/a1", "hash-1"),
                ("https://example.com/a2", None),
                (None, "hash-3"),
            ]

    class _FakeSession:
        async def execute(self, stmt):
            return _FakeResult()

    result = asyncio.run(load_existing_raw_article_index_from_db(_FakeSession(), "tgb", "10461311"))

    assert result["seen_urls"] == {"https://example.com/a1", "https://example.com/a2"}
    assert result["seen_hashes"] == {"hash-1", "hash-3"}
