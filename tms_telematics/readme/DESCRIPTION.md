Import live positions, odometer readings, and fuel fills from a telematics
provider. Provider modules only log in and translate their payload. This
module stores the reading once, links the device to a Fleet vehicle, writes
the Fleet odometer when the value changes or the ignition turns off, and
copies departure and arrival readings onto the open trip.
