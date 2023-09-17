import random
import unittest
from datetime import date as Date
from pathlib import Path

import requests

from gingrwrapp import Client
from gingrwrapp.response_objects import (
    Animal,
    AnimalReservationIds,
    CustomerSpend,
    Icon,
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
        for i, ai in icons:
            self.assertIsInstance(i, Icon)
            self.assertIsInstance(ai.animal_id, int)
        self.assertIsInstance(icons, Icons)

    def test_get_animal(self):
        # 464 hardcoded
        animal = client.get_animal(464)
        self.assertIsInstance(animal, Animal)

    def test_get_animal_reservation_ids(self):
        # 464 hardcoded
        report_cards = client.get_animal_reservation_ids(464)
        self.assertIsInstance(report_cards, AnimalReservationIds)

    def test_get_report_card_images(self):
        # 120586 hardcoded
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

    def test_get_animal_report_card_urls(self):
        urls = client.get_animal_report_card_urls(464)
        self.assertIn("/front_end/view_report_card/id/", urls[0])

    def test_get_animal_report_card_ids(self):
        ids = client.get_animal_report_card_ids(464)
        self.assertEqual(ids[-1], 2818)

    # This is too dangerous to test all the time
    # You will wipe all images and staff would have to reupload them
    # Only uncomment and test when you know what you're doing
    # def test_clear_bulk_upload(self):
    #     client.clear_bulk_upload()

    def test_upload_image(self):
        self.fail("Not working correctly yet.")
        image = Path("test_data/1024px-Wiki_Test_Image.jpg")
        self.client.upload_image(image)
