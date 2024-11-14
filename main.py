import warnings
import asyncio
import trackerClient
import datasphereClient
import arcanumClient
import datetime
import argparse

warnings.filterwarnings('ignore')

parser = argparse.ArgumentParser()
parser.add_argument("--topRevision", help="by default is trunk", default = "trunk")
parser.add_argument("--trackerToken", help="You can pass token with env.TRACKER_TOKEN also")
parser.add_argument("--arcanumToken", help="You can pass token with env.ARCANUM_TOKEN also")

args = parser.parse_args()

async def main():
    trackerToken = str(args.trackerToken) if args.trackerToken else trackerClient.getToken()
    arcanumToken = str(args.arcanumToken) if args.arcanumToken else arcanumClient.getToken()

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

    topRevision = str(args.topRevision) # trunk
    endRevision = prodVersion.revision # prodVersion.revision

    if topRevision == "trunk":
        svnTrunkRevision = await arcanumClient.getSvnRevision(
            token = arcanumToken,
            revision = topRevision,
        )
        topRevision = f"r{svnTrunkRevision}"

    endSvnPreprodRevision = await arcanumClient.getSvnRevision(
        token = arcanumToken,
        revision = endRevision,
    )

    issueList = await arcanumClient.getIssueList(
        token = arcanumToken,
        topRevision = topRevision,
        endSvnRevision = endSvnPreprodRevision,
    )
    issueListInfo = trackerClient.IssueListInfo(
        topRevision = topRevision,
        issueList = issueList,
        endRevision = endRevision
    )

    prevReleaseIssueId = lastReleaseTicket.id if lastReleaseTicket else "<Сouldn't find Previous Release Ticket>"

    releaseTicketId = await trackerClient.createReleaseTicket(
        token = trackerToken,
        prevReleaseInfo = trackerClient.ReleaseInfo(
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

    return releaseTicketId


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
loop.close()