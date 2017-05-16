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
from openerp import fields, models


class CatalogURLsConfigSettings(models.TransientModel):
    _name = 'catalog.urls.config.settings'
    _inherit = 'parameters.res.config.settings'

    base_api_url = fields.Char(
        'Base API URL',
        default='api',)

    post_product_url = fields.Char(
        'Post Product URL',
        default='products',)

    get_json_keys_url = fields.Char(
        'Get JSON Keys URL',
        default='getJsonKeys',)

    revoke_token_url = fields.Char(
        'Revoke Token URL',
        default='login',)

    mapping_csv_url = fields.Char(
        'Mapping CSV URL',
        default='getMappingCSV',)
