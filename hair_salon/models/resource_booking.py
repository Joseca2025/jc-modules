# models/resource_booking.py
from odoo import models, api, fields

import logging

_logger = logging.getLogger(__name__)

class ResourceBooking(models.Model):
    _inherit = 'resource.booking'

    state = fields.Selection(
        [
            ("pending", "Pendiente"),
            ("scheduled", "Programado"),
            ('confirmed', 'Confirmado'),
            ('in_progress', 'En Proceso'),
            ('completed', 'Finalizado'),
            ("canceled", "Cancelado"),
        ],
        compute="_compute_state",
        store=True,
        default="pending",
        index=True,
        tracking=True,
        help=(
            "Pending: No meeting scheduled.\n"
            "Scheduled: The requester has not confirmed attendance yet.\n"
            "Confirmed: Meeting scheduled, and requester attendance confirmed.\n"
            "Canceled: Meeting removed, booking archived."
        ),
    )

    @api.model_create_multi
    def create(self, vals_list):
        bookings = super(ResourceBooking, self).create(vals_list)
        for booking in bookings:
            self.env['hair.appointment'].create({
                'name': f"Cita: {booking.name or booking.display_name}",
                'booking_id': booking.id,
            })
        return bookings

    @api.depends("active", "meeting_id.attendee_ids.state")
    def _compute_state(self):
        # Los estados manuales no se recalculan (salvo si se archiva la reserva)
        manual = self.filtered(
            lambda r: r.active and r.state in ('in_progress', 'completed')
        )
        super(ResourceBooking, self - manual)._compute_state()

    def action_progress(self):
        self.write({'state': 'in_progress'})

    def action_complete(self):
        self.write({'state': 'completed'})