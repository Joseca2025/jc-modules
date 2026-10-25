from odoo import models, fields, api

class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    booking_state = fields.Selection([
        ('pending', 'Pendiente'),
        ('scheduled', 'Programado'),
        ('confirmed', 'Confirmado'),
        ('in_progress', 'En Proceso'),
        ('completed', 'Finalizado'),
        ('canceled', 'Cancelado'),
    ], string='Estado de Reserva', compute='_compute_booking_state', inverse='_inverse_booking_state')

    @api.depends('resource_booking_ids', 'resource_booking_ids.state')
    def _compute_booking_state(self):
        for event in self:
            booking = event.resource_booking_ids[:1]
            event.booking_state = booking.state if booking else 'pending'

    def _inverse_booking_state(self):
        """Permite que si el statusbar interactúa, traspase el cambio a la reserva"""
        for event in self:
            if event.resource_booking_ids:
                event.resource_booking_ids.write({'state': event.booking_state})

    def action_calendar_start(self):
        for event in self:
            for booking in event.resource_booking_ids:
                booking.action_progress()
        # Forzamos la recarga de la vista actual para que el botón desaparezca y el statusbar avance
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_calendar_complete(self):
        for event in self:
            for booking in event.resource_booking_ids:
                booking.action_complete()
        # Forzamos la recarga de la vista actual
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }