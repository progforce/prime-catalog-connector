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
import json
from openerp.tests import common
from .prime_catalog_base import ProductCatalogTestBase
from openerp.addons.connector.tests.common import mock_job_delay_to_direct
from ..backend import prime_catalog
from ..models.prime_catalog_backend import PrimeCatalogService


@prime_catalog(replacing=PrimeCatalogService)
class PrimeCatalogServiceMock(PrimeCatalogService):
    _model_name = 'prime.catalog.service'

    def post_product_json(self, *args, **kwargs):
        self.post_product_json.__func__.last_args = args
        self.post_product_json.__func__.last_kwargs = kwargs

        try:
            self.post_product_json.__func__.num_calls += 1
        except AttributeError:
            self.post_product_json.__func__.num_calls = 1


@common.at_install(False)
@common.post_install(True)
class TestExportProducts(ProductCatalogTestBase):

    def setUp(self):
        super(TestExportProducts, self).setUp()
        self.mock_data = PrimeCatalogServiceMock.post_product_json.__func__
        self.mock_data.num_calls = 0

    def _export(self):
        job_path = ('openerp.addons.prime_catalog_connector.models'
                    '.prime_catalog_backend.export_product_job')
        with mock_job_delay_to_direct(job_path):

            catalog_backend = self.env['prime.catalog.backend'].create({
                'name':
                'Test Backend',
                'version':
                '0.1',
                'url':
                'empty url',
            })

            catalog_backend.export_products()

    def test_export_products(self):
        self._export()
        self.assertEqual(
            self.product_vals,
            json.loads(self.mock_data.last_args[0]),)

    def test_num_requests(self):
        self.product_model.create({'name': 'Empty Product'})
        self._export()
        self.assertEqual(2, self.mock_data.num_calls)

    def _check_export_was_called(self, func):
        job_path = ('openerp.addons.prime_catalog_connector.models'
                    '.prime_catalog_backend.export_product_job')
        with mock_job_delay_to_direct(job_path):
            func()

        self.assertEqual(1, self.mock_data.num_calls)

    def test_export_while_create_product(self):

        def create():
            self.product_model.create({
                'name': 'Test Auto Export Product',
            })

        self._check_export_was_called(create)

    def test_export_while_change_product(self):

        def write():
            self.product.write({
                'name': 'New name',
            })

        self._check_export_was_called(write)
