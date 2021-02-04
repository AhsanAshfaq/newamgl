# -*- coding: utf-8 -*-

from odoo import models, fields, api, tools
from odoo.exceptions import UserError, ValidationError
from odoo import _


class NewAccounts(models.Model):
    _name = 'amgl.new_accounts'
    _auto = False
    _order = 'date_opened desc'
    _rec_name = 'customer_name'

    @api.multi
    def add_deposit(self,context={}):
        context = context or {}
        self.ensure_one()
        view_id = self.env.ref('amgl.customer_form').id
        customer_id = int(context.get('customer_id'))
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            "views": [[view_id, "form"]],
            'res_model': 'amgl.customer',
            'res_id': customer_id,
            'target': 'current',
            'flags':  {'initial_mode': 'edit','options': {'create': False}},
            'context': {},
        }

    @api.model_cr
    def init(self):
        tools.drop_view_if_exists(self._cr, 'new_accounts')
        self._cr.execute("""
                CREATE or REPLACE VIEW amgl_new_accounts AS (

                    SELECT 
                        row_number() OVER () AS id,
                        C.ID AS CUSTOMER_ID
                        ,(
                            SELECT NAME
                            FROM AMGL_CUSTODIAN
                            WHERE ID = C.CUSTODIAN_ID
                            ) AS CUSTODIAN
                        ,CONCAT (
                            C.FIRST_NAME
                            ,' '
                            ,C.LAST_NAME
                            ) AS CUSTOMER_NAME
                        ,C.ACCOUNT_NUMBER
                        ,C.ACCOUNT_TYPE
                        ,C.DATE_OPENED
                        ,COUNT(OL.ID) AS NUMBER_OF_ORDERLINES
                    FROM AMGL_CUSTOMER C
                    LEFT JOIN AMGL_ORDER_LINE OL ON C.ID = OL.CUSTOMER_ID
                    GROUP BY C.ID
                    HAVING COUNT(OL.ID) = 0
                )""")

    name = fields.Char()
    customer_id = fields.Char(string="Customer ID")
    custodian = fields.Char(string="Custodian Name")
    customer_name = fields.Char(string="Customer Name")
    account_number = fields.Char(string="Account Number")
    account_type = fields.Char(string="Account Type")
    date_opened = fields.Date(string="Date Added")
    number_of_orderlines = fields.Char(string="Number of order lines")