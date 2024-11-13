import requests
import datetime
import datasphereClient
import asyncio
import dotenv
import os
from dataclasses import dataclass
from typing import List

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
    dotenv.load_dotenv()

    token = os.environ.get("TRACKER_TOKEN")

    if token == None:
        print("I need your OAuth-Token for Tracker")
        print("Take it please from https://oauth.yandex-team.ru/authorize?response_type=token&client_id=5f671d781aca402ab7460fde4050267b")
        print("and paste. (If link does not work please check docs https://docs.yandex-team.ru/cloud/tracker/concepts/access)")

        token = input("Token: ")
        dotenv.set_key(".env", "TRACKER_TOKEN", token, quote_mode='always', export=False, encoding='utf-8')
        print("")

    return token


@dataclass
class Ticket:
    id: str
    status: str # "closed" | "open"
    description: str

async def getLastReleaseTicket(token: str):
    r = requests.post(
        url = "https://st-api.yandex-team.ru/v2/issues/_search?expand=transitions",
        headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
        },
        params = {
            "perPage": 1
        },
        json = {
            "filter": {
                "queue": "CLOUDFRONT",
                "components": ["112480"],
                "boards": [{"id": "25958"}],
                # "finished": "true()",
                "summary": "Релиз datasphere-ui",
            },
            "order": "-created",
        },
    )

    rJson = r.json()
    if (r.status_code != 200) or (not rJson) or (not rJson[0]):
        print(f"getLastReleaseTicket something wrond: {r.text}")
        return

    ticket = rJson[0]

    return Ticket(
        id = ticket["key"],
        status = ticket["status"]["key"],
        description = ticket["description"]
    )


async def updateReleaseTicket(token: str, issueId: str, description: str):
    r = requests.patch(
        url = f"https://st-api.yandex-team.ru/v2/issues/{issueId}",
        headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
        },
        json = {
            "description": description
        },
    )

    if r.status_code != 200:
        print(f"updateReleaseTicket something wrond: {r.text}")
        return False

    return True

async def addComment(token: str, issueId: str, comment: str):
    return requests.post(
        url = f"https://st-api.yandex-team.ru/v2/issues/{issueId}/comments",
        headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
        },
        json = {
            "text": comment
        },
    )


@dataclass
class ReleaseInfo:
    releaseIssueId: str
    preprodVersion: datasphereClient.VersionSpec
    prodVersion: datasphereClient.VersionSpec


@dataclass
class IssueListInfo:
    startSign: str
    issueList: List[str]
    endSign: str

    def __init__(self, topRevision: str, issueList: List[str], endRevision: str):
        self.startSign = f"`{topRevision}`"
        self.issueList = issueList
        self.endSign = f"`{endRevision}`"


ISSUE_LIST_PREFIX = "Release Tasks:"
def getIssueListDescription(issueListInfo: IssueListInfo):
    description = f"{ISSUE_LIST_PREFIX}\n\n"

    description += f"{issueListInfo.startSign}\n\n"
    for issueId in issueListInfo.issueList:
        description += f"{issueId}\n"
    description += f"\n{issueListInfo.endSign}"

    return description


PREVIOUS_PROD_PREFIX = "previous prod: `"
PREVIOUS_PROD_ENDING = "`"

async def createReleaseTicket(
    token: str,
    prevReleaseInfo: ReleaseInfo,
    issueListInfo: IssueListInfo,
):
    summary = f"Релиз datasphere-ui {datetime.datetime.now().strftime('%d.%m.%y')}"

    description  = f"previous release: {prevReleaseInfo.releaseIssueId}\n"

    description += f"previous preprod: `{prevReleaseInfo.preprodVersion.appVersion}`\n"
    description += f"{PREVIOUS_PROD_PREFIX}{prevReleaseInfo.prodVersion.appVersion}{PREVIOUS_PROD_ENDING}\n"

    description += "\n---\n"

    description += getIssueListDescription(issueListInfo)

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
            # "unique": summary,
        },
    )

    if r.status_code != 201:
        print(r.text)

        if r.status_code == 409:
            print(f"Ticket with name <{summary}> Was already created. Try find it and update manually")

        return None

    return str(r.json()["key"])


async def addTeamCityComment(token: str, issueId: str):
    text = "TeamCity Layout:\n"

    text += "```\n"
    text += "Build Application Docker - \n\n"
    text += "Build VM Image - \n\n"
    text += "Move by hopper - \n\n"
    text += "Deploy to Preprod - https://teamcity.aw.cloud.yandex.net/buildConfiguration/Console_Datasphere_ArcDeployToPreprod#all-projects\n\n\n"
    text += "Deploy to Prod - https://teamcity.aw.cloud.yandex.net/buildConfiguration/Console_Datasphere_ArcDeployToProd#all-projects\n\n"
    text += "```"

    return requests.post(
        url = f"https://st-api.yandex-team.ru//v2/issues/{issueId}/comments",
        headers = {
            "Authorization": f"OAuth {token}",
            "Accept": "application/json",
        },
        json = {
            "text": text
        },
    )


async def main():
    token = getToken()
    lastReleaseTicket = await getLastReleaseTicket(token)

    print(f"previous release: {lastReleaseTicket.id}\n")
    print(f"Previous Release - https://st.yandex-team.ru/{lastReleaseTicket.id}, status - {lastReleaseTicket.status}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
