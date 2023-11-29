import warnings
import asyncio
import trackerClient
import datasphereClient
import arcanumClient
import datetime

warnings.filterwarnings('ignore')

async def main():
    trackerToken = trackerClient.getToken()

    lastReleaseTicket = await trackerClient.getLastReleaseTicket(trackerToken)

    if lastReleaseTicket and lastReleaseTicket.status != "closed":
        print(f"Previous Release Ticket https://st.yandex-team.ru/{lastReleaseTicket.id} is not closed")
        print("Before create new one please close previous")
        return

    [preprodVersion, prodVersion] = await asyncio.gather(
        datasphereClient.getVersionSpec(datasphereClient.Version.Preprod),
        datasphereClient.getVersionSpec(datasphereClient.Version.Prod),
    )

    if preprodVersion == None:
        print("Preprod revision not founded")
        return

    if prodVersion == None:
        print("Prod revision not founded")
        return

    startRevision = "trunk"
    endRevision = prodVersion.revision

    arcanumToken = arcanumClient.getToken()

    endSvnPreprodRevision = await arcanumClient.getSvnRevision(
        token = arcanumToken,
        revision = endRevision,
    )

    issueList = await arcanumClient.getIssueList(
        token = arcanumToken,
        startRevision = startRevision,
        endSvnRevision = endSvnPreprodRevision,
    )
    issueListInfo = trackerClient.IssueListInfo(
        startRevision = startRevision,
        issueList = issueList,
        endRevision = endRevision
    )

    prevReleaseIssueId = lastReleaseTicket.id if lastReleaseTicket else "<Сouldn't find Previous Release Ticket>"

    releaseTicketId = await trackerClient.createReleaseTicket(
        token = trackerToken,
        prevReleaseInfo = trackerClient.PrevReleaseInfo(
            releaseIssueId = prevReleaseIssueId,
            preprodVersion = preprodVersion,
            prodVersion = prodVersion,
        ),
        issueListInfo = issueListInfo,
    )

    if releaseTicketId == None:
        print("Something wrong. Ticket was not created")
        return

    print(f"Ticket has been successfully created: https://st.yandex-team.ru/{releaseTicketId}")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()