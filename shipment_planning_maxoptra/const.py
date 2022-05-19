# Copyright 2022 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl)
# TODO: Move to settings on res.company or warehouse?
MAXOPTRA_ADDRESS_FORMAT = (
    "%(street)s, %(city)s, %(state_code)s, %(zip)s, %(country_name)s"
)
MAXOPTRA_COLUMN_NAMES = [
    "orderReference",
    "date",
    "distributionCentreName",
    "customerLocationName",
    "contactNumber",
    "contactEmail",
    "customerLocationAddress",
    "partnerKey",
]

MAXOPTRA_DATE_FORMAT = "%d/%m/%Y"
MAXOPTRA_DATETIME_FORMAT = "%d/%m/%Y %H:%M:%S"
