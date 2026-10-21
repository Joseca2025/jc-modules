# models/resource_booking.py
from odoo import models, api, fields

class ResourceBooking(models.Model):
    _inherit = 'resource.booking'


    @api.model_create_multi
    def create(self, vals_list):
        # 1. Se crea la reserva de recursos normalmente
        bookings = super(ResourceBooking, self).create(vals_list)

        # 2. Por cada reserva creada, generamos automáticamente la Cita en Hair Salon
        for booking in bookings:
            self.env['hair.appointment'].create({
                'name': f"Cita: {booking.name or booking.display_name}",
                'booking_id': booking.id, # Asigna la reserva creada
            })

        return bookings