import random
import unittest
from datetime import date as Date
from pathlib import Path

import requests

from .client import Client
from .response_objects import (
    Animal,
    AnimalReportCards,
    CustomerSpend,
    Icons,
    Reservation,
    ReservationType,
    SessionCounts,
    UnsentReportCard,
    UntaggedImage,
)

client = Client.from_env()


class ClientTestCase(unittest.TestCase):
    def test_apikey(self):
        self.assertIsNotNone(client.apikey)

    def test_get_section_counts(self):
        sc = client.get_section_counts()
        self.assertIsInstance(sc, SessionCounts)

    def test_get_reservation_types(self):
        r_types = client.get_reservation_types()
        for r in r_types:
            self.assertIsInstance(r, ReservationType)

    def test_get_reservations(self):
        reservations = client.get_reservations()
        for r in reservations:
            self.assertIsInstance(r, Reservation)

    def test_get_icons(self):
        icons = client.get_icons([1, 2, 3], [1, 2, 3])
        self.assertIsInstance(icons, Icons)

    def test_get_animal(self):
        animal = client.get_animal(464)
        self.assertIsInstance(animal, Animal)

    def test_get_animal_report_cards(self):
        report_cards = client.get_animal_report_cards(464)
        self.assertIsInstance(report_cards, AnimalReportCards)

    def test_get_report_card_images(self):
        images = client.get_report_card_images(120586)
        resp = requests.get(images[random.randint(0, len(images) - 1)])
        self.assertEqual(resp.headers["Content-Type"], "image/jpeg")

    def test_get_unsent_report_cards(self):
        unsent = client.get_unsent_report_cards()
        for rc in unsent:
            self.assertIsInstance(rc, UnsentReportCard)

    def test_get_customer_spend_by_date_range(self):
        date_from, date_to = Date(2023, 1, 1), Date(2023, 1, 31)
        spend = client.get_customer_spend_by_date_range(date_from, date_to)
        for customer in spend:
            self.assertIsInstance(customer, CustomerSpend)

    def test_get_untagged_images(self):
        untagged = client.get_untagged_images()
        for u in untagged:
            self.assertIsInstance(u, UntaggedImage)
        # What if there are no untagged images? Have to assume fail for now
        self.fail()

    def test_clear_bulk_photos(self):
        client.clear_bulk_photos()

    def test_upload_image(self):
        self.fail()
        image = Path("test_data/1024px-Wiki_Test_Image.jpg")
        self.client.upload_image(image)
