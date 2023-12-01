import asyncio
import requests
import warnings
from enum import Enum
from datetime import date as dateType
from datetime import datetime
from dataclasses import dataclass


warnings.filterwarnings('ignore')

class Version(Enum):
    Prod = "Prod"
    Preprod = "Preprod"
    def __str__(self):
        return "Prod" if self == Version.Prod else "Preprod"

VERSION_TO_URL = {
    Version.Prod: "https://datasphere.yandex.ru",
    Version.Preprod: "https://datasphere-preprod.cloud.yandex.ru",
}

@dataclass
class VersionSpec:
    appVersion: str
    date: dateType
    revision: str

    # appVersion == '2023-11-22_r12948653'
    def __init__(self, appVersion: str):
        self.appVersion = appVersion

        buff = appVersion.split("_")

        self.date = datetime.strptime(buff[0], "%Y-%m-%d").date()
        self.revision = buff[1]

async def getVersionSpec(version: Version):
    r = requests.get(
        url = f"{VERSION_TO_URL[version]}/__core/meta",
        verify = False,
    )

    if r.status_code != 200:
        print(r.text)
        return None

    # expected {'appVersion': '2023-11-22_r12948653'}
    rBody = r.json()

    return VersionSpec(appVersion = rBody["appVersion"])


async def main():
    [prevPreprod, prevProd] = await asyncio.gather(
        getVersionSpec(Version.Preprod),
        getVersionSpec(Version.Prod),
    )

    preprodAppVersion = prevPreprod.appVersion if prevPreprod else 'NOT FOUNDED'
    prodAppVersion = prevProd.appVersion if prevProd else 'NOT FOUNDED'

    print(f"preprod: `{preprodAppVersion}`")
    print(f"prod: `{prodAppVersion}`")

    print()

    print(f"previous preprod: `{preprodAppVersion}`")
    print(f"previous prod: `{prodAppVersion}`")


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    loop.close()
