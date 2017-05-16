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

import json
from openerp import models, api
from openerp.exceptions import Warning as UserError


class ParametersResConfigSettings(models.TransientModel):
    _name = 'parameters.res.config.settings'
    _inherit = 'res.config.settings'

    def _get_config_key_name(self):
        return 'config.{}'.format(self._name)

    @api.multi
    def execute(self):
        return super(ParametersResConfigSettings, self.sudo()).execute()

    @api.model
    def get_default_values(self, fields):
        json_str = self.env['ir.config_parameter'].get_param(
            self._get_config_key_name(), '{}')

        values = json.loads(json_str)

        for field in [x for x in fields if x not in values]:
            if not values.get(field):
                default_value = self._defaults.get(field)
                if default_value:
                    if callable(default_value):
                        default_value = default_value(self)

                    values.update({field: default_value})

        values.pop('id', None)

        return values

    @api.multi
    def set_default_values(self):
        self.ensure_one()
        values = self.read()[0]

        fields = self.fields_get()

        many2one_fields = [
            field for field in fields.items() if field[1]['type'] == 'many2one'
        ]

        for many2one_field in many2one_fields:
            name = many2one_field[0]
            if values[name]:
                values[name] = values[name][0]

        self.env['ir.config_parameter'].set_param(self._get_config_key_name(),
                                                  json.dumps(values))

    @api.model
    def set(self, field, value):
        json_str = self.env['ir.config_parameter'].get_param(
            self._get_config_key_name(), '{}')

        values = json.loads(json_str)
        values.update({field: value})

        self.env['ir.config_parameter'].set_param(self._get_config_key_name(),
                                                  json.dumps(values))

    @api.model
    def get(self, field, default=None):
        data = self.get_default_values([field])
        field_value = data.get(field)

        fields_desc = self.fields_get(field)

        if field not in fields_desc:
            raise Exception('Config field {0} doesn\'t exists!'.format(field))

        field_desc = fields_desc[field]

        if field_desc['type'] == 'many2one':
            field_value = self.env[field_desc['relation']].browse(field_value)
        elif field_desc['type'] == 'many2many':
            if field_value:
                if isinstance(field_value[0], tuple):
                    field_value = field_value[0][2]

                field_value = self.env[field_desc['relation']]\
                    .browse(field_value)

        if not field_value and field_desc.get('required'):
            raise UserError(
                'Please set up "{field_name}" in "{settings_name}"'.format(
                    field_name=field_desc['string'],
                    settings_name=self._name,))

        return field_value or default
