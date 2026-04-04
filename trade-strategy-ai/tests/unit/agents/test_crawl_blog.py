from __future__ import annotations

from src.agents.data_agent.skills.crawl_blog import (
    ExistingArticleIndex,
    classify_comment,
    should_stop_incremental_scan,
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


def test_tgb_crawler_parses_article_detail_and_comments() -> None:
    crawler = TgbCrawler(
        auth_provider=AuthProvider(site="tgb.cn", cookie="cookie-value"),
        list_url="https://www.tgb.cn/user/blog/moreTopic?userID=10461311",
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
        list_url="https://www.tgb.cn/user/blog/moreTopic?userID=10461311",
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
        list_url="https://www.tgb.cn/user/blog/moreTopic?userID=10461311",
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
        list_url="https://www.tgb.cn/user/blog/moreTopic?userID=10461311",
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
