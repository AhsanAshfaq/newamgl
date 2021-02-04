# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, ValidationError
from odoo import _


class Dashboard(models.Model):
    _name = 'amgl.dashboard'
    _auto = False

    @api.multi
    def view_record(self):
        """Return a Window Action to view the Sales Order form"""
        self.ensure_one()
        view_id = self.env.ref('amgl.customer_form').id
        return {
            'name': 'View Record',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[view_id, "form"]],
            'res_model': 'amgl.customer',
            'res_id': self.id,
            'target': 'current',
            'flags': {'form': {'action_buttons': False, 'options': {'edit': False}}},
            'context': {},
        }

    @api.multi
    def edit_record(self):
        """Return a Window Action to view the Sales Order form"""
        self.ensure_one()
        view_id = self.env.ref('amgl.customer_form').id
        return {
            'name': 'Edit Record',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[view_id, "form"]],
            'res_model': 'amgl.customer',
            'res_id': self.id,
            'target': 'current',
            'flags':  {'initial_mode': 'edit','options': {'create': False}},
            'context': {},
        }

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'dashboard')
        self._cr.execute("""
                CREATE or REPLACE VIEW amgl_dashboard AS (

                    SELECT 
                        row_number() OVER () AS id,
                        c.first_name AS first_name,
                        c.last_name AS last_name,
                        c.account_type AS account_type,
                        c.account_number AS account_number,
                        c.custodian_id AS custodian_id,
                        (select name from amgl_products where id = ol.products) AS product,
                        ol.quantity AS quantity,
                        (CASE
                        WHEN (select weight_unit from amgl_products where id = ol.products) = 'oz'
                               THEN
                            (select weight_per_piece from public.amgl_products where id = ol.products) * ol.quantity::float
                        WHEN (select weight_unit from amgl_products where id = ol.products) = 'gram'
                               THEN
                            ((select weight_per_piece from public.amgl_products where id = ol.products) / 28.34952) * ol.quantity::float
                        WHEN (select weight_unit from amgl_products where id = ol.products) = 'pounds'
                               THEN
                            ((select weight_per_piece from amgl_products where id = ol.products) * 16) * ol.quantity::float
                        WHEN (select weight_unit from amgl_products where id = ol.products) = 'kg'
                               THEN
                            ((select weight_per_piece from amgl_products where id = ol.products) / 0.02834952) * ol.quantity::float
                        ELSE 0.0
                        END) AS total_weight,
                        ol.state AS state
                        FROM amgl_order_line AS ol
                        INNER JOIN amgl_customer AS c ON c.id = ol.customer_id
                )""")

    name = fields.Char()
    first_name = fields.Char(string="First Name")
    last_name = fields.Char(string="Last Name")
    account_type = fields.Char(string="Account Type")
    account_number = fields.Char(string="Account Number")
    custodian_id = fields.Integer(string="Custodian")
    product = fields.Char(string="Product")
    quantity = fields.Float(string="Quantity")
    total_weight = fields.Float(string="Total Weight")
    state = fields.Selection([('expecting', 'Expecting'), ('pending', 'Pending'),
                              ('completed', 'Completed'), ('waiting', 'Waiting For Approval')],
                             'Status', default='expecting')
    pending = fields.Boolean(string="Pending", default=True)


