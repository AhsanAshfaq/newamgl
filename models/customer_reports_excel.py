from ReportXlsx import ReportXlsx


class PartnerXlsx(ReportXlsx):

    def generate_xlsx_report(self, workbook, data, partners):
        for obj in partners:
            report_name = obj.first_name
            # One sheet by partner
            sheet = workbook.add_worksheet(report_name[:31])
            bold = workbook.add_format({'bold': True})
            sheet.write(0, 0, obj.first_name, bold)


PartnerXlsx('report.amgl.customer.xlsx',
            'amgl.customer')