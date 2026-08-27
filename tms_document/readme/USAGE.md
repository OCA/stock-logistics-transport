## Creating a document

Documents can be created from the *Documents* menu under *TMS > Documents*, or
directly from a driver or vehicle form using the *Documents* tab. Click
*Create* and fill in:

- **Document type**: e.g. driver license, vehicle insurance, inspection.
- **Number / reference**: the reference printed on the document.
- **Holder**: the TMS resource the document belongs to (a driver or a vehicle).
- **Expiry date**: used to compute the validity state.
- **Critical**: mark the document as critical to enforce it on trip start.

When uploading a file from the *Documents* tab of a holder form, the document
is automatically linked to that holder and the file is attached to the
holder's chatter.

Once saved, the document appears read-only in the *Documents* tab of its
holder's form, so all documents of a driver or vehicle are visible in one
place.

## Validity states

The document state is computed from its expiry date and the configured
horizon (see *Configure*):

- **Valid** — the expiry date is further away than the horizon.
- **Expiring** — the expiry date falls within the horizon.
- **Expired** — the expiry date is in the past.

## Blocking trip start

When a trip is started, all documents of its driver and vehicle are checked.
If any **critical** document is **expired**, a user error is raised and the
trip cannot be started until the document is renewed, its expiry date is
corrected, or it is no longer flagged critical.
