# main.py
import requests_cache
import re
import logging
from bs4 import BeautifulSoup
from tqdm import tqdm
from urllib.parse import urljoin
from utils import get_response, find_tag

from constants import BASE_DIR, MAIN_DOC_URL, PEP_URL, EXPECTED_STATUS
from configs import configure_argument_parser, configure_logging
from outputs import control_output


def whats_new(session):
    results = [("Ссылка на статью", "Заголовок", "Редактор, Автор")]
    whats_new_url = urljoin(MAIN_DOC_URL, "whatsnew/")
    response = get_response(session, whats_new_url)
    soup = BeautifulSoup(response.text, features="lxml")
    main_div = find_tag(soup, "section", attrs={"id": "what-s-new-in-python"})
    div_with_ul = find_tag(main_div, "div", attrs={"class": "toctree-wrapper"})
    sections_by_python = div_with_ul.find_all("li", attrs={"class": "toctree-l1"})
    for section in tqdm(sections_by_python):
        version_a_tag = section.find("a")
        href = version_a_tag["href"]
        version_link = urljoin(whats_new_url, href)
        response = get_response(session, version_link)
        if response is None:
            continue
        soup = BeautifulSoup(response.text, features="lxml")
        h1 = find_tag(soup, "h1")
        dl = find_tag(soup, "dl")

        dl_text = dl.text.replace("\n", " ")
        results.append((version_link, h1.text, dl_text))
    return results


def latest_versions(session):
    results = [("Ссылка на документацию", "Версия", "Статус")]
    response = get_response(session, MAIN_DOC_URL)
    soup = BeautifulSoup(response.text, features="lxml")
    sidebar = find_tag(soup, "div", attrs={"class": "sphinxsidebarwrapper"})
    ul_tags = sidebar.find_all("ul")
    for ul in ul_tags:
        if "All versions" in ul.text:
            a_tags = ul.find_all("a")
            break
    else:
        raise Exception("Ничего не нашлось")
    pattern = r"Python (?P<version>\d\.\d+) \((?P<status>.*)\)"
    for a_tag in a_tags:
        link = a_tag["href"]
        text_match = re.search(pattern, a_tag.text)
        if text_match:
            version = text_match.group("version")
            status = text_match.group("status")
        else:
            version = a_tag.text
            status = ""
        results.append((link, version, status))

    return results


def download(session):
    downloads_url = urljoin(MAIN_DOC_URL, "download.html")
    response = get_response(session, downloads_url)
    soup = BeautifulSoup(response.text, features="lxml")
    table_tag = find_tag(soup, "table", attrs={"class": "docutils"})
    pdf_a4_tag = find_tag(table_tag, "a", {"href": re.compile(r".+pdf-a4\.zip$")})
    pdf_a4_link = pdf_a4_tag["href"]
    archive_url = urljoin(downloads_url, pdf_a4_link)
    filename = archive_url.split("/")[-1]
    downloads_dir = BASE_DIR / "downloads"
    downloads_dir.mkdir(exist_ok=True)
    archive_path = downloads_dir / filename
    response = session.get(archive_url)
    with open(archive_path, "wb") as file:
        # Полученный ответ записывается в файл.
        file.write(response.content)
    logging.info(f"Архив был загружен и сохранён: {archive_path}")


def check_pep_results(all_pep):
    results = {}
    output = [("Статус", "Количество")]
    wrong_tatus_exist = False
    for cell in all_pep:
        if cell[2] not in EXPECTED_STATUS[cell[0]]:
            if not wrong_tatus_exist:
                logging.info("Несовпадающие статусы:")
                wrong_tatus_exist = True
            logging.info(cell[1])
            logging.info(f"Статус в карточке: {cell[2]}")
            logging.info(f"Ожидаемый статус: {EXPECTED_STATUS[cell[0]]}")
        if cell[2] not in results.keys():
            results[cell[2]] = 1
        else:
            results[cell[2]] += 1
    results["Total"] = len(all_pep)
    output = output + list(results.items())
    return output


def pep(session):
    all_pep = []
    response = get_response(session, PEP_URL)
    soup = BeautifulSoup(response.text, features="lxml")
    tables = soup.find_all(
        "table", attrs={"class": "pep-zero-table docutils align-default"}
    )
    for cells in tqdm(tables):
        for row in cells.find_all("tr"):
            status_cell = row.find("abbr")
            if status_cell is not None:
                status = status_cell.text[1:]
            else:
                status = ""
            a_tag = row.find("a")
            if a_tag:
                link = urljoin(PEP_URL, a_tag["href"])
                response = get_response(session, link)
                soup = BeautifulSoup(response.text, features="lxml")
                status_from_link = (
                    soup.find(string="Status").parent.find_next_sibling().text
                )
            else:
                link = ""
                status_from_link = ""
            if status != "" or link != "":
                all_pep.append((status, link, status_from_link))
    return check_pep_results(all_pep)


MODE_TO_FUNCTION = {
    "whats-new": whats_new,
    "latest-versions": latest_versions,
    "download": download,
    "pep": pep,
}


def main():
    configure_logging()
    logging.info("Парсер запущен!")
    arg_parser = configure_argument_parser(MODE_TO_FUNCTION.keys())
    args = arg_parser.parse_args()
    # Логируем переданные аргументы командной строки.
    logging.info(f"Аргументы командной строки: {args}")
    session = requests_cache.CachedSession()
    if args.clear_cache:
        session.cache.clear()
    parser_mode = args.mode
    results = MODE_TO_FUNCTION[parser_mode](session)
    if results is not None:
        control_output(results, args)
    # Логируем завершение работы парсера.
    logging.info("Парсер завершил работу.")


if __name__ == "__main__":
    main()
