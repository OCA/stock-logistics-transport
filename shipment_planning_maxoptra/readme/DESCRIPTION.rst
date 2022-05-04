This module allows to use Shipment Plannings to generate a CSV to be imported
into Maxoptra for delivery planning.

Once auto scheduling is done, it allows to import the result from a CSV
generated on Maxoptra to create batch picking per vehicle to do the deliveries.

The wizard also also to reschedule picking operation if the warehouse
Outgoing Shipments are using "2 steps".

Time selected in the wizard will be stating point for scheduling pickings in delivery
locations

* Wizard should handle pick planning in serial(actual implementation) or in parallel.
  Example:
  If we have to schedule following pickings and the start time is 6.00 AM with 15 mins duration:

    PICK1 (Shelf 1 > Output)
    PICK2 (Shelf 1 > Output)
    PICK3 (Shelf 2 > Output)
    PICK4 (Shelf 2 > Output)

  With parallel planning:

      PICK1: 6.00 AM -> BATCH1
      PICK2: 6.15 AM -> BATCH1
      PICK3: 6.00 AM -> BATCH2
      PICK4: 6.15 AM -> BATCH2
