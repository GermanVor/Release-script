import requests
from ordered_set import OrderedSet
import asyncio
import datasphereClient
import os
import dotenv
import datetime
import trackerClient


# A* {'message': 'some str\n\nREVIEW: 4985974', 'author': 'zzman', 'path': 'data-ui/cloud-datasphere', 'revision': 'e1229509ee24311db8c245106b0b11d82155cd37', 'svnRevision': 12899475, 'date': 1700043192000}

def getToken():
    dotenv.load_dotenv()

    token = os.environ.get("ARCANUM_TOKEN")

    if token == None:
        print("I need your OAuth-Token for Arcanum")
        print("Take it please from https://a.yandex-team.ru/oauth/token (field access_token)")
        print("and paste. (If link does not work please check docs https://docs.yandex-team.ru/arcanum/communication/public-api)")

        token = input("Token: ")
        dotenv.set_key(".env", "ARCANUM_TOKEN", token, quote_mode='always', export=False, encoding='utf-8')
        print("")


    return token


async def getCommit(revision: int, token: str):
    r = requests.get(
        url = f"https://arcanum.yandex.net/api/v1/repos/arc_vcs/commits/r{revision}",
        verify = False,
        headers = {
            "Accept": "application/json",
            "Authorization": f"OAuth {token}",
        },
        params = {
            "fields": "issues,id",
            "diff_mode": 'tree_aware_content',
        },
    )

    if r.status_code != 200:
        print(f"getCommit for {revision} something wrond: {r.text}")
        return None

    # r.json() == {'data': {'issues': ['CLOUDFRONT-12345'], 'id': 'c06bf0c9976c883a1203ad1eb38f118c48337d10'}}
    return r.json()["data"]


# commit from getCommit
def getCloudfrontIssueList(commit):
    issueList = []

    for issue in commit["issues"]:
        if "CLOUDFRONT-" in issue:
            issueList.append(issue)

    return issueList

async def getSvnRevision(token: str, revision: str):
    r = requests.get(
        url = "https://arcanum.yandex.net/api/v1/repos/arc_vcs/tree/history/data-ui/cloud-datasphere/",
        verify = False,
        headers = {
            "Accept": "application/json",
            "Authorization": f"OAuth {token}",
        },
        params = {
            "from": revision,
            "limit": 1
        }
    )

    # r.json() == {'data': {
    #   'data': [A*],
    #   'next': {'path': 'data-ui/cloud-datasphere', 'from': '1ded0e365cca3b3f6f3839dcedf90e01b5123dfb'}
    # }},
    respBody = r.json()["data"]
    return int(respBody["data"][0]["svnRevision"])

# TODO create some class for A*

REVIEW_SRT = "REVIEW: "
REVIEW_SRT_LEN = len(REVIEW_SRT)
# repoInfo == A*
def getPRId(repoInfo):
    message = str(repoInfo["message"])
    idx = str.rfind(message, REVIEW_SRT)

    return message[idx + REVIEW_SRT_LEN:]


# repoInfo == A*
def getPRName(repoInfo):
    message = str(repoInfo["message"])
    idx = str.find(message, '\n\n')

    return message[0:idx]


# TODO return some class instead str list
async def getIssueList(
    token: str,
    startRevision: str,
    endSvnRevision: int,
):
    letI = 0

    issueIdSet: OrderedSet[str] = OrderedSet([])

    nextFrom = startRevision
    whileFlag = True

    while whileFlag:
        letI += 1

        r = requests.get(
            url = "https://arcanum.yandex.net/api/v1/repos/arc_vcs/tree/history/data-ui/cloud-datasphere/",
            verify = False,
            headers = {
                "Accept": "application/json",
                "Authorization": f"OAuth {token}",
            },
            params = {
                "from": nextFrom,
                "limit": 10
            }
        )

        if r.status_code != 200:
            print(r.text)
            break

        respBody = r.json()["data"]
        nextFrom = respBody["next"]["from"]

        commitSvnRevisionList = []

        for value in respBody["data"]:
            commitSvnRevision = value["svnRevision"]

            if commitSvnRevision == endSvnRevision:
                whileFlag = False
                break

            commitSvnRevisionList.append(commitSvnRevision)

        commitList = await asyncio.gather(
            *[getCommit(commitSvnRevision, token) for commitSvnRevision in commitSvnRevisionList]
        )

        for commit in commitList:
            if commit is not None:
                issueList = getCloudfrontIssueList(commit)

                if len(issueList) == 0:
                    issueIdSet.add(f"[{getPRName(value)}](https://a.yandex-team.ru/review/{getPRId(value)}) (no linked CLOUDFRONT Ticket)")
                else:
                    issueIdSet |= OrderedSet(issueList)

    return list(issueIdSet)


async def main(version = datasphereClient.Version.Prod):
    prodVersion = await datasphereClient.getVersionSpec(version)

    if prodVersion == None:
        print(f"Datasphere {version} Version not founded")
        return

    token = getToken()

    startRevision = "trunk" # trunk
    endRevision = prodVersion.revision #

    if startRevision == "trunk":
        svnTrunkRevision = await getSvnRevision(
            token = token,
            revision = startRevision,
        )
        startRevision = f"r{svnTrunkRevision}"

    svnPreprodRevision = await getSvnRevision(
        token = token,
        revision = endRevision,
    )

    issueList = await getIssueList(
        token = token,
        startRevision = startRevision,
        endSvnRevision = svnPreprodRevision,
    )

    issueListInfo = trackerClient.IssueListInfo(
        startRevision = startRevision,
        issueList = issueList,
        endRevision = endRevision
    )

    print(trackerClient.getIssueListDescription(issueListInfo))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
