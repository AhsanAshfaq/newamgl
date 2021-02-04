import urllib, json
from datetime import datetime

class Html_Report_Generator(object):

    @classmethod
    def calculate_total_account_value(cls,customer,gold_price,silver_price,platinum_price,palladium_price):
        total_gold = total_silver = total_platinum = total_palladium = 0
        for line in customer.customer_order_lines2:
            qty = float(line.total_received_quantity)
            for p in line.products:
                if p['type'] == 'Gold':
                    total_gold += qty
                if p['type'] == 'Silver':
                    total_silver += qty
                if p['type'] == 'Platinum':
                    total_platinum += qty
                if p['type'] == 'Palladium':
                    total_palladium += qty
        total_account_value = (total_gold * gold_price) + (total_silver * silver_price) + (total_platinum * platinum_price) + (total_palladium * palladium_price)
        return  total_account_value

    @staticmethod
    def generate_daily_transaction_html(customers):
        url = "http://www.amark.com/feeds/spotprices?uid=DD3A01DC-A3C0-4343-9654-15982627BF5A"
        response = urllib.urlopen(url)
        data = json.loads(response.read())
        gold_price = 0
        silver_price = 0
        platinum_price = 0
        palladium_price = 0
        for item in data['SpotPrices']:
            if str(item['Commodity']) == 'Gold':
                gold_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Silver':
                silver_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Platinum':
                platinum_price = float(item['SpotAsk'])
            if str(item['Commodity']) == 'Palladium':
                palladium_price = float(item['SpotAsk'])

        html_str = """
<html lang="en">
    <body style="background-color:white;">
        <div>
            <div style="float:left;">
                <b>GoldStar Trust Company</b>
            </div>
            <div style="float:right;">
                <b>""" + str(datetime.now().date()) + """</b>
            </div>
        </div>
        <br />
        <br />
        <div>
            <div>
                <b>New Accounts:</b> """ + str(datetime.now().date()) + """
            </div>
        </div>
        <hr style="margin-bottom:-10px;border: 2px solid black;" />
        <h3 style="font-weight:bold;">NON-SEGREGATED</h3>
        <table style="text-align: right;border:1px solid #DFE3ED;border-collapse: collapse;">
            <thead>
                <tr style="border:1px solid #DFE3ED;font-size: 14x;">
                    <th nowrap style="text-align:justify;font-weight:bold;border:1px solid #DFE3ED;">
                        Acct#
                    </th>
                    <th nowrap style="text-align:left;font-weight:bold;border:1px solid #DFE3ED;">
                        Dealer Acct
                    </th>
                    <th nowrap style="text-align:left;font-weight:bold;border:1px solid #DFE3ED;">
                        Init Bill Date
                    </th>
                    <th nowrap style="text-align:left;font-weight:bold;border:1px solid #DFE3ED;">
                        Account Name
                    </th>
                    <th nowrap style="text-align:left;font-weight:bold;border:1px solid #DFE3ED;">
                        Account Value
                    </th>
                    <th nowrap style="text-align:left;font-weight:bold;border:1px solid #DFE3ED;">
                        Greater Than <span>$87,500</span>
                    </th>
                    <th nowrap style="text-align:left;font-weight:bold;border:1px solid #DFE3ED;">
                        Less Than <span>$87,500</span>
                    </th>
                    <th nowrap style="text-align:justify;font-weight:bold;border:1px solid #DFE3ED;">
                        Fee
                    </th>
                </tr>
            </thead>
            <tbody>"""

        for customer in customers:
            total_account_value = Html_Report_Generator.calculate_total_account_value(customer,gold_price,silver_price,platinum_price,palladium_price)
            new_row = """
                <tr>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                        """ + str(customer.account_number) + """
                    </td>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                        """ + str(customer.gst_account_number) + """
                    </td>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                        """ + str(datetime.strptime(customer.create_date, '%Y-%m-%d %H:%M:%S').date()) + """
                    </td>
                    <td nowrap style="text-align:justify;font-size: 12x;border:1px solid #DFE3ED;">
                        """ + customer.full_name + """
                    </td>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                        """ + str(total_account_value) + """
                    </td>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                    """ + str(total_account_value if total_account_value > 87500.00 else '') + """
                    </td>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                        """ + str(total_account_value if total_account_value < 87500.00 else '') + """
                    </td>
                    <td style="text-align:justify;font-size: 13x;border:1px solid #DFE3ED;">
                        $70.00
                    </td>
                </tr> """
            html_str += new_row
        html_str += """
                
                            </tbody>
                        </table>
                    </body>
                </html>
        """
        return  html_str