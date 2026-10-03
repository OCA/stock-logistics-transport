Pull a Geotab database, including an AT&T Fleet Management federation
host, into TMS telematics. The module logs in with JSON-RPC, follows the
server returned by Authenticate, and maps LogRecord, Trip, and FillUp
feeds. Odometer values arrive in meters and are stored in kilometers.
