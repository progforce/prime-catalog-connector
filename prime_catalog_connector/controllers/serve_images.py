# -*- coding: utf-8 -*-
##############################################################################
#
#    Prime Catalog Connector
#    Copyright (C) 2017 Progforce, LLC (<http://progforce.com/>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.http import Controller, route, request
from openerp.addons.web.controllers.main import (serialize_exception,
                                                 content_disposition)
import logging
import base64
import imghdr
import os

_logger = logging.getLogger(__name__)


class ServeImageController(Controller):

    @route('/image_for/<string:sku>', type='http', auth='public')
    @serialize_exception
    def return_image(self, sku=None, **args):
        product_template = request.env['product.template']
        product_template_ids = product_template.search([('sku', '=', sku)])
        if not product_template_ids:
            result = request.not_found()
        elif len(product_template_ids.ids) > 1:
            result = request.not_found()
        else:
            image = product_template_ids.image
            if not image:
                result = request.not_found()
            else:
                image_type = 'jpg'
                try:
                    tmp_filename = '/tmp/' + sku
                    open(tmp_filename, 'wb').write(base64.b64decode(image))
                    image_type = imghdr.what(tmp_filename)
                    os.remove(tmp_filename)
                except OSError:
                    pass
                result = request.make_response(
                    base64.b64decode(image),
                    [('Content-Type', 'application/octet-stream'),
                     ('Content-Disposition',
                      content_disposition('{}.{}'.format(sku, image_type)))])
        return result
