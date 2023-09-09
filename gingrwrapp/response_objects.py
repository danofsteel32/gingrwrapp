"""Return useful, documented objects rather than a dict in client responses."""

import io
import json
import re
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable


def dt_helper(x: str) -> datetime | None:
    """Convert a string in isoformat or epoch timestamp into a datetime."""

    def timestamp(_x: str) -> datetime:
        return datetime.fromtimestamp(int(_x))

    funcs: list[Callable] = [
        datetime.fromisoformat,
        timestamp,
    ]

    for f in funcs:
        try:
            return f(x)
        except Exception:
            continue
    else:
        return None


def dt_helper_raise(x: str) -> datetime:
    """Convert string to datetime or raise ValueError."""
    dt = dt_helper(x)
    if not dt:
        raise ValueError(f"Required datetime; input={x}")
    return dt


def date_helper(x: str) -> Date | None:
    """Return the date from a string."""
    try:
        return datetime.fromtimestamp(int(x)).date()
    except Exception:
        return None


def bool_helper(x: str) -> bool:
    """Convert various string representations to their actual bool value."""
    bool_map = {
        "0": False,
        "false": False,
        "False": False,
        "1": True,
        "true": True,
        "True": True,
    }
    return bool_map.get(x, False)


def int_or_none(x: Any) -> int | None:
    try:
        return int(x)
    except Exception:
        return None


@dataclass
class SessionCounts:
    daily_notices: int
    expected_today: int
    checked_in: int
    unconfirmed: int
    requested: int
    going_home_today: int

    @classmethod
    def from_json(cls, resp: dict) -> "SessionCounts":
        data = resp["data"]
        return cls(
            int(data["daily_notices"]),
            int(data["expected_today"]),
            int(data["checked_in"]),
            int(data["unconfirmed"]),
            int(data["requested"]),
            int(data["going_home_today"]),
        )


@dataclass
class ReservationType:
    id: int
    type: str
    description: str

    @classmethod
    def from_json(cls, resp: dict) -> "ReservationType":
        return cls(int(resp["id"]), resp["type"], resp["description"])


@dataclass
class CustomerSpend:
    o_id: int
    first_name: str
    last_name: str
    email: str
    customer_source: str
    customer_since: datetime | None
    last_reservation: datetime | None
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal

    @classmethod
    def from_csv(cls, row: dict) -> "CustomerSpend":
        return cls(
            int(row["id"]),
            row["first_name"],
            row["last_name"],
            row["email"],
            row["source"],
            dt_helper(row["created_at"]),
            dt_helper(row["last_reservation"]),
            Decimal(row["subtotal"]),
            Decimal(row["tax_amount"]),
            Decimal(row["total"]),
        )


@dataclass
class Reservation:
    """Everything in the reservations_by_days report."""

    # reservation details
    id: int
    cancel_stamp: datetime | None
    check_in_stamp: datetime | None
    check_out_stamp: datetime | None
    confirmed_stamp: datetime | None
    wait_list_stamp: datetime | None
    color: str  # hex encoded background color for their row on dashboard
    r_notes: str
    reservation_service_ids: list[int]
    run_name: str
    services_string: str
    standing_reservation: bool
    type: str
    type_id: int
    start_date: datetime
    starts_today: bool
    end_date: datetime
    ends_today: bool
    feeding_amount: str
    feeding_method: str
    feeding_notes: str
    feeding_time: str
    feeding_type: str
    # animal details
    a_id: int
    a_notes: str
    a_first: str
    allergies: str
    birthday: Date | None
    breed_name: str
    fixed: bool
    icons_string: str
    medicines: str
    next_immunization_expiration: Date | None
    only_appointment: bool
    # owner details
    o_id: int
    o_first: str
    o_last: str
    o_notes: str
    email: str
    cell_phone: str
    home_phone: str
    stripe_default_card: bool
    address_1: str
    address_2: str
    city: str
    state: str
    zip: str
    answer_1: str
    answer_2: str
    answer_3: str
    question_1: str
    question_2: str
    question_3: str

    @classmethod
    def from_csv(cls, row: dict) -> "Reservation":
        """Called by Client.get_reservations_csv."""
        return cls(
            id=int(row["id"]),
            cancel_stamp=dt_helper(row["cancel_stamp"]),
            check_in_stamp=dt_helper(row["check_in_stamp"]),
            check_out_stamp=dt_helper(row["check_out_stamp"]),
            confirmed_stamp=dt_helper(row["confirmed_stamp"]),
            wait_list_stamp=dt_helper(row["wait_list_stamp"]),
            color=row["color"],
            r_notes=row["r_notes"],
            reservation_service_ids=row["reservation_service_ids"],
            run_name=row["run_name"],
            services_string=row["services_string"],
            standing_reservation=bool_helper(row["standing_reservation"]),
            type=row["type"],
            type_id=int(row["type_id"]),
            start_date=dt_helper_raise(row["start_date"]),
            starts_today=bool_helper(row["starts_today"]),
            end_date=dt_helper_raise(row["end_date"]),
            ends_today=bool_helper(row["ends_today"]),
            feeding_amount=row["feeding_amount"],
            feeding_method=row["feeding_method"],
            feeding_notes=row["feeding_notes"],
            feeding_time=row["feeding_time"],
            feeding_type=row["feeding_type"],
            a_id=int(row["a_id"]),
            a_notes=row["a_notes"],
            a_first=row["a_first"],
            allergies=row["allergies"],
            birthday=date_helper(row["birthday"]),
            breed_name=row["breed_name"],
            fixed=bool_helper(row["fixed"]),
            icons_string=row["icons_string"],
            medicines=row["medicines"],
            next_immunization_expiration=date_helper(
                row["next_immunization_expiration"]
            ),
            only_appointment=bool_helper(row["only_appointment"]),
            o_id=int(row["o_id"]),
            o_first=row["o_first"],
            o_last=row["o_last"],
            o_notes=row["o_notes"],
            email=row["email"],
            cell_phone=row["cell_phone"],
            home_phone=row["home_phone"],
            stripe_default_card=bool_helper(row["stripe_default_card"]),
            address_1=row["address_1"],
            address_2=row["address_2"],
            city=row["city"],
            state=row["state"],
            zip=row["zip"],
            answer_1=row["answer_1"],
            answer_2=row["answer_2"],
            answer_3=row["answer_3"],
            question_1=row["question_1"],
            question_2=row["question_2"],
            question_3=row["question_3"],
        )


class GenderType(Enum):
    MALE = "M"
    FEMALE = "F"


@dataclass
class AnimalReservationIds:
    a_id: int
    future: list[int]
    complete: list[int]
    cancelled: list[int]
    wait_list: list[int]

    @classmethod
    def from_json(cls, animal_id: int, resp: dict) -> "AnimalReservationIds":
        return cls(
            a_id=animal_id,
            future=[int(i) for i in resp["data"]["future"]["ids"]],
            complete=[int(i) for i in resp["data"]["complete"]["ids"]],
            cancelled=[int(i) for i in resp["data"]["cancelled"]["ids"]],
            wait_list=[int(i) for i in resp["data"]["wait_list"]["ids"]],
        )


@dataclass
class Animal:
    id: int
    name: str
    gender: GenderType
    medicines: str
    allergies: str
    notes: str
    breed_name: str
    breed_id: int
    banned: bool
    image_url: str
    home_location: int

    @classmethod
    def from_html(cls, html: str) -> "Animal":
        info = cls._extract_animal_info(html)
        gender = (
            GenderType.MALE if info["gender"].upper() == "MALE" else GenderType.FEMALE
        )
        return cls(
            id=1,
            name=info["animal_name"],
            gender=gender,
            medicines=info["medicines"],
            allergies=info["allergies"],
            notes=info["a_notes"],
            breed_name=info["breed_name"],
            breed_id=int(info["breed_id"]),
            banned=bool_helper(info["banned"]),
            image_url=info["image"],
            home_location=int(info["home_location"]),
        )

    @staticmethod
    def _extract_animal_info(html: str) -> dict:
        with io.StringIO(html) as stream:
            for line in stream:
                animal = re.search("var animal = ", line)
                if animal:
                    animal_json = json.loads(line.replace(" var animal = ", "")[:-2])
                    return animal_json
        raise ValueError("Could not get animal info payload")


@dataclass(frozen=True, slots=True)
class AnimalIcon:
    icon_template_id: int | None
    icon_template_group_id: int | None
    content: str | None
    comment: str | None
    name: str | None
    title: str
    type: str  # custom || system
    fontawesome_icon_id: int
    capacity: int | None
    fontawesome_class: str

    @classmethod
    def from_json(cls, resp: dict) -> "AnimalIcon":
        return cls(
            icon_template_id=int_or_none(resp.get("color_label_template_id")),
            icon_template_group_id=int_or_none(
                resp.get("color_label_template_group_id")
            ),
            content=resp.get("content"),
            comment=resp.get("comment"),
            name=resp.get("name"),
            title=resp["title"],
            type=resp["type"],
            fontawesome_icon_id=int(resp["fontawesome_icon_id"]),
            capacity=int_or_none(resp.get("capacity")),
            fontawesome_class=resp["class"],
        )


@dataclass
class AnimalIconTemplate:
    id: int
    fontawesome_icon_id: int
    color_label_template_group_id: int | None
    title: str
    color: str
    capacity: int | None
    group_name: str | None
    checkout_alert: bool
    checkin_alert: bool
    reservation_creation_alert: bool
    reservation_details_alert: bool
    owner_details_alert: bool
    animal_details_alert: bool
    fontawesome_class: str
    location_ids: list[int] | None

    @classmethod
    def from_json(cls, resp: dict) -> "AnimalIconTemplate":
        if resp.get("location_ids"):
            location_ids = [int(x) for x in resp.get("location_ids", "").split(",")]
        else:
            location_ids = None
        return cls(
            id=int(resp["id"]),
            fontawesome_icon_id=int(resp["fontawesome_icon_id"]),
            color_label_template_group_id=int_or_none(
                resp["color_label_template_group_id"]
            ),
            title=resp["title"],
            color=resp["color"],
            capacity=int_or_none(resp["capacity"]),
            group_name=resp["group_name"],
            checkout_alert=bool_helper(resp["checkout_alert"]),
            checkin_alert=bool_helper(resp["checkin_alert"]),
            reservation_creation_alert=bool_helper(resp["reservation_creation_alert"]),
            reservation_details_alert=bool_helper(resp["reservation_details_alert"]),
            owner_details_alert=bool_helper(resp["owner_details_alert"]),
            animal_details_alert=bool_helper(resp["animal_details_alert"]),
            fontawesome_class=resp["class"],
            location_ids=location_ids,
        )


@dataclass
class Icons:
    """We don't care about the owners right now but they could be in there."""

    animal_icons: dict[int, list[AnimalIcon]]  # a_id: icons

    @classmethod
    def from_json(cls, resp: dict) -> "Icons":
        animal_icons = {}
        animals = resp["data"]["animals"]
        for a_id in animals:
            icons = [AnimalIcon.from_json(icon) for icon in animals[a_id]["icons"]]
            animal_icons[int(a_id)] = icons
        return cls(animal_icons)

    def unique_icons(self) -> set[AnimalIcon]:
        icons = set()
        for a_id in self.animal_icons:
            for i in self.animal_icons[a_id]:
                icons.add(i)
        return icons


@dataclass
class UnsentReportCard:
    a_id: int
    report_card_id: int
    num_photos: int


@dataclass
class UntaggedImage:
    file_id: int
    url: str
