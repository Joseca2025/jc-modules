# -*- coding: utf-8 -*-
# from odoo import http


# class HairSalon(http.Controller):
#     @http.route('/hair_salon/hair_salon', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/hair_salon/hair_salon/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('hair_salon.listing', {
#             'root': '/hair_salon/hair_salon',
#             'objects': http.request.env['hair_salon.hair_salon'].search([]),
#         })

#     @http.route('/hair_salon/hair_salon/objects/<model("hair_salon.hair_salon"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('hair_salon.object', {
#             'object': obj
#         })

