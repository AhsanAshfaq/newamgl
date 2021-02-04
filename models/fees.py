# -*- coding: utf-8 -*-

from odoo import models, fields, api
import datetime
import calendar

package_selection = [('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'),
                     ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), ('11', '11'), ('12', '12'),
                     ('13', '13'), ('14', '14'),
                     ('15', '15'), ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20')]
metal_movement_type_selection =[('IT', 'Internal Transfer'), ('USPSPRI', 'USPS Priority Mail')
        , ('UPS2D', 'UPS 2nd Day'), ('UPSND', 'UPS Next Day'), ('OTHER', 'Other'), ('TRANSAC', 'Armored Carrier')
        , ('PICKUP', 'InPerson Pickup')]


class Fees(models.Model):
    _name = 'amgl.fees'
    _description = 'Fees'

    def _calculate_outbound_fees(self):
        for item in self:
            if str(item.metal_movement_type) == 'IT':
                item.update({
                    'outbound_fees': 10.00
                })
            else:
                if item.number_of_packages == 0:
                    item.update({
                        'outbound_fees': 16.50
                    })
                else:
                    item.update({
                        'outbound_fees': 16.50 * int(item.number_of_packages)
                    })

    @api.depends('shipment_fees', 'administrative_fees', 'outbound_fees', 'other_fees')
    def _calculate_total_fees(self):
        for item in self:
            item.update({
                'total_fees': item.administrative_fees + item.shipment_fees + item.outbound_fees + item.other_fees,
                'outbound_fees': item.outbound_fees
            })

    @api.multi
    def get_total_fees(self, transaction):
        return transaction.inbound_fees + transaction.outbound_fees + transaction.shipment_fees + transaction.administrative_fees + transaction.other_fees

    def get_billing_month(self, docs):
        if len(docs) > 0:
            if docs[0].order_line_id:
                month = datetime.datetime.strptime(docs[0].order_line_id.date_received, '%Y-%m-%d').month
                year = datetime.datetime.strptime(docs[0].order_line_id.date_received, '%Y-%m-%d').year
                return str(calendar.month_name[month]) + "-" + str(year)
            if docs[0].metal_movement_id:
                month = datetime.datetime.strptime(docs[0].metal_movement_id.date_create, '%Y-%m-%d').month
                year = datetime.datetime.strptime(docs[0].metal_movement_id.date_create, '%Y-%m-%d').year
                return str(calendar.month_name[month]) + "-" + str(year)
        else:
            return str(calendar.month_name[datetime.datetime.now().month]) + "-" + str(datetime.datetime.now().year)
        return datetime.datetime.now()

    name = fields.Char()
    customer_id = fields.Many2one('amgl.customer', string='Customer')
    order_line_id = fields.Many2one('amgl.order_line', string='Customer')
    metal_movement_id = fields.Many2one('amgl.metal_movement', string='Withdrawal Request')
    inbound_fees = fields.Float(string='Inbound Fees')
    outbound_fees = fields.Float(string='Withdrawal Fees')  # compute="_calculate_outbound_fees"
    administrative_fees = fields.Float(string='Administrative Fees')
    shipment_fees = fields.Float(string='Shipment Fees')
    other_fees = fields.Float(string="Other Fees")
    outbound_fees_type = fields.Char(string='Outbound Type')
    number_of_packages = fields.Selection(selection=package_selection, related='metal_movement_id.number_of_packages',
                                          string="Number Of Packages")
    metal_movement_type = fields.Selection(selection=metal_movement_type_selection,
                                           related='metal_movement_id.metal_movement_type', store=False)
    total_fees = fields.Float(string='Total Fees', compute='_calculate_total_fees')
    fee_note = fields.Char(string="Fees Notes")
