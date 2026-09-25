from odoo import api, fields, models

class HairAppointment(models.Model):
    _name = 'hair.appointment'
    _description = 'Hair Salon Appointment'

    name = fields.Char(string='Name', required=True)
    id_res_partner = fields.Many2one('res.partner', string='Customer', required=True)
    id_calendar_event = fields.Many2one('calendar.event', string='Calendar Event', required=True)
    id_resourcer_booking = fields.Many2one('resource.booking', string='Resource Booking', required=True)
    id_sale_order = fields.Many2one('sale.order', string='Sale Order', required=True)
    id_hr_employee = fields.Many2one('hr.employee', string='Employee', required=True)


