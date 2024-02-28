In the shipment planner you will see a new option added to the planning methods.
If you select TourSolver, a TourSolver task per warehouse will be created for
the pickings you want to plan.

The task will pass through different states by a dedicated cron and at the end
of the process will create shipment advices according the returned result from
TourSolver.
