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

from openerp.tests import common
from openerp import models, fields
from openerp.exceptions import Warning as UserError


class TestConfigSettings(models.TransientModel):
    _name = 'test.config.settings'
    _inherit = 'parameters.res.config.settings'

    name = fields.Char('Name')
    number = fields.Integer('Number', default=13)
    required = fields.Char(required=True)


@common.at_install(False)
@common.post_install(True)
class TestParametersResConfigSettings(common.TransactionCase):

    def setUp(self):
        super(TestParametersResConfigSettings, self).setUp()
        self.conf = self.env['test.config.settings']

    def test_set(self):
        self.assertEqual(self.conf.get('number'), 13)

        self.conf.set('name', 'value')

        self.assertEqual(self.conf.get('name'), 'value')
        self.assertEqual(self.conf.get('number'), 13)

    def test_default_set(self):
        self.conf.set('number', 1)
        self.assertEqual(self.conf.get('number'), 1)

    def test_empty_required_raise_exception(self):
        self.assertRaises(UserError, lambda: self.conf.get('required'))
