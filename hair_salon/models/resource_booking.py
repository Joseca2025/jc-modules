# models/resource_booking.py
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

# Reservas que esperan al cliente
HAIR_EXPECTED_STATES = ('scheduled', 'confirmed')
# Estados que maneja el salón: la asistencia del calendario no los recalcula
HAIR_MANUAL_STATES = ('arrived', 'in_progress', 'completed', 'no_show')
# Estados de cierre: ni archivar la reserva los cambia
HAIR_FINAL_STATES = ('completed', 'no_show')


class ResourceBooking(models.Model):
    _inherit = 'resource.booking'

    state = fields.Selection(
        selection_add=[
            ('pending', 'Pendiente'),
            ('scheduled', 'Programado'),
            ('confirmed', 'Confirmado'),
            ('arrived', 'Llegó'),
            ('in_progress', 'En Proceso'),
            ('completed', 'Finalizado'),
            ('no_show', 'No asistió'),
            ('canceled', 'Cancelado'),
        ],
        ondelete={
            'arrived': 'set default',
            'in_progress': 'set default',
            'completed': 'set default',
            'no_show': 'set default',
        },
    )
    arrival_datetime = fields.Datetime(string='Hora de llegada', readonly=True, copy=False, tracking=True)
    service_start_datetime = fields.Datetime(string='Inicio real', readonly=True, copy=False, tracking=True)
    service_end_datetime = fields.Datetime(string='Fin real', readonly=True, copy=False, tracking=True)
    canceled_start = fields.Datetime(
        string='Fecha original', readonly=True, copy=False,
        help='Fecha que tenía la reserva al cancelarse.',
    )
    canceled_datetime = fields.Datetime(string='Cancelada el', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        bookings = super().create(vals_list)
        # sudo: quien reserva no necesita permiso de escritura sobre las citas
        self.env['hair.appointment'].sudo().create([{
            'name': f"Cita: {booking.name or booking.display_name}",
            'booking_id': booking.id,
        } for booking in bookings])
        return bookings

    @api.depends('active', 'meeting_id.attendee_ids.state')
    def _compute_state(self):
        # _origin: en un registro nuevo de onchange, leer state aquí daría False
        manual = self.filtered(
            lambda r: r._origin.state in HAIR_FINAL_STATES
            or (r.active and r._origin.state in HAIR_MANUAL_STATES)
        )
        super(ResourceBooking, self - manual)._compute_state()

    @api.depends('is_overdue', 'state')
    @api.depends_context('uid', 'using_portal')
    def _compute_is_modifiable(self):
        super()._compute_is_modifiable()
        # Recepción reprograma citas del mismo día sin ser manager de reservas
        if not self.env.context.get('using_portal') and self.env.user.has_group(
            'hair_salon.group_hair_receptionist'
        ):
            self.is_modifiable = True
        # Una atención ya iniciada no se mueve ni para el manager: primero se reabre
        self.filtered(lambda r: r.state in HAIR_MANUAL_STATES).is_modifiable = False

    def _hair_write_state(self, allowed_states, vals):
        """Cambia de estado validando el origen.

        El contexto evita que OCA reescriba la reunión por un simple cambio de
        estado, lo que volvería a validar la disponibilidad del estilista.
        """
        invalid = self.filtered(lambda r: r.state not in allowed_states)
        if invalid:
            raise UserError(self.env._(
                'Esta acción no se puede aplicar en el estado actual de:\n\n- %s',
                '\n- '.join(invalid.mapped('display_name')),
            ))
        self.with_context(syncing_booking_ids=self.ids).write(vals)

    def action_arrive(self):
        self._hair_write_state(HAIR_EXPECTED_STATES, {
            'state': 'arrived',
            'arrival_datetime': fields.Datetime.now(),
        })

    def action_progress(self):
        # No exige "confirmado": la mayoría de clientes nunca responde la invitación
        self._hair_write_state(HAIR_EXPECTED_STATES + ('arrived',), {
            'state': 'in_progress',
            'service_start_datetime': fields.Datetime.now(),
        })

    def action_complete(self):
        self._hair_write_state(('in_progress',), {
            'state': 'completed',
            'service_end_datetime': fields.Datetime.now(),
        })

    def action_no_show(self):
        now = fields.Datetime.now()
        future = self.filtered(lambda r: r.start and r.start > now)
        if future:
            raise UserError(self.env._(
                'No se puede marcar como "No asistió" antes de la hora de la cita:\n\n- %s',
                '\n- '.join(future.mapped('display_name')),
            ))
        self._hair_write_state(HAIR_EXPECTED_STATES, {'state': 'no_show'})

    def action_reopen(self):
        """Corrige un error de operación y devuelve la reserva a su estado de agenda."""
        if not self.env.user.has_group('hair_salon.group_hair_manager'):
            raise AccessError(self.env._('Solo un encargado puede reabrir una atención.'))
        self._hair_write_state(HAIR_MANUAL_STATES, {
            'state': 'scheduled',
            'arrival_datetime': False,
            'service_start_datetime': False,
            'service_end_datetime': False,
        })
        # Programado o Confirmado lo decide la asistencia del calendario
        self.env.add_to_compute(self._fields['state'], self)

    def action_unschedule(self):
        locked = self.filtered(lambda r: r.state in HAIR_MANUAL_STATES)
        if locked:
            raise UserError(self.env._(
                'No se puede quitar de la agenda una atención ya iniciada:\n\n- %s',
                '\n- '.join(locked.mapped('display_name')),
            ))
        return super().action_unschedule()

    def action_cancel(self):
        # OCA borra la reunión y con ella la fecha: se guarda para el historial
        now = fields.Datetime.now()
        for booking in self:
            booking.with_context(syncing_booking_ids=booking.ids).write({
                'canceled_start': booking.start,
                'canceled_datetime': now,
            })
        return super().action_cancel()
