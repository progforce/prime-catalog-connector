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
from __future__ import absolute_import
from openerp.tests import common


class ProductCatalogTestBase(common.TransactionCase):

    def setUp(self):
        super(ProductCatalogTestBase, self).setUp()

        self.product_model = self.env['product.product']
        self.product_model.search([]).write({'active': False})

        self.product_vals = {
            u'name': u'Test Product',
            u'description': u'Test Product Description',
            u'weight': 3.14,
            u'standard_price': 15.1,
            u'description_sale': u'Test Sale Description For Product',
        }

        self.product = self.product_model.create(dict(self.product_vals))
        self.product_vals.update({
            u'id': self.product.id,
            u'categ_id': {
                u'id': self.product.categ_id.id,
                u'name': self.product.categ_id.name,
            },
        })
