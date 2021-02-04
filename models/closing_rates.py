# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError


class ClosingRates(models.Model):
    _name = 'amgl.closing.rates'
    _description = 'AMGL Metal Closing Rates'
    _rec_name = 'month'
    _order = 'year_and_month_for_sorting asc'

    def get_months(self):
        return [('January', 'January'), ('February', 'February'), ('March', 'March'), ('April', 'April'),
                ('May', 'May'), ('June', 'June'), ('July', 'July'), ('August', 'August'),
                ('September', 'September'), ('October', 'October'), ('November', 'November'), ('December', 'December')]

    @staticmethod
    def zero_validation_on_float_fields(vals):
        if vals.get('gold_rate'):
            if float(vals['gold_rate']) <= 0:
                raise ValidationError('Closing rate for gold must be greater than zero.')
        if vals.get('silver_rate'):
            if float(vals['silver_rate']) <= 0:
                raise ValidationError('Closing rate for silver must be greater than zero.')
        if vals.get('platinum_rate'):
            if float(vals['platinum_rate']) <= 0:
                raise ValidationError('Closing rate for platinum must be greater than zero.')
        if vals.get('palladium_rate'):
            if float(vals['palladium_rate']) <= 0:
                raise ValidationError('Closing rate for palladium must be greater than zero.')

    def validate_selected_closing_month(self, vals):
        if vals.get('month'):
            month = vals['month']
            existing_record = self.env['amgl.closing.rates'].search(
                [('month', '=', month), ('years', '=', datetime.today().year)])
            if existing_record:
                raise ValidationError('Record already exists against selected month and year.')

    @api.model
    def create(self, vals):
        self.zero_validation_on_float_fields(vals)
        self.validate_selected_closing_month(vals)
        self.fill_year_and_month_column_value(vals,False)
        record = super(ClosingRates, self).create(vals)
        return record

    @api.multi
    def write(self, vals):
        self.zero_validation_on_float_fields(vals)
        self.validate_selected_closing_month(vals)
        self.fill_year_and_month_column_value(vals,True)
        record = super(ClosingRates, self).write(vals)
        return record

    def get_month_description(self,month):
        months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        index = months.index(month) + 1
        month_description= '('
        if index < 10:
            month_description += '0'
        month_description +=  str(index) + ') ' + month
        return month_description

    def fill_year_and_month_column_value(self,vals,is_edit):
        month = vals.get('month')
        _years = ''
        if month:
            if is_edit:
                _years = str(self.years)
            else:
                _years = str(datetime.today().year)
            _month = self.get_month_description(month)
            year_and_month = str(_years + ' - ' + _month)
            vals.update({'year_and_month_for_sorting': year_and_month})
        return vals

    def get_years(self):
        year_list = []
        current_year = int(datetime.today().year) + 1
        for i in range(2016, current_year):
            year_list.append((str(i), str(i)))
        return year_list

    name = fields.Char()
    month = fields.Selection(selection=get_months, required=True)
    years = fields.Selection(default=str(datetime.today().year), selection=get_years, required=True)
    gold_rate = fields.Float(required=True)
    silver_rate = fields.Float(required=True)
    platinum_rate = fields.Float(required=True)
    palladium_rate = fields.Float(required=True)
    year_and_month_for_sorting = fields.Char(String="Year and Month")
