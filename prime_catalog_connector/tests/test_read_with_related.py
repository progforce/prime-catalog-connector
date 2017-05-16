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
from .prime_catalog_base import ProductCatalogTestBase
from ..models.prime_catalog_backend import read


@common.at_install(False)
@common.post_install(True)
class TestRead(ProductCatalogTestBase):

    def test_read_with_related(self):
        self.assertEqual(
            [{
                'id': self.product_vals['id'],
                'name': self.product_vals['name'],
                'categ_id': self.product.categ_id.id,
            }],
            read(self.product, ['name', 'categ_id']),
            'Simple read',)

        self.assertEqual(
            [{
                'id': self.product_vals['id'],
                'name': self.product_vals['name'],
                'categ_id': {
                    'id': self.product.categ_id.id,
                    'name': self.product.categ_id.name,
                    'create_uid': {
                        'id': self.product.categ_id.create_uid.id,
                        'name': self.product.categ_id.create_uid.name,
                    },
                },
            }],
            read(self.product, [
                'name', 'categ_id', 'categ_id.name', 'categ_id.create_uid.name'
            ]),
            'Read nested fields',)
