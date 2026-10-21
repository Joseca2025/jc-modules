from odoo import fields, models


class HairAppointment(models.Model):
    _name = 'hair.appointment'
    _description = 'Hair Salon Appointment'

    name = fields.Char(string='Appointment', required=True)

    # Enlace principal con la Reserva de Recurso
    booking_id = fields.Many2one('resource.booking', string='Resource Booking', required=True, ondelete='cascade')

    # Datos obtenidos desde la Reserva de Recurso (resource.booking)
    partner_id = fields.Many2one(string='Customer', related='booking_id.partner_id', store=True, readonly=True)
    resource_ids = fields.Many2many(string='Resources / Stylists',
                                    related='booking_id.combination_id.resource_ids', readonly=True)
    state_booking = fields.Selection(string='Booking State', related='booking_id.state', store=True, readonly=True)

    # Enlace indirecto al Evento de Calendario (que resource.booking crea automáticamente)
    calendar_event_id = fields.Many2one('calendar.event', string='Calendar Event',
                                        related='booking_id.meeting_id', store=True, readonly=True)

    # Datos de Calendario a través del evento generado
    calendar_event_name = fields.Char(string='Calendar Event Name', related='calendar_event_id.name', store=True,
                                      readonly=True)
    calendar_event_date_start = fields.Datetime(string='Calendar Event Start', related='calendar_event_id.start',
                                                store=True, readonly=True)
    calendar_event_date_end = fields.Datetime(string='Calendar Event End', related='calendar_event_id.stop', store=True,
                                              readonly=True)
    calendar_event_duration = fields.Float(string='Calendar Event Duration', related='calendar_event_id.duration',
                                           store=True, readonly=True)
    calendar_event_organizer = fields.Char(string='Calendar Event Organizer', related='calendar_event_id.user_id.name',
                                           store=True, readonly=True)
    calendar_event_description = fields.Html(string='Calendar Event Description',
                                             related='calendar_event_id.description', store=True, readonly=True)