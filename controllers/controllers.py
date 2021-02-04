# -*- coding: utf-8 -*-
from odoo import http

# class Amgl(http.Controller):
#     @http.route('/amgl/amgl/', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/amgl/amgl/objects/', auth='public')
#     def list(self, **kw):
#         return http.request.render('amgl.listing', {
#             'root': '/amgl/amgl',
#             'objects': http.request.env['amgl.amgl'].search([]),
#         })

#     @http.route('/amgl/amgl/objects/<model("amgl.amgl"):obj>/', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('amgl.object', {
#             'object': obj
#         })