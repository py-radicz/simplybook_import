from traceback import print_exception
import logging
import urllib3
import sys

from requests import Session
import pandas as pd
import tomli

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
cfg = tomli.load(open("settings.toml", "rb"))

formatter = logging.Formatter("%(asctime)s %(name)s [%(levelname)s]: %(message)s")

# log all also to stdout
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
sh.setLevel(logging.DEBUG)

# all logging messages to debug file
dfh = logging.FileHandler(cfg.get("Files").get("debug_log"))
dfh.setFormatter(formatter)
dfh.setLevel(logging.DEBUG)

# errors to special file
efh = logging.FileHandler(cfg.get("Files").get("failed_bookings_log"))
efh.setFormatter(formatter)
efh.setLevel(logging.WARNING)

# unhandled exceptions to log files as well
def _excepthook(*args):
    logging.getLogger("simplybook.import").error(
        "An unhandled exception occurred.", exc_info=(args)
    )
    print_exception(*args)


sys.excepthook = _excepthook

LOGGER = logging.getLogger("simplybook.import")
LOGGER.setLevel(logging.DEBUG)
LOGGER.addHandler(sh)
LOGGER.addHandler(dfh)
LOGGER.addHandler(efh)


class SimplyBook:
    def __init__(self):
        self.usr = cfg.get("Account").get("user")
        self.pwd = cfg.get("Account").get("password")
        domain = cfg.get("Account").get("domain")
        self.company = domain.split(".")[0]
        self.api = f"https://user-api-v2.{domain}/admin"
        self.input = pd.read_csv(cfg.get("Files").get("import_csv"))

    def __enter__(self):
        LOGGER.debug("Authenticating..")
        self.session = Session()
        self.session.verify = False
        self.session.headers.update({"Content-Type": "application/json"})

        payload = {"company": self.company, "login": self.usr, "password": self.pwd}
        r = self.session.post(f"{self.api}/auth", json=payload).json()

        if not "token" in r:
            LOGGER.error(f"Authentication failed - {r.get('message')}")
            sys.exit()

        self.token = r.get("token")
        self.session.headers.update(
            {"X-Company-Login": self.company, "X-Token": self.token}
        )
        LOGGER.debug("Authentication successfull")
        return self

    def __exit__(self, *exc):
        LOGGER.debug("Logging out..")
        self.session.post(f"{self.api}/auth/logout", json={"auth_token": self.token})
        self.session.close()

    def get(self, entity):
        r = self.session.get(f"{self.api}/{entity}").json()
        data = r.get("data")
        page = 1
        LOGGER.debug(f"Fetching {entity}... paginator: {page}")

        while len(data) != r.get("metadata").get("items_count"):
            page += 1
            r = self.session.get(f"{self.api}/{entity}?page={page}")
            data = data + r.get("data")
            LOGGER.debug(f"Fetching {entity}... paginator: {page}")

        if len(data) != r.get("metadata").get("items_count"):
            LOGGER.error(f"failed to obtain correct item counts on {entity}")
            sys.exit()

        return data

    def init(self):
        self.clients = pd.DataFrame(self.get("clients"))
        self.providers = pd.DataFrame(self.get("providers"))
        self.services = pd.DataFrame(self.get("services"))

    def import_bookings(self):
        self.init()

        for i, row in enumerate(self.input.itertuples(index=False), start=1):
            sid = self.services[self.services.name == row.service]
            pid = self.providers[self.providers.name == row.provider]

            if sid.empty:
                LOGGER.error(
                    f"Unable to match service with name {row.service}, CSV row {i} import skipped"
                )
                continue

            if pid.empty:
                LOGGER.error(
                    f"Unable to match provider with name {row.provider}, CSV row {i} import skipped"
                )
                continue

            sid, pid = int(sid.id.item()), int(pid.id.item())
            cid = self.clients[self.clients.email == row.email]

            if cid.empty:
                LOGGER.debug("Creating client", row.name)
                cid = self.create_client(row)
            else:
                cid = int(cid.id.item())

            payload = {
                "start_datetime": row.start,
                "provider_id": pid,
                "service_id": sid,
                "client_id": cid,
            }
            r = self.create_booking(payload)

            if "bookings" in r:
                LOGGER.debug(f"Successfully created booking from CSV row {i}")
            else:
                LOGGER.error(
                    f'Failed to create booking from CSV row {i} - {r.get("data")}'
                )

    def create_client(self, row):
        payload = {"name": row.name, "email": row.email, "phone": row.phone}
        r = self.session.post(f"{self.api}/clients", json=payload).json()
        return r.get("id")

    def create_booking(self, payload):
        r = self.session.post(f"{self.api}/bookings", json=payload)
        return r.json()


if __name__ == "__main__":
    with SimplyBook() as sb:
        sb.import_bookings()
