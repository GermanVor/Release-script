import trackerClient
import datasphereClient
import asyncio
import arcanumClient

STR = "previous prod: `"
def getProdVersionSpecFromTicketDescription(releaseTicketDescription: str):
    idx = releaseTicketDescription.find(STR)
    if idx == -1:
        return None

    idx += len(STR)
    endIdx = releaseTicketDescription.find("`", idx)

    appVersion = releaseTicketDescription[idx:endIdx]

    return datasphereClient.VersionSpec(appVersion)


async def main():
    arcanumToken = arcanumClient.getToken()
    trackerToken = trackerClient.getToken()

    lastReleaseTicket = await trackerClient.getLastReleaseTicket(trackerToken)

    if lastReleaseTicket.status == "closed":
        print(f"Release - https://st.yandex-team.ru/{lastReleaseTicket.id} is closed. Do you want update it ?")
        ans = input(""""y" to continue, * to stop: """)

        if ans != "y":
            return

    prevReleaseVersionSpec = getProdVersionSpecFromTicketDescription(lastReleaseTicket.description)

    if prevReleaseVersionSpec == None:
        print("It is not possible to restore the previous release revision")
        return

    [preprod, prod] = await asyncio.gather(
        datasphereClient.getVersionSpec(datasphereClient.Version.Preprod),
        datasphereClient.getVersionSpec(datasphereClient.Version.Prod),
    )

    startRevision = preprod.revision #
    endRevision = prevReleaseVersionSpec.revision #

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
        comment = ""
        comment += f"preprod: `{preprod.appVersion}`\n"
        comment += f"prod: `{prod.appVersion}`"

        await trackerClient.addComment(trackerToken, lastReleaseTicket.id, comment)

        print(f"Ticket has been successfully updated: https://st.yandex-team.ru/{lastReleaseTicket.id}")
    else :
        print(f"Ticket was NOT updated: https://st.yandex-team.ru/{lastReleaseTicket.id}")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()