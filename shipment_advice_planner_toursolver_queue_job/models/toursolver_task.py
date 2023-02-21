# Copyright 2023 ACSONE SA/NV
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models
from odoo.exceptions import UserError

from odoo.addons.queue_job.exception import RetryableJobError


class ToursolverTask(models.Model):

    _inherit = "toursolver.task"

    def _toursolver_process(self):
        self.ensure_one()
        send_request_job = self.delayable()._toursolver_send_request()
        check_status_job = self.delayable()._toursolver_check_status()
        get_result_job = self.delayable()._toursolver_get_result()
        send_request_job.on_done(check_status_job.on_done(get_result_job)).delay()
        self.env.user.notify_info(
            message=_(
                "TourSolver task '%(task)s' is being processed in background."
                " You will be notify once it's done"
            )
            % dict(task=self.name),
            sticky=False,
        )

    def _toursolver_check_status(self):
        res = super()._toursolver_check_status()
        if not self.task_id:
            raise UserError(_("TourSolver taskID is null"))
        if self.state == "in_progress":
            raise RetryableJobError(
                "The result is not ready yet", seconds=5, ignore_retry=True
            )
        return res

    def _toursolver_get_result(self):
        res = super()._toursolver_get_result()
        if self.state == "done":
            self.create_uid.notify_success(
                message=_(
                    "TourSolver task '%(task)s' process finished with success."
                    " Shipment advices are created."
                )
                % dict(task=self.name),
                sticky=False,
            )
        return res

    def _toursolver_notify_error(self, error_msg):
        res = super()._toursolver_notify_error(error_msg)
        self.create_uid.notify_danger(
            message=_(
                "TourSolver task '%(task)s' process failed."
                " Please check the task for more details."
            )
            % dict(task=self.name),
            sticky=False,
        )
        return res
