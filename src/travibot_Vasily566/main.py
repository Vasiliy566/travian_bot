import logging
import random
import time
from datetime import datetime
from enum import Enum
from typing import Tuple, List, Optional

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement

logger = logging.getLogger(__name__)


class MainBuildSlot:
    def __init__(self, element: WebElement,
                 name: str,
                 level: int,
                 subslot: WebElement):
        self.element = element
        self.name = name
        self.level = level
        self.subslot = subslot


BUILDING_PLAN_TIER1 = [
    ("Пунтк сбора", 1, 1),
    ("Склад", 3, 1),
    ("Амбар", 2, 1),

]

BUILDING_PLAN_TIER2 = [
    ("Главное здание", 5, 1),
    ("Склад", 5, 1),
    ("Капканщик", 6, 1),
    ("Тайник", 10, 1),

    ("Казарма", 3, 1),
    ("Академия", 1, 1),
    ("Кузница", 1, 1),
    ("Тайник", 10, 2),
    ("Склад", 8, 1),
    ("Амбар", 6, 1),
    ("Рынок", 3, 1),
    ("Главное здание", 10, 1),
    ("Академия", 10, 1),
    ("Изгородь", 10, 1),

    ("Ратуша", 2, 1),
    ("Мастерская", 1, 1),
    ("Резиденция", 3, 1),
    ("Кузница", 3, 1),
    ("Конюшня", 5, 1),
    ("Резиденция", 10, 1),
]


def upgrade_building_on_main(driver, tier: int, url: str, building_tier1: List[Tuple] = None,
                             building_tier2: List[Tuple] = None) -> bool:
    try:
        middle_city_buttons = driver.find_element(By.CLASS_NAME, "village.buildingView")
        middle_city_buttons.click()

        slots = driver.find_elements(By.XPATH, ".//*[contains(@class,'buildingSlot')]")
        buildings = []
        empty = []
        for slot in slots:
            building_name = slot.get_attribute("data-name")
            if building_name == "Изгородь":
                subslot = driver.find_element(By.CLASS_NAME, "level.colorLayer.good.aid40.gaul")
                buildings.append(
                    MainBuildSlot(element=slot, name=building_name, level=int(subslot.get_attribute("data-level")),
                                  subslot=subslot))
                continue
            subslot = slot.find_element(By.XPATH, ".//*[contains(@href,'build.php')]")
            if building_name is None or building_name == "":
                try:
                    subslot = slot.find_element(By.CLASS_NAME, "buildingShape.iso").find_element(By.XPATH, ".//*")

                    empty.append(MainBuildSlot(element=slot, name="", level=0, subslot=subslot))
                except Exception as e:
                    ...
            else:

                buildings.append(MainBuildSlot(element=slot, name=slot.get_attribute("data-name"),
                                               level=int(subslot.get_attribute("data-level")), subslot=subslot))
        for step in building_tier1 or BUILDING_PLAN_TIER1 if tier == 1 else building_tier2 or BUILDING_PLAN_TIER2:
            build_name, required_level, amount = step
            existing_buildings: list[MainBuildSlot] = []
            for b in buildings:
                if b.name == build_name:
                    existing_buildings.append(b)

            # Все построили и все здания прокачены
            if len(existing_buildings) >= amount and [e.level >= required_level for e in existing_buildings].count(
                    True) >= amount:
                continue
            else:
                # Строим еще домик ( открывается после 10 лвла прокачки старого)
                if len(existing_buildings) != amount and all([e.level == required_level for e in existing_buildings]):
                    logger.info(f"Choose to build as new {build_name}")
                    empty[0].subslot.click()
                    # Ищем в инфраструктуре, если нет - в вкладке Военные, затем промышленность

                    for elem in driver.find_elements(By.CLASS_NAME, "buildingWrapper"):
                        if build_name.lower() in elem.find_element(By.TAG_NAME, "h2").text.lower():
                            elem.find_element(By.TAG_NAME, "button").click()
                            return True

                    driver.find_element(By.CLASS_NAME, "tabItem.military.normal").click()
                    for elem in driver.find_elements(By.CLASS_NAME, "buildingWrapper"):
                        if build_name.lower() in elem.find_element(By.TAG_NAME, "h2").text.lower():
                            elem.find_element(By.TAG_NAME, "button").click()
                            return True

                    driver.find_element(By.CLASS_NAME, "tabItem.resources.normal").click()
                    for elem in driver.find_elements(By.CLASS_NAME, "buildingWrapper"):
                        if build_name.lower() in elem.find_element(By.TAG_NAME, "h2").text.lower():
                            elem.find_element(By.TAG_NAME, "button").click()
                            return True
                    return False
                # апгрейд
                else:
                    upgrade_me = [e for e in existing_buildings if e.level < required_level]
                    logger.info(f"Choose to grade {build_name} {upgrade_me[0].level} -> {upgrade_me[0].level + 1}")
                    if upgrade_me[0].name == "Изгородь":
                        driver.get(url + "build.php?id=40&gid=33")
                    else:
                        upgrade_me[0].subslot.click()
                    build_button = driver.find_element(By.XPATH, ".//*[contains(@value,'Улучшить до уровня')]")
                    build_button.click()
                    return True
    except Exception as e:
        logger.warning(f"Failed upgrade main: {e}")
        return False
    return False


class Actions(Enum):
    celebration = "CELEBRATION"
    build_traps = "BUILD_TRAPS"
    build_colonist = "BUILD_COLONIST"


def get_upcoming_attack(driver):
    resource_menu = driver.find_element(By.CSS_SELECTOR, "a.village.resourceView")
    resource_menu.click()
    upcoming = driver.find_element(By.CLASS_NAME, "villageInfobox.movements")
    if "Напад" in upcoming.find_element(By.CLASS_NAME, "a1").text:
        timer = upcoming.find_element(By.CLASS_NAME, "timer")
        logger.info(f"Upcaming attack in {timer.text}")


def action_in_city_middle(driver, action: Actions):
    middle_city_buttons = driver.find_element(By.CLASS_NAME, "village.buildingView")
    middle_city_buttons.click()

    if action == Actions.celebration:
        try:
            slot = driver.find_element(By.XPATH, ".//*[contains(@data-name,'Ратуша')]")
            slot.click()

            process = driver.find_element(By.XPATH, ".//*[contains(@value,'Провести')]")
            process.click()
            time.sleep(2)
        except Exception as e:
            logger.info("No celebration")
        else:
            logger.info("Celebration started")
    elif action == Actions.build_traps:
        slot = driver.find_element(By.XPATH, ".//*[contains(@data-name,'Капканщик')]")
        slot.click()

        available_amount = driver.find_element(By.CLASS_NAME, "cta")
        available = available_amount.find_element(By.TAG_NAME, "a").text
        if int(available) > 0:
            inp = available_amount.find_element(By.TAG_NAME, "input")
            inp.clear()
            inp.send_keys(10)

            driver.find_element(By.CLASS_NAME, "textButtonV1.green.startBuild").click()
            time.sleep(2)
            logger.info("Purchased traps")
        logger.info("No traps aviable")
    elif action == Actions.build_colonist:
        slot = driver.find_element(By.XPATH, ".//*[contains(@data-name,'Резиденция')]")
        slot.click()
        driver.find_element(By.CLASS_NAME, "content.favor.favorKey1").click()

        page = driver.find_element(By.CLASS_NAME, "action.troop.troopt10")
        available = page.find_element(By.CLASS_NAME, "cta").find_element(By.TAG_NAME, "a")
        if int(available.text) > 0:
            inp = page.find_element(By.TAG_NAME, "input")
            inp.clear()
            inp.send_keys(1)
            driver.find_element(By.CLASS_NAME, "textButtonV1.green.startBuild").click()
            time.sleep(2)
            logger.info("Purchased colonists")
        logger.info("Colonists not available")


def get_current_army(driver):
    middle_city_buttons = driver.find_element(By.CLASS_NAME, "village.buildingView")
    middle_city_buttons.click()

    try:
        slot = driver.find_element(By.XPATH, ".//*[contains(@data-name,'Пункт сбора')]")
        slot.click()

        driver.find_element(By.CLASS_NAME, "content.overviewRallyPoint.favor.favorKey1").click()

        troops = driver.find_elements(By.CLASS_NAME, "troop_details")
        for troop in troops:
            try:
                if troop.find_element(By.CLASS_NAME, "troopHeadline").find_element(By.TAG_NAME,
                                                                                   "a").text == "Собственные войска":
                    return int(troop.find_element(By.CLASS_NAME, "units.last").find_elements(By.TAG_NAME, "td")[0].text)
                else:
                    ...
            except Exception as e:
                ...
    except Exception as e:
        logger.info(f"Failed to get army: {e}")
    return 0


def get_min_level_elem(driver):
    resource_menu = driver.find_element(By.CSS_SELECTOR, "a.village.resourceView")
    resource_menu.click()
    resource_fields = driver.find_element(By.ID, "resourceFieldContainer")
    min_level_elem = None
    min_level = -1
    for elem in resource_fields.find_elements(By.CSS_SELECTOR, "*"):
        # //button[contains(@value,'Улучшить до уровня')]"
        field_css_class = elem.get_attribute("class")
        if field_css_class is not None and "level" in field_css_class and "colorLayer" in field_css_class:
            level = int(field_css_class[-1])
            # if level > 3:
            #     if "gid2" in elem.get_attribute("class"):  # глина
            #         level -= 1
            # elif "gid3" in elem.get_attribute("class"):  # железо
            #     level -= 1
            # elif "gid1" in elem.get_attribute("class"):  # лес
            #     level -= 1

        else:
            continue
        if min_level_elem is None:
            min_level_elem = elem
            min_level = level
        else:
            if level < min_level:
                min_level = level
                min_level_elem = elem
            if "gid4" in elem.get_attribute("class") and level <= min_level:  # зерно в приоритете из за блока
                min_level = level
                min_level_elem = elem
    return min_level, min_level_elem


def get_achivs_reses(driver):
    time.sleep(1)
    quest_master_button = driver.find_element(By.ID, "questmasterButton")
    quest_master_button.click()

    time.sleep(1)

    while True:
        try:
            get_res_button = driver.find_element(By.CSS_SELECTOR,
                                                 "button.textButtonV2.buttonFramed.collect.preventAnimation.rectangle.withText.green")
        except NoSuchElementException:
            break
        get_res_button.click()
        logger.info("Got achivements res")
        time.sleep(1)
    try:
        close_achives_button = driver.find_element(By.ID, "closeContentButton")
        close_achives_button.click()
    except Exception as e:
        ...


def get_from_hero(driver):
    hero_image = driver.find_element(By.ID, "heroImageButton")
    hero_image.click()

    time.sleep(1)
    res_buttons = driver.find_elements(By.CSS_SELECTOR, "div.heroItem.consumable.inventory")
    for consume_res_button in res_buttons:
        if consume_res_button.find_elements(By.XPATH, ".//*[contains(@class,'item')]")[0].get_attribute(
                "class").replace("item", "").strip() \
                not in ("145", "146", "147", "148"):
            continue
        time.sleep(1)
        try:
            consume_res_button.click()
        except Exception as e:
            cancell_button = driver.find_element(By.CSS_SELECTOR,
                                                 "button.textButtonV2.buttonFramed.rectangle.withText.grey")
            cancell_button.click()


        else:
            approve_button = driver.find_element(By.CSS_SELECTOR,
                                                 "button.textButtonV2.buttonFramed.rectangle.withText.green")
            if approve_button.get_attribute("disabled") == 'true':
                cancel_button = driver.find_element(By.CSS_SELECTOR,
                                                    "button.textButtonV2.buttonFramed.rectangle.withText.grey")
                cancel_button.click()

            else:
                approve_button.click()
                logger.info("Got res from hero")
    try:
        time.sleep(1)
        close_button = driver.find_element(By.ID, "closeContentButton")
        close_button.click()
    except Exception as e:
        logger.info(f"Failed to close: {e}")
        ...
    time.sleep(1)


def login(driver, url, email, password):
    driver.get(url)
    elem = driver.find_element(By.NAME, "name")
    elem.clear()
    elem.send_keys(email)
    elem2 = driver.find_element(By.NAME, "password")
    elem2.clear()
    elem2.send_keys(password)

    try:
        button = driver.find_element(By.XPATH, "//button[@value='Login']")
    except Exception as e:
        button = driver.find_element(By.XPATH, "//button[@value='Войти']")
    button.click()
    return driver


def is_second_village_exist(driver):
    try:
        second_ref = driver.find_element(By.XPATH, "//*[@data-sortindex='2']").find_element(By.TAG_NAME,
                                                                                            "a").get_attribute("href")
        return second_ref
    except Exception:
        return None


def purchase_resource(driver, url, building_tier1: List[Tuple] = None, building_tier2: List[Tuple] = None):
    try:
        in_progress_buildings = driver.find_element(By.CLASS_NAME, "finishNow")
    except Exception as e:
        in_progress = False
        logger.info("Process resource building...")
    else:
        in_progress = True
        logger.info("Already in progress...")

    if not in_progress:
        # get done achivements resources
        get_achivs_reses(driver)
        min_level, min_level_elem = get_min_level_elem(driver)
        upgraded = False
        if 1 <= min_level < 3:
            logger.info(f"Resources are ok, min level = {min_level}, go tier1")
            upgraded = upgrade_building_on_main(driver, tier=1, url=url, building_tier1=building_tier1)
        elif min_level >= 5:
            logger.info(f"Resources are ok, min level = {min_level}, go tier2")
            upgraded = upgrade_building_on_main(driver, tier=2, url=url, building_tier2=building_tier2)

            # Пытаемся запустить праздник
            # Пытаемся построить ловушки

        if not upgraded:
            min_level, min_level_elem = get_min_level_elem(driver)
            time.sleep(1)
            logger.info("Not upgraded main, try upgrade res")
            min_level_elem.click()
            try:
                purchase_button = driver.find_element(By.XPATH, "//button[contains(@value,'Улучшить до уровня')]")
                purchase_button.click()
            except NoSuchElementException:
                get_from_hero(driver)
                logger.info("Not enought resources!!!")
            else:
                logger.info("Upgrade started")
            try:
                close_button = driver.find_element(By.XPATH, "//button[contains(@class,'contentTitleButton')]")
                close_button.click()
            except NoSuchElementException:
                ...


def post_actions(driver):
    # move hero to trip
    driver.find_element(By.ID, "heroImageButton").click()

    time.sleep(1)
    driver.find_element(By.XPATH, ".//*[contains(@data-tab,'2')]").click()
    hp = int(driver.find_element(By.CLASS_NAME, "stats").find_element(By.CLASS_NAME, "value").text.encode('ascii',
                                                                                                          'ignore').decode().replace(
        "%", ""))
    if hp < 40:
        logger.info("hero is low, ski trip")
        return
    trip_list = driver.find_element(By.XPATH, "//*[contains(@href,'adventures')]")
    trip_list.click()
    time.sleep(2)
    try:
        trip = driver.find_element(By.CSS_SELECTOR, "button.textButtonV2.buttonFramed.rectangle.withText.green")
        trip.click()
    except NoSuchElementException as e:
        ...
    else:
        logger.info("Moved hero to trip")

    # upgrade hero

    driver.find_element(By.ID, "heroImageButton").click()

    try:
        time.sleep(1)
        driver.find_element(By.XPATH, ".//*[contains(@data-tab,'2')]").click()
        elem = driver.find_element(By.XPATH, "//*[contains(@name,'resourceProduction')]")
        elem.clear()
        elem.send_keys(1000)
        save = driver.find_element(By.ID, "savePoints")
        save.click()
        time.sleep(2)
    except Exception as e:
        ...
    else:
        logger.info("Hero point purchased")

    try:
        action_in_city_middle(driver, Actions.build_colonist)
    except Exception as e:
        logger.info("colonist failed")

    try:
        action_in_city_middle(driver, Actions.celebration)
    except Exception as e:
        logger.info("celebration failed")

    try:
        action_in_city_middle(driver, Actions.build_traps)
    except Exception as e:
        logger.info("traps failed")

    try:
        get_upcoming_attack(driver)
    except Exception as e:
        ...

    army_n = get_current_army(driver)
    logger.info(f"{army_n}  Фаланг в деревне.")
    if army_n < 100:
        ...


def run_travian(creds: Optional[List[Tuple]] = None, creds_file: Optional[str] = None,
                server_url: str = "https://ts5.x1.europe.travian.com/",
                infinity_run=True,
                browser_visible=False,
                default_strategy=False,
                building_tier1: List[Tuple[str, str]] = None,
                building_tier2: List[Tuple[str, str]] = None):
    if default_strategy is True:
        raise Exception("Not unsupported, check for updates in future versions.")
    if creds is None and creds_file is None:
        raise Exception("One of creds/creds_file must be provided")
    if creds is None and creds_file is not None:
        creds = []
        with open(creds_file) as f:
            for l in f.readlines():
                creds.append(l.split())

    if browser_visible:
        driver = webdriver.Firefox()
    else:

        op = webdriver.FirefoxOptions()
        op.add_argument('--headless')
        driver = webdriver.Firefox(options=op)

    if infinity_run:
        while True:
            for email, password in creds:
                try:
                    logger.info(f"Started with {email}")
                    driver = login(driver, server_url, email, password)
                    purchase_resource(driver, server_url)
                    second = is_second_village_exist(driver)
                    if second is not None:
                        driver.get(second)
                        purchase_resource(driver, server_url)
                    post_actions(driver)
                except Exception as e:

                    logger.info(f"Failed for {email=}, {password=}\n{e}")
                logger.info(f"Done at {datetime.now()}")
                time.sleep(2)
            time.sleep(4 * 60)
    else:
        for email, password in creds:
            try:
                logger.info(f"Started with {email}")
                driver = login(driver, server_url, email, password)
                purchase_resource(driver, server_url)
                second = is_second_village_exist(driver)
                if second is not None:
                    driver.get(second)
                    purchase_resource(driver, server_url)
                post_actions(driver)
            except Exception as e:

                logger.info(f"Failed for {email=}, {password=}\n{e}")
            logger.info(f"Done at {datetime.now()}")
            time.sleep(2)

    driver.close()
