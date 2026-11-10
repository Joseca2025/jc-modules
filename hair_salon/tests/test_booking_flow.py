from datetime import datetime, timedelta

from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import TransactionCase, tagged

START = datetime(2030, 1, 7, 10, 0)  # lunes


@tagged('post_install', '-at_install')
class TestBookingFlow(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(
            cls.env.context, tracking_disable=True, no_reset_password=True, tz='UTC',
        ))
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Lunes',
            'tz': 'UTC',
            'attendance_ids': [Command.create({
                'name': 'Lunes', 'dayofweek': '0', 'hour_from': 8, 'hour_to': 18, 'day_period': 'morning',
            })],
        })
        cls.stylist_a = cls._user('stylist_a', 'hair_salon.group_hair_stylist')
        cls.stylist_b = cls._user('stylist_b', 'hair_salon.group_hair_stylist')
        cls.receptionist = cls._user('recepcion', 'hair_salon.group_hair_receptionist')
        cls.manager = cls._user('encargado', 'hair_salon.group_hair_manager')
        cls.employee = cls._user('otro_empleado', 'base.group_user')
        cls.combination_a = cls._combination(cls.stylist_a)
        cls.combination_b = cls._combination(cls.stylist_b)
        cls.booking_type = cls.env['resource.booking.type'].create({
            'name': 'Corte',
            'duration': 0.5,
            'resource_calendar_id': cls.calendar.id,
            'combination_rel_ids': [
                Command.create({'combination_id': cls.combination_a.id}),
                Command.create({'combination_id': cls.combination_b.id}),
            ],
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Cliente', 'email': 'cliente@example.com'})

    @classmethod
    def _user(cls, login, group):
        return cls.env['res.users'].create({
            'name': login,
            'login': login,
            'email': f'{login}@example.com',
            'groups_id': [Command.set(cls.env.ref(group).ids)],
        })

    @classmethod
    def _combination(cls, user):
        resource = cls.env['resource.resource'].create({
            'name': user.name,
            'resource_type': 'user',
            'user_id': user.id,
            'calendar_id': cls.calendar.id,
            'tz': 'UTC',
        })
        return cls.env['resource.booking.combination'].create({'resource_ids': [Command.set(resource.ids)]})

    def _booking(self, combination=None, start=START):
        return self.env['resource.booking'].create({
            'partner_ids': [Command.set(self.partner.ids)],
            'type_id': self.booking_type.id,
            'start': start,
            'combination_auto_assign': False,
            'combination_id': (combination or self.combination_a).id,
        })

    def _appointment(self, booking):
        return self.env['hair.appointment'].search([('booking_id', '=', booking.id)])

    # Flujo de estados

    def test_full_flow_records_real_times(self):
        booking = self._booking()
        self.assertEqual(booking.state, 'scheduled')
        with freeze_time(START - timedelta(minutes=5)):
            booking.action_arrive()
        with freeze_time(START):
            booking.action_progress()
        with freeze_time(START + timedelta(minutes=40)):
            booking.action_complete()
        self.assertEqual(booking.state, 'completed')
        self.assertEqual(booking.arrival_datetime, START - timedelta(minutes=5))
        self.assertEqual(booking.service_start_datetime, START)
        self.assertEqual(booking.service_end_datetime, START + timedelta(minutes=40))

    def test_start_does_not_require_confirmation(self):
        booking = self._booking()
        self.assertEqual(booking.state, 'scheduled')
        booking.action_progress()
        self.assertEqual(booking.state, 'in_progress')

    def test_invalid_transitions(self):
        booking = self._booking()
        with self.assertRaises(UserError):
            booking.action_complete()
        booking.action_progress()
        with self.assertRaises(UserError):
            booking.action_arrive()
        pending = self.env['resource.booking'].create({
            'partner_ids': [Command.set(self.partner.ids)],
            'type_id': self.booking_type.id,
        })
        self.assertEqual(pending.state, 'pending')
        with self.assertRaises(UserError):
            pending.action_progress()

    def test_no_show_only_after_start(self):
        booking = self._booking()
        with freeze_time(START - timedelta(hours=1)), self.assertRaises(UserError):
            booking.action_no_show()
        with freeze_time(START + timedelta(minutes=20)):
            booking.action_no_show()
        self.assertEqual(booking.state, 'no_show')

    def test_attendance_does_not_override_manual_state(self):
        booking = self._booking()
        booking.action_progress()
        booking.meeting_id.attendee_ids.write({'state': 'accepted'})
        self.env.flush_all()
        booking.invalidate_recordset(['state'])
        self.assertEqual(booking.state, 'in_progress')

    def test_archive_keeps_final_state(self):
        booking = self._booking()
        booking.action_progress()
        booking.action_complete()
        with freeze_time(START + timedelta(hours=2)):
            booking.action_archive()
            self.env.flush_all()
        self.assertEqual(booking.state, 'completed')

    def test_spanish_labels_and_order(self):
        selection = self.env['resource.booking']._fields['state'].selection
        self.assertEqual([value for value, _label in selection], [
            'pending', 'scheduled', 'confirmed', 'arrived', 'in_progress', 'completed', 'no_show', 'canceled',
        ])
        self.assertEqual(dict(selection)['scheduled'], 'Programado')

    # Bloqueos y reapertura

    def test_started_booking_is_locked_even_for_manager(self):
        booking = self._booking().with_user(self.manager)
        booking.action_progress()
        self.assertFalse(booking.is_modifiable)
        with self.assertRaises(UserError):
            booking.action_unschedule()
        with self.assertRaises(UserError):
            booking.action_cancel()
        with self.assertRaises(ValidationError):
            booking.meeting_id.write({'start': START + timedelta(hours=1), 'stop': START + timedelta(hours=2)})

    def test_reopen_only_manager(self):
        booking = self._booking()
        booking.action_arrive()
        booking.action_progress()
        with self.assertRaises(AccessError):
            booking.with_user(self.receptionist).action_reopen()
        booking.with_user(self.manager).action_reopen()
        self.assertEqual(booking.state, 'scheduled')
        self.assertFalse(booking.arrival_datetime)
        self.assertFalse(booking.service_start_datetime)
        self.assertTrue(booking.is_modifiable)

    # Cancelación

    def test_cancel_keeps_original_date(self):
        booking = self._booking()
        appointment = self._appointment(booking)
        self.assertEqual(appointment.appointment_start, START)
        booking.action_cancel()
        self.assertEqual(booking.state, 'canceled')
        self.assertFalse(booking.start)
        self.assertEqual(booking.canceled_start, START)
        self.assertTrue(booking.canceled_datetime)
        self.assertEqual(appointment.appointment_start, START)

    # Roles

    def test_receptionist_can_operate_same_day(self):
        booking = self._booking()
        with freeze_time(START - timedelta(hours=2)):
            self.assertFalse(booking.with_user(self.stylist_a).is_modifiable)
            as_receptionist = booking.with_user(self.receptionist)
            self.assertTrue(as_receptionist.is_modifiable)
            as_receptionist.write({'start': START + timedelta(hours=1)})
            self.assertEqual(booking.meeting_id.start, START + timedelta(hours=1))
            as_receptionist.action_arrive()
        self.assertEqual(booking.state, 'arrived')

    def test_portal_context_keeps_deadline_for_receptionist(self):
        booking = self._booking().with_user(self.receptionist).with_context(using_portal=True)
        with freeze_time(START - timedelta(hours=2)):
            self.assertFalse(booking.is_modifiable)

    def test_visibility_by_role(self):
        booking = self._booking(self.combination_a)
        appointment = self._appointment(booking)
        domain = [('id', '=', appointment.id)]
        Appointment = self.env['hair.appointment']
        self.assertEqual(Appointment.with_user(self.stylist_a).search_count(domain), 1)
        self.assertEqual(Appointment.with_user(self.stylist_b).search_count(domain), 0)
        self.assertEqual(Appointment.with_user(self.receptionist).search_count(domain), 1)
        with self.assertRaises(AccessError):
            appointment.with_user(self.stylist_b).read(['partner_id'])
        with self.assertRaises(AccessError):
            Appointment.with_user(self.employee).search_count(domain)
        Booking = self.env['resource.booking']
        booking_domain = [('id', '=', booking.id)]
        self.assertEqual(Booking.with_user(self.stylist_b).search_count(booking_domain), 0)
        self.assertEqual(Booking.with_user(self.receptionist).search_count(booking_domain), 1)

    def test_stylist_cannot_edit_appointment(self):
        appointment = self._appointment(self._booking())
        with self.assertRaises(AccessError):
            appointment.with_user(self.stylist_a).write({'name': 'Otro nombre'})

    def test_stylist_creates_exactly_one_appointment(self):
        booking = self.env['resource.booking'].with_user(self.stylist_a).create({
            'partner_ids': [Command.set(self.partner.ids)],
            'type_id': self.booking_type.id,
            'start': START,
            'combination_auto_assign': False,
            'combination_id': self.combination_a.id,
        })
        self.assertEqual(self.env['hair.appointment'].search_count([('booking_id', '=', booking.id)]), 1)

    # Calendario

    def test_calendar_buttons_and_state(self):
        booking = self._booking()
        meeting = booking.meeting_id
        self.assertEqual(meeting.booking_state, 'scheduled')
        meeting.action_calendar_arrive()
        meeting.action_calendar_start()
        meeting.action_calendar_complete()
        self.assertEqual(booking.state, 'completed')
        self.assertEqual(meeting.booking_state, 'completed')

    def test_plain_event_for_user_without_booking_group(self):
        event = self.env['calendar.event'].create({
            'name': 'Reunión',
            'start': START,
            'stop': START + timedelta(hours=1),
            'partner_ids': [Command.set(self.employee.partner_id.ids)],
        })
        event.invalidate_recordset()
        self.assertFalse(event.with_user(self.employee).booking_state)
