from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    booking_state = fields.Selection(
        selection='_selection_booking_state',
        string='Estado de Reserva',
        compute='_compute_booking_state',
        compute_sudo=True,
    )

    @api.model
    def _selection_booking_state(self):
        return self.env['resource.booking']._fields['state']._description_selection(self.env)

    @api.depends('resource_booking_ids', 'resource_booking_ids.state')
    def _compute_booking_state(self):
        for event in self:
            booking = event.resource_booking_ids[:1]
            event.booking_state = booking.state if booking else False

    def action_calendar_arrive(self):
        self.resource_booking_ids.action_arrive()

    def action_calendar_start(self):
        self.resource_booking_ids.action_progress()

    def action_calendar_complete(self):
        self.resource_booking_ids.action_complete()

    def action_calendar_no_show(self):
        self.resource_booking_ids.action_no_show()
