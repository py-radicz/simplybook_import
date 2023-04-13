import urllib3
import sys

from requests import Session
import pandas as pd

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class SimplyBook:
    def __init__(self, usr, pwd, domain):
        self.usr, self.pwd = usr, pwd
        self.company = domain.split(".")[0]
        self.api = f"https://user-api-v2.{domain}/admin"

    def __enter__(self):
        print("Authenticating..")
        self.session = Session()
        self.session.verify = False
        self.session.headers.update({"Content-Type": "application/json"})

        payload = {"company": self.company, "login": self.usr, "password": self.pwd}
        r = self.session.post(f"{self.api}/auth", json=payload).json()

        if not "token" in r:
            print(f"Authentication failed - {r.get('message')}")
            sys.exit()

        self.token = r.get("token")
        self.session.headers.update(
            {"X-Company-Login": self.company, "X-Token": self.token}
        )
        print("Authentication successfull")
        return self

    def __exit__(self, *exc):
        print("Logging out..")
        self.session.post(f"{self.api}/auth/logout", json={"auth_token": self.token})

    def get(self, entity):
        r = self.session.get(f"{self.api}/{entity}").json()
        data = r.get("data")
        page = 1
        print(f"Fetching {entity}... paginator: {page}")

        while len(data) != r.get("metadata").get("items_count"):
            page += 1
            r = self.session.get(f"{self.api}/{entity}?page={page}")
            data = data + r.get("data")
            print(f"Fetching {entity}... paginator: {page}")

        assert len(data) == r.get("metadata").get("items_count"), "invalid item count"
        return data

    def init(self):
        self.clients = pd.DataFrame(self.get("clients"))
        self.providers = pd.DataFrame(self.get("providers"))
        self.services = pd.DataFrame(self.get("services"))

    def import_bookings(self, filename):
        self.init()
        self.input = pd.read_csv(filename)

        for row in self.input.itertuples(index=False):
            sid = self.services[self.services.name == row.service]
            pid = self.providers[self.providers.name == row.provider]

            if sid.empty:
                print(f"Unable to match service with name {row.service}")
                continue

            if pid.empty:
                print(f"Unable to match provider with name {row.provider}")
                continue

            sid, pid = int(sid.id.item()), int(pid.id.item())
            cid = self.clients[self.clients.email == row.email]

            if cid.empty:
                self.create_client(row)
                pass
            else:
                cid = int(cid.id.item())

    def create_client(self, row):
        payload = {"name": row.name, "email": row.email, "phone": row.phone}
        print("Creating new client", payload)
        r = self.session.post(f"{self.api}/clients", json=payload)
        print(r.json())


if __name__ == "__main__":
    with SimplyBook("ig@notando.is", "Radim", "regtestig.secure.simplybook.it") as sb:
        sb.import_bookings("bookings.csv")
