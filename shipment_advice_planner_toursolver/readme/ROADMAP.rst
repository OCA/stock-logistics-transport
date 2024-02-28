At this stage, the TourSolver task is managed by a cron which will synchronize
its status with TourSolver and get the result when it is ready.
Another approach is available using queue jobs where the sync task will be
rescheduled until it gets the optimization result.

Ideally, a webhook can be developed to be notified by toursolver when the result
is ready. He will ensure that the result is obtained as soon as possible.
