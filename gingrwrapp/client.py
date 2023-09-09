import csv
import io
import operator
import os
import pickle
import re
import tempfile
import zipfile
from datetime import date as Date
from datetime import timedelta
from pathlib import Path
from typing import Any, Iterable

import requests
from bs4 import BeautifulSoup as bs  # type: ignore
from cachetools import TTLCache, cachedmethod
from loguru import logger

from .response_objects import (
    Animal,
    AnimalReservationIds,
    CustomerSpend,
    Icons,
    Reservation,
    ReservationType,
    SessionCounts,
    UnsentReportCard,
    UntaggedImage,
)

ResponseType = requests.Response | dict | str | Iterable[dict]
"""raw response || json || html || csv rows"""

# Call this in your script to disable logging
# logger.disable("gingrwrapp")


# TODO change this up sometimes?
USER_AGENT = os.getenv(
    "USER_AGENT",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/11.1.2 Safari/605.1.15",  # noqa: E501
)
"""Not sure if matters but use it anyways."""
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
"""Raise GingrClientError after too many bad/timed out requests. Default is 3."""


class GingrClientError(Exception):
    """Catch this exception to catch all exceptions"""

    pass


class EnhancedSession(requests.Session):
    """Add timeout to every request made with the session."""

    def __init__(
        self, timeout: tuple[float, float] | float | int = (3.05, 27.0)
    ) -> None:
        self.timeout = timeout
        return super().__init__()

    def request(self, method: str | bytes, url: str, **kwargs: Any):  # type: ignore
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return super().request(method, url, **kwargs)


class Client:
    """Make authenticated requests to gingrapp.com.

    Handles session cookie and automatically gets a new cookie on expiry.
    TODO document MAX_RETRIES

    Prefer to fetch json data from the api but some data is only available in
    rendered HTML so we use BeautifulSoup to get it.

    icon_templates
    group_icons
    system_icons
    custom_icons
    """

    def __init__(
        self,
        subdomain: str,
        username: str,
        password: str,
        location: int = 1,
        timeout: int | float | tuple[float, float] = (3.05, 27.0),
    ) -> None:
        self.subdomain = subdomain
        """<subdomain>.gingrapp.com"""
        self.username = username
        self.password = password
        self.location = location
        """Multiple locations not tested yet."""
        self.timeout = timeout
        """See https://requests.readthedocs.io/en/latest/user/advanced/#timeouts"""
        self.base_url = f"https://{subdomain}.gingrapp.com"
        self.cookie_file = Path(tempfile.gettempdir()) / Path(
            f"{self.subdomain}-{self.username}.cookiefile"
        )
        """This is supposed to work on windows and unixy OS but only tested on unix"""
        self.apikey: str | None = None
        """Set on first authenticated request."""
        self._session = self._establish_session()
        self.reservation_types: Iterable[ReservationType] = TTLCache(
            maxsize=100, ttl=3600
        )
        """Will only be updated from gingr if > 3600 seconds since last update."""

    @classmethod
    def from_env(cls) -> "Client":
        subdomain = os.environ.get("GINGR_SUBDOMAIN", "")
        username = os.environ.get("GINGR_USERNAME", "")
        password = os.environ.get("GINGR_PASSWORD", "")
        if all([subdomain, username, password]):
            return cls(subdomain, username, password)
        else:
            raise GingrClientError("Login details not provided")

    @property
    def auth_url(self) -> str:
        return f"{self.base_url}/auth/login"

    @property
    def dash_url(self) -> str:
        return f"{self.base_url}/dashboard"

    def _get_session(self) -> EnhancedSession:
        session = EnhancedSession(self.timeout)
        session.headers["User-Agent"] = USER_AGENT
        return session

    def _establish_session(self) -> requests.Session:
        """
        First we try to reuse existing cookies but if that doesn't work
        we have to re-login. If no existing cookies we just login.
        """
        logger.info("Establishing session ...")

        if Path(self.cookie_file).exists():
            logger.info("Loading cookies from existing cookiefile")
            session = self._get_session()
            cookies = self.load_cookies(self.cookie_file)
            for c in cookies:
                session.cookies[c.name] = c.value

            response = session.get(self.dash_url, allow_redirects=False)
            if self._session_expired(response):
                return self._login()

            self.apikey = self._extract_window_apikey(response.text)
            logger.info("Previous session still valid")
            return session

        logger.info("No cookiefile; need to login")
        return self._login()

    def _login(self) -> EnhancedSession:
        """
        Grab csrf_token and use it along with username/password to
        login and establish a session with gingr.
        """
        session = self._get_session()
        logger.info("Making request to get csrf_token ...")
        session.get(self.auth_url)

        csrf_token = session.cookies.get("gingr_csrf_cookie_name", None)
        if not csrf_token:
            logger.critical("Unable to get csrf_token!")
            logger.critical(f"Cookies: {session.cookies.values()}")
            raise GingrClientError("Unable to get csrf_token")
        logger.info("Got csrf_token")

        login_data = {
            "identity": self.username,
            "password": self.password,
            "gingr_csrf_token": csrf_token,
        }
        logger.info(f"Attempting login as {self.username} ...")
        session.post(self.auth_url, data=login_data)

        response = session.get(self.dash_url, allow_redirects=False)
        if self._session_expired(response):
            self._log_bad_request(response)
            raise GingrClientError("Unable to login")
        logger.info("Successfully logged in")

        self.apikey = self._extract_window_apikey(response.text)
        self.save_cookies(session.cookies, self.cookie_file)

        return session

    def _session_expired(self, response: requests.Response) -> bool:
        """Returns whether gingr wants the client to re-login."""
        if response.status_code == 302:
            location = response.headers.get("location", "")
            if location == self.auth_url:
                logger.info("Session/cookies expired; need to re-login")
                return True
        return False

    def _get_from_content_type(self, resp: requests.Response) -> ResponseType:
        content_type = resp.headers["content-type"]
        if content_type == "application/csv" or content_type == '"text/csv"':
            return self._extract_csv(resp)
        elif "application/json" in content_type:
            json_resp = resp.json()
            if json_resp.get("error", False) or not json_resp.get("success", True):
                logger.critical(json_resp)
                self._log_bad_request(resp)
                raise GingrClientError("Error in json response")
            return json_resp
        elif "text/html" in content_type:
            return resp.text
        else:
            return resp

    def _extract_csv(self, response: requests.Response) -> Iterable[dict]:
        if zipfile.is_zipfile(io.BytesIO(response.content)):
            return csv.DictReader(self.unzip(response.content))
        csv_part = response.text.split("<!DOCTYPE html>")[0]
        return csv.DictReader(io.StringIO(csv_part))

    def post(self, url: str, data: dict) -> ResponseType:
        """Wraps POST request and return result based on Content-Type header."""
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                resp = self._session.post(url, data=data)
                logger.info(f"POST {url} {data} {resp.status_code} {resp.reason}")
            except requests.exceptions.RequestException as exc:
                logger.exception(exc)
                attempts += 1
                continue
            if self._session_expired(resp):
                self._session = self._login()
            return self._get_from_content_type(resp)

        logger.critical("Too many bad requests")
        raise GingrClientError("Too many bad requests")

    def get(self, url: str, params: dict | None = None) -> ResponseType:
        """Wraps GET request and return result based on Content-Type header."""
        attempts = 0
        while attempts < MAX_RETRIES:
            try:
                resp = self._session.get(url, params=params)
                logger.info(f"GET {url} {params} {resp.status_code} {resp.reason}")
            except requests.exceptions.RequestException as exc:
                logger.exception(exc)
                attempts += 1
                continue

            if self._session_expired(resp):
                self._session = self._login()
            return self._get_from_content_type(resp)

        logger.critical("Too many bad requests")
        raise GingrClientError("Too many bad requests")

    def get_section_counts(self) -> SessionCounts:
        """Return summary of animals checked_in, going_home, etc."""
        url = f"{self.dash_url}/section_counts"
        resp = self.get(url)
        if isinstance(resp, dict):
            return SessionCounts.from_json(resp)
        logger.critical(resp)
        raise GingrClientError("get_section_counts() resp not json")

    @cachedmethod(operator.attrgetter("reservation_types"))
    def get_reservation_types(self) -> Iterable[ReservationType]:
        """These are cached with an hour TTL."""
        url = f"{self.base_url}/api/v1/reservation_types_by_booking_category"
        params = {
            "key": self.apikey,
            "booking_category_id": "",
            "location_id": self.location,
            "fetch_only_other_location": 0,
        }
        resp = self.get(url, params)
        try:
            r_types = resp.get("reservation_types", [])  # type: ignore
            return [ReservationType.from_json(r_type) for r_type in r_types]
        except Exception as exc:
            logger.critical(resp)
            logger.exception(exc)
            raise GingrClientError("get_reservation_types()") from exc

    def get_reservations(
        self, date: Date | None = None, days_ahead: int = 1
    ) -> Iterable[Reservation]:
        """Return all reservations from the date plus days_ahead.

        date defaults to today if not provided
        """
        date_from = date if date else Date.today()
        date_to = date_from + timedelta(days=days_ahead)
        data = {
            "date_from": date_from.strftime("%m/%d/%Y"),
            "date_to": date_to.strftime("%m/%d/%Y"),
            "type_ids[]": [r.id for r in self.get_reservation_types()],
            "cancelled": "true",
            "csv": "true",
        }
        url = f"{self.base_url}/reports/reservations_by_days"
        resp = self.post(url, data=data)
        try:
            return [Reservation.from_csv(row) for row in resp]  # type: ignore
        except Exception as exc:
            logger.critical(resp)
            logger.exception(exc)
            raise GingrClientError("get_reservations()") from exc

    def get_icons(
        self, animal_ids: Iterable[int], owner_ids: Iterable[int] | None = None
    ) -> Icons:
        """Return all icons for the animals and owners.

        owner_ids is optional
        """
        url = f"{self.dash_url}/get_icons"
        data = {
            "animal_ids": str(animal_ids),
            "owner_ids": str(owner_ids) if owner_ids else "[]",
            "key": self.apikey,
        }
        # lol that `get_icons` is a POST.
        resp = self.post(url, data)
        try:
            return Icons.from_json(resp)  # type: ignore
        except Exception as exc:
            logger.critical(resp)
            logger.exception(exc)
            raise GingrClientError("get_icons()") from exc

    def get_animal(self, animal_id: int) -> Animal:
        """Return animal info from it's profile page."""
        url = f"{self.base_url}/animals/view/id/{animal_id}"
        resp = self.get(url)
        try:
            return Animal.from_html(resp)  # type: ignore
        except Exception as exc:
            logger.critical(resp)
            logger.exception(exc)
            raise GingrClientError("get_animal()") from exc

    def get_animal_reservation_ids(self, animal_id: int) -> AnimalReservationIds:
        """Return ids of all future, complete, cancelled, wait listed reservations."""
        url = f"{self.base_url}/api/v1/reservation_stats"
        params = {"type": "animal", "id": animal_id, "key": self.apikey}
        resp = self.get(url, params)
        try:
            return AnimalReservationIds.from_json(animal_id, resp)  # type: ignore
        except Exception as exc:
            logger.critical(resp)
            logger.exception(exc)
            raise GingrClientError("get_animal()") from exc

    def get_report_card_images(self, report_card_id: int) -> Iterable[str]:
        """Return image urls associated with the report card."""
        url = f"{self.base_url}/front_end_v1/get_report_card_details_v1"
        data = {"report_card_id": report_card_id}
        resp = self.post(url, data)
        try:
            return [
                file["file_location"]  # type: ignore[index]
                for file in resp["data"]["report_card"]["files"]  # type: ignore[index]
            ]
        except Exception as exc:
            logger.critical(resp)
            logger.exception(exc)
            raise GingrClientError("get_animal()") from exc

    def get_customer_spend_by_date_range(
        self, date_from: Date, date_to: Date
    ) -> Iterable[CustomerSpend]:
        """Return customer and amount they have spent over the date range."""
        url = f"{self.base_url}/reports/customer_spend"
        data = {
            "date_from": date_from.strftime("%m/%d/%Y"),
            "date_to": date_to.strftime("%m/%d/%Y"),
            "payment_amount_min": "1.00",
            "csv": "true",
        }
        resp = self.post(url, data)
        try:
            return [CustomerSpend.from_csv(row) for row in resp]  # type: ignore
        except Exception as exc:
            raise GingrClientError("get_customer_spend_by_date_range()") from exc

    def get_unsent_report_cards(self) -> Iterable[UnsentReportCard]:
        """Return unsent report cards and number of photos in each one."""
        url = f"{self.base_url}/report_cards"
        resp = self.get(url)

        unsent_div = bs(resp, "lxml").find("div", {"id": "unsent"})
        tbody = unsent_div.find("tbody")

        ret = []
        for row in tbody.find_all("tr"):  # type: ignore
            cols = row.find_all("td")
            report_card_id = int(
                cols[0].find("a", {"title": "Edit"})["href"].split("/")[-1]
            )
            a_id = int(cols[1].find("a")["href"].split("/")[-1])
            num_files = int(cols[4].text)
            ret.append(UnsentReportCard(a_id, report_card_id, num_files))
        return ret

    def get_untagged_images(self) -> Iterable[UntaggedImage]:
        """Return all images currently in bulk_upload."""
        ret: list[UntaggedImage] = []

        url = f"{self.base_url}/report_cards/bulk_upload"
        resp = self.get(url)

        tbody = bs(resp, "lxml").find("tbody")
        if not tbody:
            return ret

        for row in tbody.find_all("tr"):  # type: ignore
            cols = row.find_all("td")
            try:
                url = cols[0].find("img")["src"].replace("https ", "https:")
                # <select multiple="" name="files[2275938][file][]">
                file_thing = cols[1].find("select")["name"]
                file_id = int(file_thing.replace("files[", "").replace("][file][]", ""))
                ret.append((UntaggedImage(file_id, url)))
            except TypeError:
                continue
        return ret

    def upload_image(self, image: str | Path) -> None:
        """Upload an image to the bulk_upload area."""
        raise NotImplementedError
        # url = "https://us-central1-gingr-file-uploads-198700.cloudfunctions.net/sign-upload-url"
        # file_name = image if isinstance(image, str) else image.name
        # data = {
        #     "key": self.apikey,
        #     "bucket_name": "gingr-app-user-uploads",
        #     "file_name": file_name,
        #     "type": "image/jpeg",
        # }
        # resp = self.post(url, data=data)
        # google_url = resp["data"]
        # with open(image, "rb") as file:
        #     files = {file_name: file}
        #     with requests.Session() as session:
        #         resp = session.options(google_url)
        #         resp = session.put(google_url, files=files)
        #         print(resp.headers)
        #         print(resp.content)

    def clear_bulk_upload(self) -> None:
        """Delete all images in the bulk_upload section."""
        for image in self.get_untagged_images():
            self.delete_image(image.file_id)

    def tag_images(self, tags: Iterable) -> None:
        """Assign tags to images in bulk_upload."""
        raise NotImplementedError
        # url = f"{self.base_url}/report_cards/bulk_update"
        # This is not hard to implement just haven't done it yet
        # tags should be just

    def delete_image(self, file_id: int) -> None:
        """Delete an image from the report cards.

        I assume this removes the image from all report cards referencing it.
        """
        url = f"{self.base_url}/report_cards/delete_file/id/{file_id}"
        response = self.get(url)
        if response:
            logger.info(f"Deleted file {file_id}")

    @staticmethod
    def _log_bad_request(response: requests.Response) -> None:
        logger.warning(f"Response: {response.status_code} {response.reason}")
        logger.warning(f"Headers: {response.headers}")

    @staticmethod
    def _extract_window_apikey(html: str) -> str:
        """Found by scrolling through view source."""
        with io.StringIO(html) as stream:
            for line in stream:
                apikey = re.search("window.apiKey = ", line)
                if apikey:
                    return line.split(" = ")[-1].replace("'", "").strip().strip(";")
        raise GingrClientError("Could not get apikey")

    @staticmethod
    def unzip(content: bytes) -> Iterable[str]:
        """Return first file in the zip archive."""
        with io.BytesIO(content) as stream:
            with zipfile.ZipFile(stream) as zipped:
                zip_contents = zipped.namelist()
                if len(zip_contents) == 1:
                    with zipped.open(zip_contents[0]) as target_file:
                        return io.StringIO(target_file.read().decode("utf-8"))
                else:
                    # I've never seen gingr send more than one file in the zip.
                    raise GingrClientError("Not sure which file to read in zip.")

    @staticmethod
    def save_cookies(cookies: Any, filename: Path) -> None:
        """Pickle the cookies in /tmp."""
        with open(filename, "wb") as f:
            pickle.dump(cookies, f)
            logger.info("Saved cookiefile")

    @staticmethod
    def load_cookies(filename: Path) -> Any:
        """UnPickle the cookies in /tmp."""
        with open(filename, "rb") as f:
            cookies = pickle.load(f)
        return cookies
