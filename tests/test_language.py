from thesis.research.language import looks_english


def test_english_posts_are_kept():
    assert looks_english("Apple has turned into Wall Street's hedge against the AI trade, and I think the stock looks cheap here.")
    assert looks_english("Why people subject themselves to TV operating systems for chromecasts when a mini PC works fine")


def test_short_text_is_kept():
    assert looks_english("AAPL up")
    assert looks_english("Świetnie")  # too short to judge


def test_other_languages_are_dropped():
    polish = "Robotics ma swój własny łańcuch dostaw, który się zmienia, a Apple przenosi produkcję z Chin do Indii i Wietnamu"
    assert not looks_english(polish)
    assert not looks_english("Акции Apple выросли после публикации квартального отчёта, аналитики ждут продолжения роста")
    assert not looks_english("苹果公司发布了最新季度财报，营收超过市场预期，股价在盘后交易中上涨")
