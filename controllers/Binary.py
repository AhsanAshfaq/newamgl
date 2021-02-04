import base64
from odoo.addons.web.controllers.main import serialize_exception, content_disposition

from odoo import api
from odoo import http
from odoo.http import request


class Binary(http.Controller):
    @http.route('/web/binary/download_document', type='http', auth="public")
    @serialize_exception
    def download_document(self, model, field, id, filename=None, **kw):
        """ Download link for files stored as binary fields.
        :param str model: name of the model to fetch the binary from
        :param str field: binary field
        :param str id: id of the record from which to fetch the binary
        :param str filename: field holding the file's name, if any
        :returns: :class:`werkzeug.wrappers.Response`
        """
        Model = request.registry[model]
        env = api.Environment(request.cr, request.uid, request.context)
        res = env['ir.attachment'].search([('id', '=', id)])
        filecontent = base64.b64decode(res.datas or '')
        if not filecontent:
            return request.not_found()
        else:
            if not filename:
                filename = '%s_%s' % (model.replace('.', '_'), id)
                return request.make_response(filecontent,
                                             [('Content-Type', 'application/octet-stream'),
                                              ('Content-Disposition', content_disposition(filename))])
            else:
                return request.make_response(filecontent,
                                             [('Content-Type', 'application/vnd.ms-excel'),
                                              ('Content-Disposition', content_disposition(filename))])
