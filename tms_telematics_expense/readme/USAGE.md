1. Match the telematics device to a vehicle, and set that vehicle's driver.
2. Import a fuel fill. Odoo creates a fuel expense for the driver, at the
   odometer reading of the fill.
3. The amount is the receipt sent with the fill. When the provider sends
   liters only, the amount is the liters times the fuel product cost.
4. The existing fuel allocation splits that amount across the trips whose
   odometer readings fall between this fill and the previous fill of the same
   vehicle.
5. Open the fill reading to see the expense.
