* Importation of scheduling from Maxoptra is not supported if the warehouse
  uses Outgoing Shipments in 3 steps.
* Column names in CSV generated on Maxoptra can differ from the columns used
  by the wizard. (e.g. Rescheduling of Delivery Operations is based on
  "Scheduled arrival time" which must be present in CSV)
* Wizard should handle pick planning in serial(actual implementation) or in parallel.
  Example:
  If we have to schedule following pickings and the start time is 6.00 AM with 15 mins duration:

    PICK1 (Shelf 1 > Output)
    PICK2 (Shelf 1 > Output)
    PICK3 (Shelf 2 > Output)
    PICK4 (Shelf 2 > Output)

  We could either have a serial planning (actual implementation):

      PICK1: 6.00 AM
      PICK2: 6.15 AM
      PICK3: 6.30 AM
      PICK4: 6.45 AM

  Or a parallel planning:

      PICK1: 6.00 AM
      PICK2: 6.15 AM
      PICK3: 6.00 AM
      PICK4: 6.15 AM
