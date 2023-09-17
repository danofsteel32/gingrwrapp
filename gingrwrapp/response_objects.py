"""Return useful, documented objects rather than a dict in client responses."""

import io
import json
import re
from dataclasses import dataclass
from datetime import date as Date
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Generator


def clean_not_applicable(x: str) -> str:
    """Stupid that they didn't have it be an empty string or null."""
    case = {
        "<p>n/a</p>",
        "<p>na</p>",
        "<p>no</p>",
        "<p>none</p>",
        "<p>no&nbsp;</p>",
        "<p>no!&nbsp;</p>",
        "na",
    }
    if x.lower().strip() in case:
        return ""
    return x


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
    name: str
    color: str
    enabled: bool
    single_day: bool
    convert_to: int | None

    @classmethod
    def from_json(cls, resp: dict) -> "ReservationType":
        return cls(
            int(resp["id"]),
            resp["name"].strip(),
            resp["color"],
            bool_helper(resp["status"]),
            bool_helper(resp["single_day"]),
            int_or_none(resp["convert_to"]),
        )


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
    last_name: str
    gender: GenderType
    medicines: str
    allergies: str
    notes: str
    grooming_notes: str
    breed_name: str
    breed_id: int
    banned: bool
    image_url: str
    home_location: int
    profile_creation: Date
    species_id: int
    species_name: str
    emergency_contact_name: str
    emergency_contact_phone: str
    vet_name: str
    vet_phone: str

    @classmethod
    def from_html(cls, html: str) -> "Animal":
        info = cls._extract_animal_info(html)
        gender = (
            GenderType.MALE if info["gender"].upper() == "MALE" else GenderType.FEMALE
        )
        return cls(
            id=1,
            name=info["animal_name"],
            last_name=info["o_last"],
            gender=gender,
            medicines=info["medicines"],
            allergies=clean_not_applicable(info["allergies"]),
            notes=info["a_notes"],
            grooming_notes=info["grooming_notes"],
            breed_name=info["breed_name"],
            breed_id=int(info["breed_id"]),
            banned=bool_helper(info["banned"]),
            image_url=info["image"],
            home_location=int(info["home_location"]),
            profile_creation=dt_helper_raise(info["animal_created_at"]).date(),
            species_id=int(info["species_id"]),
            species_name=info["species_name"],
            emergency_contact_name=info["emergency_contact_name"],
            emergency_contact_phone=info["emergency_contact_phone"],
            vet_name=info["vet_name"],
            vet_phone=info["vet_phone"],
        )

    @staticmethod
    def _extract_animal_info(html: str) -> dict:
        with io.StringIO(html) as stream:
            for line in stream:
                animal = re.search("var animal = ", line)
                if animal:
                    animal_json = json.loads(line.replace(" var animal = ", "")[:-2])
                    # print(json.dumps(animal_json, indent=2))
                    return animal_json
        raise ValueError("Could not get animal info payload")


@dataclass(frozen=True, slots=True)
class CustomAnimalIcon:
    """Extends from a template by adding animal specific fields."""

    icon_id: int
    animal_id: int
    content: str | None
    comment: str | None

    @classmethod
    def from_json(cls, resp: dict) -> "AnimalIcon":
        return cls(
            icon_id=int(resp.get("color_label_template_id")),  # type: ignore[arg-type]
            animal_id=int(resp.get("animal_id")),  # type: ignore[arg-type]
            content=resp.get("content"),
            comment=resp.get("comment"),
        )


@dataclass(frozen=True, slots=True)
class SystemAnimalIcon:
    """Built into gingr and does not have a corresponding template."""

    icon_id: int
    animal_id: int
    enabled: bool
    color: str
    secondary_color: str | None
    title: str
    fontawesome_icon_id: int
    fontawesome_class: str
    comment: str | None
    content: str | None

    @classmethod
    def from_json(cls, resp: dict, animal_id: int) -> "AnimalIcon":
        return cls(
            icon_id=int(resp["id"]),
            animal_id=animal_id,
            enabled=bool_helper(resp["status"]),
            color=resp["color"],
            secondary_color=resp["secondary_color"],
            title=resp["title"],
            fontawesome_icon_id=int(resp["fontawesome_icon_id"]),
            fontawesome_class=resp["class"],
            comment=resp.get("comment"),
            content=resp.get("content"),
        )

    def to_template(self) -> "Icon":
        return Icon(
            id=self.icon_id,
            fontawesome_icon_id=self.fontawesome_icon_id,
            fontawesome_class=self.fontawesome_class,
            title=self.title,
            color=self.color,
            capacity=None,
            group_name=None,
            secondary_color=self.secondary_color,
            type="system",
        )


@dataclass(frozen=True, slots=True)
class Icon:
    """Template that all instances of the icon build off.

    icon_templates->animal_templates {
        "id": "20",
        "fontawesome_icon_id": "100",
        "class": "fa fa-asterisk",
        "title": "Animal Notes",
        "color": "#171515",
        "capacity": null,
        "group_name": null,
    }
    """

    id: int
    fontawesome_icon_id: int
    fontawesome_class: str
    title: str
    color: str
    capacity: int | None
    group_name: str | None
    secondary_color: str | None = None
    type: str = "custom"

    @classmethod
    def from_json(cls, resp: dict) -> "Icon":
        return cls(
            id=int(resp["id"]),
            fontawesome_icon_id=int(resp["fontawesome_icon_id"]),
            fontawesome_class=resp["class"],
            title=resp["title"],
            color=resp["color"],
            capacity=int_or_none(resp.get("capacity")),
            group_name=resp.get("group_name"),
        )


AnimalIcon = CustomAnimalIcon | SystemAnimalIcon  # Type alias


@dataclass
class Icons:
    """Provides both icon templates and animal specific instances of the templates."""

    templates: dict[int, Icon]  # icon_id: icon
    animal_icons: dict[int, list[AnimalIcon]]  # a_id: icons

    @classmethod
    def from_json(cls, resp: dict) -> "Icons":
        templates = {}
        for template in resp["icon_templates"]["animal_templates"]:
            icon_t = Icon.from_json(template)
            templates[icon_t.id] = icon_t

        animal_icons: dict[int, list[AnimalIcon]] = {}
        animals = resp["data"]["animals"]
        for a_id_str in animals:
            a_id = int(a_id_str)
            animal_icons[a_id] = []
            for icon in animals[a_id_str]["icons"]:
                if icon["type"] == "system":
                    system_icon = SystemAnimalIcon.from_json(icon, a_id)
                    if system_icon.icon_id not in templates:
                        templates[system_icon.icon_id] = system_icon.to_template()  # type: ignore[union-attr]  # noqa: E501
                    animal_icons[a_id].append(system_icon)
                else:
                    custom_icon = CustomAnimalIcon.from_json(icon)
                    animal_icons[a_id].append(custom_icon)
        return cls(templates, animal_icons)

    def __iter__(self) -> Generator[tuple[Icon, AnimalIcon], None, None]:
        for a_id in self.animal_icons:
            for animal_icon in self.animal_icons[a_id]:
                yield self.templates[animal_icon.icon_id], animal_icon


@dataclass
class UnsentReportCard:
    a_id: int
    report_card_id: int
    num_photos: int


@dataclass
class UntaggedImage:
    file_id: int
    url: str
