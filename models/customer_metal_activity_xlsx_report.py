from ReportXlsx import ReportXlsx
import datetime


class CustomerMetalActivityXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            worksheet = workbook.add_worksheet(obj.full_name)
            bold = workbook.add_format({'bold': True})
            CustomerMetalActivityXlsx.add_headers_for_current_inventory(bold, worksheet, workbook)
            total_cells_format = workbook.add_format({'bold': True})
            total_cells_format.set_border(1)
            self.add_rows_in_worksheet_for_current_inventory(obj, worksheet, bold, workbook)

    def add_rows_in_worksheet_for_current_inventory(self, obj, worksheet, bold, workbook):
        format_for_numeric_without_bold = workbook.add_format({'align': 'right'})
        customer_current_activity = self.get_filtered_order_lines_for_metal_activity_report(obj.id)
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
        if customer_current_activity:
            for inventory in customer_current_activity:
                worksheet.write(row_count, column_count, inventory.products.goldstar_name)
                column_count += 1
                worksheet.write(row_count, column_count, inventory.commodity)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.0f}'.format(inventory.total_received_quantity)),
                                format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str('{0:,.2f}'.format(inventory.temp_received_weight) + ' oz'),
                                format_for_numeric_without_bold)
                column_count += 1
                worksheet.write(row_count, column_count, str(
                    datetime.datetime.strptime(inventory.date_for_customer_metal_activitiy, '%Y-%m-%d').strftime(
                        "%m/%d/%Y")))
                column_count += 1
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
            worksheet.write(row_count, column_count, 'N/A')
            column_count += 1
            row_count += 1

    @staticmethod
    def add_headers_for_current_inventory(bold, worksheet, workbook):
        row_count = 10
        column_count = 0
        format_for_title = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
        format_for_date = workbook.add_format({'bold': True, 'align': 'right', 'valign': 'vcenter'})
        worksheet.merge_range(0, 0, 1, 6, 'Customer Metal Activity', format_for_title)
        worksheet.merge_range(2, 5, 2, 6, str(
            datetime.datetime.strptime(str(datetime.datetime.now().date()), '%Y-%m-%d').strftime("%m/%d/%Y")),
                              format_for_date)
        worksheet.write(row_count, column_count, 'Product', bold)
        worksheet.write(row_count, column_count + 1, 'Commodity', bold)
        worksheet.write(row_count, column_count + 2, 'Quantity', bold)
        worksheet.write(row_count, column_count + 3, 'Total Weight', bold)
        worksheet.write(row_count, column_count + 4, 'Date', bold)

    def get_sorted_list(self, obj_list, sort_by_product_code=False, sort_by_product_id=False):
        if sort_by_product_code:
            return obj_list.sorted(key=lambda x: x.gs_product_code, reverse=False)
        elif sort_by_product_id:
            return obj_list.sorted(key=lambda x: x.id, reverse=False)
        else:
            return obj_list.sorted(key=lambda x: x.date_for_customer_metal_activitiy, reverse=True)

    def get_filtered_order_lines_for_metal_activity_report(self,customer_id):
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

CustomerMetalActivityXlsx('report.customer.metal.activity.xlsx',
            'amgl.customer')