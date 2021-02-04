
from ReportXlsx import ReportXlsx
import datetime
import xlsxwriter



class CustomerTransactionHistoryXlsx(ReportXlsx):


    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            worksheet = workbook.add_worksheet(obj.full_name)
            bold = workbook.add_format({'bold': True})
            CustomerTransactionHistoryXlsx.add_headers_for_customer_transaction_history(bold, worksheet, workbook, obj)
            total_cells_format = workbook.add_format({'bold': True})
            total_cells_format.set_border(1)
            self.add_rows_in_worksheet_for_customer_transaction_history(worksheet, bold, workbook,obj)

    @staticmethod
    def add_headers_for_customer_transaction_history(bold, worksheet, workbook, obj):
        format_for_subject = workbook.add_format({
            'bold': True,
            'align': 'center',
            'valign': 'vcenter',
            'underline': True
        })
        worksheet.merge_range(0, 0, 3, 12, 'Customer Transaction History', format_for_subject)
        row_count = 8
        column_count = 0
        if not obj.is_account_closed:
            worksheet.write(row_count, column_count, 'Product', bold)
            worksheet.write(row_count, column_count + 1, 'Date', bold)
            worksheet.write(row_count, column_count + 2, 'Prod Code', bold)
            worksheet.write(row_count, column_count + 3, 'Units', bold)
            worksheet.write(row_count, column_count + 4, 'Gold Weight', bold)
            worksheet.write(row_count, column_count + 5, 'Silver Weight', bold)
            worksheet.write(row_count, column_count + 6, 'Plat Weight', bold)
            worksheet.write(row_count, column_count + 7, 'Pall Weight', bold)
            worksheet.write(row_count, column_count + 8, 'Vault', bold)

    def add_rows_in_worksheet_for_customer_transaction_history(self, worksheet, bold, workbook,customer):
        format_for_numeric_bold = workbook.add_format({'bold': True, 'align': 'right', })
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        customer_order_lines = self.get_filtered_order_lines(customer.id)
        row_count = 4
        column_count = 0
        if not customer.is_account_closed:
            worksheet.write(row_count, column_count, customer.custodian_id.name, bold)
            worksheet.write(row_count, column_count + 10, str(
                datetime.datetime.strptime(str(datetime.datetime.now().date()), '%Y-%m-%d').strftime("%m/%d/%Y")), bold)
            row_count += 2
            worksheet.write(row_count, column_count, 'Customer Name:', bold)
            worksheet.write(row_count, column_count + 1, customer.full_name)
            if 'Gold' in customer.custodian_id.name:
                worksheet.write(row_count, column_count + 4, 'GS#:', bold)
                worksheet.write(row_count, column_count + 5,
                                'N/A' if 'Gold' not in customer.custodian_id.name else customer.gst_account_number)
                worksheet.write(row_count, column_count + 6, 'FTI#:', bold)
                worksheet.write(row_count, column_count + 7, customer.account_number)
                worksheet.write(row_count, column_count + 10, 'A-NS:', bold)
                worksheet.write(row_count, column_count + 11, customer.full_name)
            else:
                worksheet.write(row_count, column_count + 4, 'FTI#:', bold)
                worksheet.write(row_count, column_count + 5, customer.account_number)
                worksheet.write(row_count, column_count + 9, 'A-NS:', bold)
                worksheet.write(row_count, column_count + 10, customer.full_name)
            unique_product_total = total_quantity = total_gold = total_silver = total_platinum = total_palladium = 0
        if not customer.is_account_closed:
            if customer_order_lines:
                unique_products_list = []
                for ol in customer_order_lines:
                    if ol.products.gs_product_code not in unique_products_list:
                        unique_products_list.append(ol.products.gs_product_code)
                row_count = 9
                column_count = 0
                for unique_product_code in unique_products_list:
                    for inventory in customer_order_lines:
                        if inventory.products.gs_product_code == unique_product_code:
                            unique_product_total += inventory.total_received_quantity
                            worksheet.write(row_count, column_count, inventory.products.goldstar_name)
                            column_count += 1
                            worksheet.write(row_count, column_count, str(
                                datetime.datetime.strptime(inventory.date_for_customer_metal_activitiy,
                                                           '%Y-%m-%d').strftime("%m/%d/%Y")))
                            column_count += 1
                            worksheet.write(row_count, column_count, inventory.products.gs_product_code)
                            column_count += 1
                            total_quantity += inventory.total_received_quantity
                            if inventory.metal_movement_id:
                                worksheet.write(row_count, column_count,
                                                '(' + str('{0:,.0f}'.format(-(inventory.total_received_quantity))) + ')',
                                                format_for_numeric_without_bold)
                            else:
                                worksheet.write(row_count, column_count,
                                                str('{0:,.0f}'.format(inventory.total_received_quantity)),
                                                format_for_numeric_without_bold)
                            column_count += 1
                            if inventory.commodity == 'Gold':
                                worksheet.write(row_count, column_count,
                                                str('{0:,.2f}'.format(inventory.temp_received_weight)) + ' oz',
                                                format_for_numeric_without_bold)
                                total_gold += inventory.temp_received_weight
                            else:
                                worksheet.write(row_count, column_count, '0.00 oz', format_for_numeric_without_bold)
                            column_count += 1
                            if inventory.commodity == 'Silver':
                                total_silver += inventory.temp_received_weight
                                worksheet.write(row_count, column_count,
                                                str('{0:,.2f}'.format(inventory.temp_received_weight)) + ' oz',
                                                format_for_numeric_without_bold)
                            else:
                                worksheet.write(row_count, column_count, '0.00 oz', format_for_numeric_without_bold)
                            column_count += 1
                            if inventory.commodity == 'Platinum':
                                total_platinum += inventory.temp_received_weight
                                worksheet.write(row_count, column_count,
                                                str('{0:,.2f}'.format(inventory.temp_received_weight)) + ' oz',
                                                format_for_numeric_without_bold)
                            else:
                                worksheet.write(row_count, column_count, '0.00 oz', format_for_numeric_without_bold)
                            column_count += 1
                            if inventory.commodity == 'Palladium':
                                total_palladium += inventory.temp_received_weight
                                worksheet.write(row_count, column_count,
                                                str('{0:,.2f}'.format(inventory.temp_received_weight)) + ' oz',
                                                format_for_numeric_without_bold)
                            else:
                                worksheet.write(row_count, column_count, '0.00 oz', format_for_numeric_without_bold)
                            column_count += 1
                            worksheet.write(row_count, column_count, inventory.vault)
                            row_count += 1
                            column_count = 0
                    column_count = 2
                    worksheet.write(row_count, column_count, unique_product_code, bold)
                    column_count += 1
                    worksheet.write(row_count, column_count, '{0:,.0f}'.format(unique_product_total),
                                    format_for_numeric_bold)
                    unique_product_total = 0
                    row_count += 1
                    column_count = 0

                row_count += 1
                column_count = 3
                worksheet.write(row_count, column_count, '{0:,.0f}'.format(total_quantity), format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(total_gold)) + ' oz',
                                format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(total_silver)) + ' oz',
                                format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(total_platinum)) + ' oz',
                                format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(total_palladium)) + ' oz',
                                format_for_numeric_bold)
            else:
                row_count = 9
                worksheet.write(row_count, column_count, 'N/A')
                column_count += 1
                worksheet.write(row_count, column_count, 'N/A')
                column_count += 1
                worksheet.write(row_count, column_count, 'N/A')
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.0f}'.format(0)), format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz', format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz', format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz', format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz', format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, 'N/A')

                row_count += 2
                column_count = 3
                worksheet.write(row_count, column_count, '{0:,.0f}'.format(0), format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz',
                                format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz',
                                format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz',
                                format_for_numeric_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(0)) + ' oz',
                                format_for_numeric_bold)
        else:
            worksheet.write(row_count, column_count, 'No information as this account is closed.', bold)

    def get_filtered_order_lines(self,customer_id):
        order_lines = self.env['amgl.order_line'].search(
            [('is_master_records', '=', False), ('customer_id', '=', customer_id), ('is_active', '=', True)])
        filtered_order_lines = []
        if order_lines:
            sorted_order_lines = self.get_sorted_list(order_lines)
            for item in sorted_order_lines:
                if not item.metal_movement_id or (
                    item.metal_movement_id and item.metal_movement_id.state == 'completed'):
                    filtered_order_lines.append(item)
        return filtered_order_lines

    def get_sorted_list(self, obj_list, sort_by_product_code=False, sort_by_product_id=False):
        if sort_by_product_code:
            return obj_list.sorted(key=lambda x: x.gs_product_code, reverse=False)
        elif sort_by_product_id:
            return obj_list.sorted(key=lambda x: x.id, reverse=False)
        else:
            return obj_list.sorted(key=lambda x: x.date_for_customer_metal_activitiy, reverse=True)

CustomerTransactionHistoryXlsx('report.customer.transaction.history.xlsx',
            'amgl.customer')