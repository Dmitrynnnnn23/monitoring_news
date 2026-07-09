from app.categorizer import DEFAULT_CATEGORY, categorize, is_macro_relevant


def test_key_rate():
    assert categorize("Банк России принял решение сохранить ключевую ставку") == "ставка ЦБ"
    assert categorize("Основные направления денежно-кредитной политики") == "ставка ЦБ"


def test_inflation():
    assert categorize("Годовая инфляция в июне замедлилась до 4,2%") == "инфляция"
    assert categorize("Инфляционные ожидания населения снизились") == "инфляция"


def test_gdp():
    assert categorize("Росстат оценил рост ВВП во втором квартале") == "ВВП"
    assert categorize("Промышленное производство выросло на 2%") == "ВВП"


def test_fx():
    assert categorize("Официальные курсы валют ЦБ РФ на 10.07.2026") == "курс валют"
    assert categorize("Курс доллара превысил 80 рублей") == "курс валют"


def test_sanctions():
    assert categorize("ЕС обсуждает новый пакет санкций против России") == "санкции"


def test_reserves():
    assert categorize("Международные резервы РФ выросли за неделю") == "резервы"
    assert categorize("Объём ФНБ на 1 июля составил...") == "резервы"


def test_budget():
    assert categorize("Минфин разместил ОФЗ на 50 млрд рублей") == "бюджет и налоги"


def test_banking():
    assert (
        categorize("Результаты мониторинга максимальных процентных ставок кредитных организаций")
        == "банковский сектор"
    )


def test_default():
    assert categorize("Открылась выставка современного искусства") == DEFAULT_CATEGORY


def test_macro_relevance():
    assert is_macro_relevant("Росстат опубликовал данные о безработице")
    assert is_macro_relevant("ЦБ сохранил ключевую ставку")
    assert not is_macro_relevant("Футбольный клуб выиграл матч чемпионата")
