"""批量核查测试 — 覆盖5大类舆论话题"""
import asyncio
import json
import sys
import httpx

TEST_ITEMS = [
    # 一、国际政治与经济
    ("国际1", "特朗普第二任期推行激进关税政策，引发全球贸易战，各国纷纷报复美国"),
    ("国际2", "俄乌冲突进入僵持阶段，双方都不愿停火，第三次世界大战一触即发"),
    ("国际3", "金砖国家扩容后即将推出新货币，美元霸权将在5年内彻底崩溃"),
    ("国际4", "朝韩关系彻底破裂，朝鲜已经切断所有交通线，半岛战争即将爆发"),

    # 二、国内社会与经济
    ("国内1", "延迟退休政策落地后，年轻人就业更难了，养老金也要减少一半"),
    ("国内2", "中国楼市彻底崩盘，房价暴跌70%，大量房企破产倒闭"),
    ("国内3", "中国结婚率跌破0.5%，独居人口超3亿，单身社会导致人口危机"),
    ("国内4", "预制菜全部进入中小学食堂，孩子们每天吃防腐剂，家长愤怒抗议"),

    # 三、科技与数码
    ("科技1", "AI生成内容已经无法识别真假，整个互联网的信息都是假的"),
    ("科技2", "人形机器人将取代2亿工人，未来5年大量岗位消失，人类面临失业潮"),
    ("科技3", "无人驾驶出租车全面商用后，全国3000万司机将全部失业"),

    # 四、文娱与体育
    ("文娱1", "巴黎奥运会中国金牌数造假，实际金牌数远低于官方公布"),

    # 五、生态环境与公共卫生
    ("生态1", "呼吸道传染病多种病原叠加流行，医院系统已经崩溃，比新冠时更严重"),
    ("生态2", "日本核污染水排海后，中国沿海海鲜全部受到污染，不能再吃了"),
]

async def test_one(client, label, text):
    """测试单条信息，返回摘要"""
    try:
        async with client.stream(
            "POST", "http://localhost:8000/api/analyze",
            json={"text": text}, timeout=120
        ) as resp:
            result = {}
            buffer = ""
            async for chunk in resp.aiter_bytes():
                buffer += chunk.decode()
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    if line.startswith("data: "):
                        try:
                            d = json.loads(line[6:])
                            evt = d.get("event", "")
                            data = d.get("data", {})
                            if evt == "agent_complete" and d.get("agent") == "malice":
                                result["evil"] = data.get("evil_score", 0)
                                result["escalation"] = data.get("escalation", "")
                            elif evt == "report":
                                result["verdict"] = data.get("overall_verdict", "?")
                                result["display"] = data.get("verdict_display", "")
                                result["one_line"] = data.get("one_sentence_verdict", "")[:80]
                                ec = data.get("evidence_chain", [])
                                result["claims"] = len(ec)
                                result["category"] = data.get("category", "")
                            elif evt == "knowledge_hit":
                                result["kb"] = f"命中({data.get('similarity', 0):.0%})"
                        except:
                            pass
            return label, text[:40], result
    except Exception as e:
        return label, text[:40], {"error": str(e)[:50]}


async def main():
    print("=" * 80)
    print("🧪 真相猎人 — 批量核查测试（5大类·15条抽样）")
    print("=" * 80)

    async with httpx.AsyncClient(timeout=120) as client:
        # 顺序测试（避免API限流）
        results = []
        for label, text in TEST_ITEMS:
            print(f"\n{'─'*60}")
            print(f"📋 [{label}] {text[:60]}...")
            sys.stdout.flush()

            l, t, r = await test_one(client, label, text)
            results.append((l, t, r))

            # 打印单条结果
            kb = r.get("kb", "")
            if kb:
                print(f"  📚 {kb}")
            else:
                evil = r.get("evil", "?")
                esc = r.get("escalation", "?")
                v = r.get("display", r.get("verdict", "?"))
                claims = r.get("claims", 0)
                print(f"  👁️ evil={evil:.0%} | {esc} | 📊 {v} | claims={claims}")
            sys.stdout.flush()

    # 汇总
    print(f"\n{'='*80}")
    print("📊 测试汇总")
    print(f"{'='*80}")
    deep_count = sum(1 for _, _, r in results if r.get("escalation") == "deep")
    quick_count = sum(1 for _, _, r in results if r.get("escalation") == "quick")
    kb_count = sum(1 for _, _, r in results if "kb" in r)
    error_count = sum(1 for _, _, r in results if "error" in r)

    print(f"  总数: {len(results)} | 深度核查: {deep_count} | 快速判伪: {quick_count} | 知识库命中: {kb_count} | 出错: {error_count}")

    # 分类统计
    cats = {}
    for _, _, r in results:
        c = r.get("category", "unknown")
        cats[c] = cats.get(c, 0) + 1
    print(f"  操纵分类分布: {cats}")

    print(f"\n✅ 批量测试完成")


if __name__ == "__main__":
    asyncio.run(main())
