import requests
import datetime
import datasphereClient
import asyncio

CHECK_LIST_ITEMS = [
    {
        "text": "Обновить дату в заголовке тикета",
        "checked": True,
        "checklistItemType": "standard",
    },
    {
        "text": "Прикрепить прошлый релизный тикет",
        "checked": True,
        "checklistItemType": "standard",
    },
    {
        "text": "Указать прошлые версии preprod и prod",
        "checked": True,
        "checklistItemType": "standard",
    },
    {
        "text": "Прикрепить тикеты попавшие в релиз",
        "checked": True,
        "checklistItemType": "standard",
    },
    {
        "text": "В комментах добавлять ссылки на сборки из сборочного цеха (пример смотри в комментах к релизу https://nda.ya.ru/t/gGY7Tdjv6sGbda)",
        "checked": False,
        "checklistItemType": "standard",
    },
    {
        "text": "Для сборки deploy to preprod указать текущую версию после деплоя (узнать её можно из https://datasphere-preprod.cloud.yandex.ru/__core/meta)",
        "checked": False,
        "checklistItemType": "standard",
    },
    {
        "text": "Для сборки deploy to prod указать текущую версию после деплоя (узнать её можно из https://datasphere.yandex.ru/__core/meta)",
        "checked": False,
        "checklistItemType": "standard",
    },
    {
        "text": "После выкатки в прод необходимо закрыть все связанные тикеты, а затем закрыть релизный тикет",
        "checked": False,
        "checklistItemType": "standard",
    }
]


def getToken():
    print("I need your OAuth-Token for Tracker")
    print("Take it please from https://oauth.yandex-team.ru/authorize?response_type=token&client_id=5f671d781aca402ab7460fde4050267b")
    print("and paste. (If link does not work please check docs https://docs.yandex-team.ru/cloud/tracker/concepts/access)")
    return input('Token: ')


async def getPrevReleaseTicketIssueId(token: str):
    r = requests.post(
        url = "https://st-api.yandex-team.ru/v2/issues/_search?expand=transitions",
        headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
        },
        json = {
            "filter": {
                "queue": "CLOUDFRONT",
                "components": ["112480"],
                "boards": [{"id": "25958"}],
                "finished": "true()",
                "summary": "Релиз datasphere-u",
            },
            "order": "-updated",
            # "perPage": 1 per Page does not work
        },
    )

    rJson = r.json()
    if rJson and rJson[0]:
        return rJson[0]["key"]

    return None


async def createReleaseTicket(
        token: str,
        prevReleaseIssueId: str,
        preprodVersion: datasphereClient.VersionSpec,
        prodVersion: datasphereClient.VersionSpec,
        issueList: list[str],
):
    now = datetime.datetime.now()
    dateStr = f"{now.day}.{now.month}.{now.year}"

    summary = f"Релиз datasphere-ui {dateStr}"

    description = f"previous release: {prevReleaseIssueId}\n"
    description += f"preprod: {preprodVersion.appVersion}\n"
    description += f"prod: {prodVersion.appVersion}\n"
    description += "\n---\n"
    description += "Release Tasks:\n"

    for issueId in issueList:
        description += f"{issueId}\n"

    r = requests.post(
        url = "https://st-api.yandex-team.ru/v2/issues/",
        headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
        },
        json = {
            "queue": {
                "id": '3096',
                "key": 'CLOUDFRONT',
            },
            "summary": summary,
            "description": description,
            "type": "task",
            "priority": "normal",
            "followers": ["telegine", "zzman", "revenkov-k", "sergeyzolotov"],
            "components": ["datasphere"],
            "boards": [{"id": "25958"}],
            "checklistItems": CHECK_LIST_ITEMS,
            "unique": summary,
        },
    )

    if r.status_code != 201:
        print(r.text)

        if r.status_code == 409:
            print(f"Ticket with name <{summary}> Was already created. Try find it and update manually")

        return None

    return str(r.json()["key"])


async def main():
    token = getToken()
    issueId = await getPrevReleaseTicketIssueId(token)
    print(f"Previous Release - https://st.yandex-team.ru/{issueId}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
