from ReportXlsx import ReportXlsx
import datetime
import urllib
import json


class CustomerCurrentInventoryXlsx(ReportXlsx):

    gold_price = 0
    silver_price = 0
    platinum_price = 0
    palladium_price = 0

    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            worksheet = workbook.add_worksheet(obj.full_name)
            bold = workbook.add_format({'bold': True})
            CustomerCurrentInventoryXlsx.add_headers_for_current_inventory(bold, worksheet, workbook, obj)
            total_cells_format = workbook.add_format({'bold': True})
            total_cells_format.set_border(1)
            self.add_rows_in_worksheet_for_current_inventory(obj, worksheet, bold, workbook)

    def get_customer_master_order_lines(self, customer):
        customer_master_order_lines = self.env['amgl.order_line'].search([('customer_id', '=', customer.id),
                                                                          ('is_master_records', '=', True),
                                                                          ('is_active', '=', True)])
        filtered_order_lines = []
        if customer_master_order_lines:
            for order_line in customer_master_order_lines:
                master_product_quantity = self.get_total_quantity_after_including_completed_withdrawal(order_line)
                if master_product_quantity > 0:
                    filtered_order_lines.append(order_line)
        return filtered_order_lines

    def get_total_quantity_after_including_completed_withdrawal(self, order):
        master_product_quantity = order.total_received_quantity
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', order.products.id), ('is_master_records', '=', False), ('customer_id', '=', order.customer_id.id)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed' and item.metal_movement_id.mmr_number:
                    master_product_quantity += (-item.total_received_quantity)
        return master_product_quantity

    def get_total_weight_after_including_completed_withdrawal(self, order):
        master_product_quantity = order.temp_received_weight
        order_lines = self.env['amgl.order_line'].search(
            [('products', '=', order.products.id), ('is_master_records', '=', False), ('customer_id', '=', order.customer_id.id)])
        if order_lines:
            for item in order_lines:
                if item.metal_movement_id and item.metal_movement_id.state != 'completed' and item.metal_movement_id.mmr_number:
                    master_product_quantity += (-item.temp_received_weight)
        return master_product_quantity

    def add_rows_in_worksheet_for_current_inventory(self, obj, worksheet, bold, workbook):
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        row_count = 5
        column_count = 0
        worksheet.write(row_count, column_count, 'First Name', bold)
        worksheet.write(row_count, column_count + 1, obj.first_name)
        worksheet.write(row_count, column_count + 5, 'Last Name', bold)
        worksheet.write(row_count, column_count + 6, obj.last_name)
        row_count += 1
        worksheet.write(row_count, column_count, 'Account Type', bold)
        worksheet.write(row_count, column_count + 1, obj.account_type)
        worksheet.write(row_count, column_count + 5, 'Account Number', bold)
        worksheet.write(row_count, column_count + 6,
                        obj.account_number if 'Gold' not in obj.custodian_id.name else obj.gst_account_number)
        row_count += 1
        worksheet.write(row_count, column_count, 'Custodian', bold)
        worksheet.write(row_count, column_count + 1, obj.custodian_id.name)
        row_count = 11
        column_count = 0
        order_lines = self.get_customer_master_order_lines(obj)
        if not obj.is_account_closed:
            if order_lines:
                for inventory in order_lines:
                    render_row = False
                    if not inventory.metal_movement_id:
                        render_row = True
                    if inventory.metal_movement_id:
                        if inventory.metal_movement_id.state == 'completed':
                            render_row = True
                    if render_row:
                        worksheet.write(row_count, column_count, inventory.products.goldstar_name)
                        column_count += 1
                        worksheet.write(row_count, column_count, inventory.commodity)
                        column_count += 1
                        worksheet.write(row_count, column_count, str('{0:,.0f}'.format(self.get_total_quantity_after_including_completed_withdrawal(inventory))),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        worksheet.write(row_count, column_count, str('{0:,.2f}'.format(self.get_total_weight_after_including_completed_withdrawal(inventory)) + ' oz'),
                                        format_for_numeric_without_bold)
                        column_count += 1
                        is_data_exists = True
                        row_count += 1
                        column_count = 0
            else:
                worksheet.write(row_count, column_count, 'N/A')
                column_count += 1
                worksheet.write(row_count, column_count, 'N/A')
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.0f}'.format(0)),
                                format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0) + ' oz'),
                                format_for_numeric_without_bold)
                column_count += 1
                row_count += 1
            self.add_total_table(obj, row_count, worksheet, bold, format_for_numeric_bold,
                                                         format_for_numeric_without_bold)
        else:
            worksheet.write(row_count, column_count, 'No information as this account is closed.', bold)

    @staticmethod
    def add_headers_for_current_inventory(bold, worksheet, workbook, obj):
        row_count = 10
        column_count = 0
        format_for_title = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
        format_for_date = workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter'})
        worksheet.merge_range(0, 0, 1, 6, 'Customer Current Inventory', format_for_title)
        worksheet.merge_range(3, 5, 3, 6, str(
            datetime.datetime.strptime(str(datetime.datetime.now().date()), '%Y-%m-%d').strftime("%m/%d/%Y")),
                              format_for_date)

        if not obj.is_account_closed:
            worksheet.write(row_count, column_count, 'Product', bold)
            worksheet.write(row_count, column_count + 1, 'Commodity', bold)
            worksheet.write(row_count, column_count + 2, 'Quantity', bold)
            worksheet.write(row_count, column_count + 3, 'Total Weight', bold)

    def check_if_all_quantity_is_withdrawn(self, customer):
        if customer.total > 0:
            return False
        if customer.total == 0:
            withdraws = self.env['amgl.metal_movement'].search([('customer', '=', customer.id), ('state', '!=', 'completed')])
            if withdraws:
                return False
            else:
                return True

    def get_spot_price_from_amark(self):
        url = "http://www.amark.com/feeds/spotprices?uid=DD3A01DC-A3C0-4343-9654-15982627BF5A"
        response = urllib.urlopen(url)
        data = json.loads(response.read())

        for item in data['SpotPrices']:
            if str(item['Commodity']) == 'Gold':
                CustomerCurrentInventoryXlsx.gold_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Silver':
                CustomerCurrentInventoryXlsx.silver_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Platinum':
                CustomerCurrentInventoryXlsx.platinum_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Palladium':
                CustomerCurrentInventoryXlsx.palladium_price = float(item['SpotAsk'])
        return CustomerCurrentInventoryXlsx.gold_price, CustomerCurrentInventoryXlsx.palladium_price, CustomerCurrentInventoryXlsx.platinum_price, CustomerCurrentInventoryXlsx.silver_price

    def calculate_weights(self, product, quantity):
        total_weight = 0.0
        if product.weight_unit == 'oz':
            total_weight = quantity * product.weight_per_piece
        if product.weight_unit == 'gram':
            total_weight = quantity * (product.weight_per_piece * 0.03215)
        if product.weight_unit == 'kg':
            total_weight = quantity * (product.weight_per_piece * 32.15)
        if product.weight_unit == 'pounds':
            total_weight = quantity * product.weight_per_piece * 16
        return total_weight

    def calculate_current_inventory_values(self, customer, type):
        order_lines = self.env['amgl.order_line'].search([('customer_id', '=', customer.id)])
        all_withdrawn = self.check_if_all_quantity_is_withdrawn(customer)
        if all_withdrawn:
            return [0.00, 0.00, 0.00]

        filtered_order_lines = []
        for item in order_lines:
            if item.metal_movement_id:
                if item.metal_movement_id.state == 'completed':
                    filtered_order_lines.append(item)
            else:
                if not item.is_master_records:
                    filtered_order_lines.append(item)

        gold_price, palladium_price, platinum_price, silver_price = self.get_spot_price_from_amark()
        total_gold = total_silver = total_platinum = total_palladium = total = 0
        total_weight = gold_weight = silver_weight = platinum_weight = palladium_weight = 0
        for line in filtered_order_lines:
            for p in line.products:
                qty = line.total_received_quantity
                if p['type'] == 'Gold':
                    total_gold += qty
                    total += qty
                    gold_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Silver':
                    total_silver += qty
                    total += qty
                    silver_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Platinum':
                    total_platinum += qty
                    total += qty
                    platinum_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)
                if p['type'] == 'Palladium':
                    total_palladium += qty
                    total += qty
                    palladium_weight += self.calculate_weights(p, qty)
                    total_weight += self.calculate_weights(p, qty)

        account_value = gold_weight * gold_price + silver_weight * silver_price + platinum_weight * platinum_price + palladium_weight * palladium_price

        if type == 'Gold':
            return [total_gold, round(gold_weight, 2), round(gold_weight * gold_price, 2)]
        if type == 'Silver':
            return [total_silver, round(silver_weight, 2), round(silver_weight * silver_price, 2)]
        if type == 'Platinum':
            return [total_platinum, round(platinum_weight, 2), round(platinum_weight * platinum_price, 2)]
        if type == 'Palladium':
            return [total_palladium, round(palladium_weight, 2), round(palladium_weight * palladium_price, 2)]
        if type == 'Total':
            return [total_gold + total_silver + total_platinum + total_palladium ,
                    round(gold_weight + silver_weight + platinum_weight + palladium_weight, 2),
                    round(account_value,2)]

    def add_total_table(self, obj, row_count, worksheet, bold, format_for_numeric_bold, format_for_numeric_without_bold):
        gold_values = self.calculate_current_inventory_values(obj, 'Gold')
        silver_values = self.calculate_current_inventory_values(obj, 'Silver')
        platinum_values = self.calculate_current_inventory_values(obj, 'Platinum')
        palladium_values = self.calculate_current_inventory_values(obj, 'Palladium')
        g_total_values = self.calculate_current_inventory_values(obj, 'Total')

        row_number = row_count + 3
        column_count = 4
        worksheet.write(row_number, column_count, '')
        row_number += 1
        worksheet.write(row_number, column_count, 'Gold')
        row_number += 1
        worksheet.write(row_number, column_count, 'Silver')
        row_number += 1
        worksheet.write(row_number, column_count, 'Platinum')
        row_number += 1
        worksheet.write(row_number, column_count, 'Palladium')
        row_number += 1
        worksheet.write(row_number, column_count, 'Grand Total', bold)
        row_number = row_count + 3
        column_count += 1

        worksheet.write(row_number, column_count, 'Total Units', bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(gold_values[0])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(silver_values[0])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(platinum_values[0])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(palladium_values[0])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.0f}'.format(g_total_values[0])), format_for_numeric_bold)
        row_number = row_count + 3
        column_count += 1

        worksheet.write(row_number, column_count, 'Total Weight', bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(gold_values[1]) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(silver_values[1]) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(platinum_values[1]) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(palladium_values[1]) + ' oz'),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, str('{0:,.2f}'.format(g_total_values[1]) + ' oz'),
                        format_for_numeric_bold)
        row_number = row_count + 3
        column_count += 1

        worksheet.write(row_number, column_count, 'Total Value', bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(gold_values[2])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(silver_values[2])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(platinum_values[2])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(palladium_values[2])),
                        format_for_numeric_without_bold)
        row_number += 1
        worksheet.write(row_number, column_count, '$ ' + str('{0:,.2f}'.format(g_total_values[2])),
                        format_for_numeric_bold)


CustomerCurrentInventoryXlsx('report.customer.current.inventory.xlsx',
            'amgl.customer')