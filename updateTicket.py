import trackerClient
import datasphereClient
import asyncio
import arcanumClient

async def main():
    arcanumToken = arcanumClient.getToken()
    trackerToken = trackerClient.getToken()

    lastReleaseTicket = await trackerClient.getLastReleaseTicket(trackerToken)

    if lastReleaseTicket.status == "closed":
        print(f"Release - https://st.yandex-team.ru/{lastReleaseTicket.id} is closed. Do you want update it ?")
        ans = input(""""y" to continue, * to stop: """)

        if ans != "y":
            return

    [preprod, prod] = await asyncio.gather(
        datasphereClient.getVersionSpec(datasphereClient.Version.Preprod),
        datasphereClient.getVersionSpec(datasphereClient.Version.Prod),
    )

    if preprod.appVersion == prod.appVersion:
        print(f"Preprod and Prod revisions are the same {prod.appVersion}. Nothing to update")
        return

    startRevision = preprod.revision #
    endRevision = prod.revision #

    svnProdRevision = await arcanumClient.getSvnRevision(
        token = arcanumToken,
        revision = endRevision,
    )

    issueList = await arcanumClient.getIssueList(
        token = arcanumToken,
        startRevision = startRevision,
        endSvnRevision = svnProdRevision,
    )

    issueListInfo = trackerClient.IssueListInfo(
        startRevision = startRevision,
        issueList = issueList,
        endRevision = endRevision
    )

    newIssueListDescription = trackerClient.getIssueListDescription(issueListInfo)

    idx = lastReleaseTicket.description.find("Release Tasks:")

    if idx == -1:
        print("""Something wrong with description of Release. There is no substring - "Release Tasks:".""")
        return

    prevIssueListDescription = lastReleaseTicket.description[idx:]

    newDescription = lastReleaseTicket.description.replace(
        prevIssueListDescription,
        newIssueListDescription
    )

    isOk = await trackerClient.updateReleaseTicket(trackerToken, lastReleaseTicket.id, newDescription)

    if isOk:
        print(f"Ticket has been successfully updated: https://st.yandex-team.ru/{lastReleaseTicket.id}")
    else :
        print(f"Ticket was NOT updated: https://st.yandex-team.ru/{lastReleaseTicket.id}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()