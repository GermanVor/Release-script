import warnings
import asyncio
import trackerClient
import datasphereClient
import arcanumClient

warnings.filterwarnings('ignore')

async def main():
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

    arcanumToken = arcanumClient.getToken()

    svnPreprodRevision = await arcanumClient.getSvnRevision(
        revision = preprodVersion.revision,
        token = arcanumToken,
    )

    issueList = await arcanumClient.getIssueList(
        endSvnRevision = svnPreprodRevision,
        token = arcanumToken,
    )

    trackerToken = trackerClient.getToken()
    lastReleaseTicket = await trackerClient.getLastReleaseTicket(trackerToken)

    if lastReleaseTicket and lastReleaseTicket.status != "closed":
        print(f"Previous Release Ticket https://st.yandex-team.ru/{lastReleaseTicket.id} is not closed")
        print("Before create new one please close previous")
        return

    prevReleaseIssueId = lastReleaseTicket.id if lastReleaseTicket else "<Сouldn't find Previous Release Ticket>"

    releaseTicketId = await trackerClient.createReleaseTicket(
        token = trackerToken,
        prevReleaseIssueId = prevReleaseIssueId,
        preprodVersion = preprodVersion,
        prodVersion = prodVersion,
        issueList = issueList
    )

    if releaseTicketId == None:
        print("Something wrong. Ticket was not created")
        return

    print(f"Ticket has been successfully created: https://st.yandex-team.ru/{releaseTicketId}")


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()